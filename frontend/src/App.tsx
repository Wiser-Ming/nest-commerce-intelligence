import {
  Activity,
  CircleGauge,
  Eraser,
  History,
  Layers3,
  MessageSquarePlus,
  Network,
  Server,
  Wifi,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Composer } from "./components/Composer";
import { EmptyState, type ExamplePrompt } from "./components/EmptyState";
import { MessageBubble } from "./components/MessageBubble";
import { streamQuery } from "./lib/agentApi";
import { summarizeResult } from "./lib/format";
import type { AgentEvent, ChatMessage, StepState } from "./types/agent";

const examples: ExamplePrompt[] = [
  {
    query: "统计 2025 年第一季度各大区的 GMV，并按 GMV 从高到低排序",
    label: "区域表现",
    description: "跨区域对比 · 排名",
  },
  {
    query: "统计 2025 年 3 月各商品品类的销量和销售额",
    label: "品类拆解",
    description: "销量与销售额 · 聚合",
  },
  {
    query: "查询华东地区 2025 年第一季度销售额最高的前 5 个商品",
    label: "商品排行",
    description: "限定区域 · Top 5",
  },
  {
    query: "按会员等级统计 2025 年第一季度的订单数和销售额",
    label: "会员分析",
    description: "分层统计 · 双指标",
  },
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "Vite /api proxy";

function makeId() {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function upsertStep(steps: StepState[] = [], event: Extract<AgentEvent, { type: "progress" }>) {
  const next = steps.filter((item) => item.step !== event.step);
  next.push({
    step: event.step,
    status: event.status,
    updatedAt: Date.now(),
  });
  return next;
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [activeController, setActiveController] = useState<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const isStreaming = Boolean(activeController);
  const canSubmit = draft.trim().length > 0 && !isStreaming;

  const completedCount = useMemo(
    () => messages.filter((message) => message.role === "assistant" && message.status === "done").length,
    [messages],
  );

  useEffect(() => {
    const panel = scrollRef.current;
    if (panel) {
      panel.scrollTo({
        top: messages.length === 0 ? 0 : panel.scrollHeight,
        behavior: messages.length === 0 ? "instant" : "smooth",
      });
    }
  }, [messages]);

  const startQuery = async (rawQuery = draft) => {
    const query = rawQuery.trim();
    if (!query || isStreaming) return;

    const userMessage: ChatMessage = {
      id: makeId(),
      role: "user",
      content: query,
      createdAt: Date.now(),
    };

    const assistantId = makeId();
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "正在建立分析链路...",
      createdAt: Date.now(),
      status: "streaming",
      steps: [],
    };

    const controller = new AbortController();
    setActiveController(controller);
    setDraft("");
    setMessages((current) => [...current, userMessage, assistantMessage]);

    const onEvent = (event: AgentEvent) => {
      setMessages((current) =>
        current.map((message) => {
          if (message.id !== assistantId) return message;

          if (event.type === "progress") {
            return {
              ...message,
              content: event.status === "running" ? `正在执行：${event.step}` : message.content,
              steps: upsertStep(message.steps, event),
            };
          }

          if (event.type === "result") {
            return {
              ...message,
              status: "done",
              content: summarizeResult(event.data),
              result: event.data,
            };
          }

          if (event.type === "route") {
            const routeText =
              event.intent === "database_query"
                ? "已识别为数据库查询，准备执行问数流程..."
                : event.intent === "clarification"
                  ? "已识别为信息不完整的问题。"
                  : "已识别为非数据库问题。";
            return {
              ...message,
              content: routeText,
              route: event,
            };
          }

          if (event.type === "text") {
            return {
              ...message,
              status: "done",
              content: event.content,
            };
          }

          if (event.type === "done") {
            return message.status === "streaming" ? { ...message, status: "done" } : message;
          }

          return {
            ...message,
            status: "error",
            content: "这次查询没有成功。",
            error: event.message,
          };
        }),
      );
    };

    try {
      await streamQuery(query, { signal: controller.signal, onEvent });
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId && message.status === "streaming"
            ? { ...message, status: "done", content: "流程已结束，后端未返回查询结果。" }
            : message,
        ),
      );
    } catch (error) {
      const isAbort = error instanceof DOMException && error.name === "AbortError";
      setMessages((current) =>
        current.map((message) =>
          message.id === assistantId
            ? {
                ...message,
                status: isAbort ? "done" : "error",
                content: isAbort ? "已停止本次查询。" : "无法连接问数接口。",
                error: isAbort ? undefined : error instanceof Error ? error.message : String(error),
              }
            : message,
        ),
      );
    } finally {
      setActiveController(null);
    }
  };

  const stopQuery = () => {
    activeController?.abort();
  };

  const clearConversation = () => {
    if (isStreaming) return;
    setMessages([]);
    setDraft("");
  };

  return (
    <div className="app-shell">
      <div className="ambient-grid" />
      <div className="grain" />

      <div className="workspace-grid">
        <aside className="sidebar">
          <div className="brand-lockup">
            <div className="brand-mark"><Network className="h-5 w-5" aria-hidden="true" /></div>
            <div>
              <div className="brand-name">NEST</div>
              <div className="brand-subtitle">commerce intelligence</div>
            </div>
          </div>

          <div className="sidebar-body">
            <div className="sidebar-kicker">WORKSPACE</div>
            <button
              type="button"
              onClick={clearConversation}
              disabled={isStreaming}
              className="new-session-button"
            >
              <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
              开始一次新分析
            </button>

            <section className="sidebar-section">
              <div className="sidebar-section-title">
                <History className="h-3.5 w-3.5" aria-hidden="true" />
                探索模板
              </div>
              <div className="sidebar-prompts">
                {examples.map((example) => (
                  <button
                    key={example.query}
                    type="button"
                    disabled={isStreaming}
                    onClick={() => startQuery(example.query)}
                    className="sidebar-prompt"
                  >
                    <span className="prompt-dot" />
                    <span className="min-w-0">
                      <span className="sidebar-prompt-label">{example.label}</span>
                      <span className="sidebar-prompt-copy">{example.description}</span>
                    </span>
                  </button>
                ))}
              </div>
            </section>

            <section className="sidebar-section sidebar-system">
              <div className="sidebar-section-title">
                <Layers3 className="h-3.5 w-3.5" aria-hidden="true" />
                系统配置
              </div>
              <div className="system-card">
                <div className="system-row"><span>Intent router</span><span className="mono-text">本地推理</span></div>
                <div className="system-row"><span>Model</span><span className="mono-text">Laya / head</span></div>
                <div className="system-row"><span>Transport</span><span className="mono-text">SSE stream</span></div>
              </div>
            </section>
          </div>

          <div className="sidebar-footer">
            <div className="footer-stat"><span><Activity className="h-3.5 w-3.5" aria-hidden="true" /> 本次完成</span><strong>{completedCount}</strong></div>
            <div className="footer-api"><Server className="h-3.5 w-3.5" aria-hidden="true" /> {API_BASE_URL}</div>
            <div className="sidebar-signature">NEST / 01 · made for decisions</div>
          </div>
        </aside>

        <main className="main-panel">
          <header className="topbar">
            <div className="topbar-title">
              <div className="mobile-brand-mark"><Network className="h-4 w-4" aria-hidden="true" /></div>
              <div className="breadcrumb"><span>NEST</span><b>/</b><strong>决策工作台</strong></div>
            </div>
            <div className="topbar-actions">
              <span className="connection-pill"><Wifi className="h-3.5 w-3.5" aria-hidden="true" /> LOCAL ROUTER</span>
              <button
                type="button"
                onClick={clearConversation}
                disabled={messages.length === 0 || isStreaming}
                className="icon-button"
                title="清空当前会话"
                aria-label="清空当前会话"
              >
                <Eraser className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </header>

          <div ref={scrollRef} className="conversation-scroll">
            {messages.length === 0 ? (
              <EmptyState examples={examples} onUseExample={(example) => setDraft(example)} />
            ) : (
              <div className="conversation-list">
                {messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}
              </div>
            )}
          </div>

          <div className="status-strip">
            <span className={isStreaming ? "status-copy running" : "status-copy"}>
              <span className="status-pulse" />
              {isStreaming ? "ANALYSIS IN PROGRESS" : "READY FOR A BUSINESS QUESTION"}
            </span>
            <span className="status-details"><CircleGauge className="h-3.5 w-3.5" aria-hidden="true" /> intent → route → insight</span>
          </div>
          <Composer
            value={draft}
            disabled={!canSubmit}
            isStreaming={isStreaming}
            onChange={setDraft}
            onSubmit={() => startQuery()}
            onStop={stopQuery}
          />
        </main>
      </div>
    </div>
  );
}
