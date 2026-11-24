import { Bot, Check, Copy, Database, Info, UserRound } from "lucide-react";
import { ResultTable } from "./ResultTable";
import { StepRail } from "./StepRail";
import { cn, formatTime, toClipboardText } from "../lib/format";
import type { ChatMessage, Intent } from "../types/agent";

function intentLabel(intent: Intent) {
  if (intent === "database_query") return "数据库查询";
  if (intent === "clarification") return "需要澄清";
  return "无需查库";
}

function intentIcon(intent: Intent) {
  if (intent === "database_query") return Database;
  return Info;
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  const copy = async () => {
    const text = message.result ? toClipboardText(message.result) : message.content;
    await navigator.clipboard.writeText(text);
  };

  return (
    <article className={cn("message-row", isUser && "is-user")}>
      {!isUser && (
        <div className="message-avatar assistant-avatar">
          <Bot className="h-4 w-4" aria-hidden="true" />
        </div>
      )}

      <div className={cn("message-column", isUser && "user-column")}>
        <div
          className={cn(
            "message-card",
            isUser
              ? "user-message-card"
              : "assistant-message-card",
          )}
        >
          <div className="message-card-header">
            <div className="message-author">
              {isUser ? "YOU" : "NEST ANALYST"}
              {!isUser && message.status === "streaming" && <span className="typing-dot" />}
            </div>
            {!isUser && message.status !== "streaming" && (
              <button
                type="button"
                onClick={copy}
                className="copy-button"
                title="复制"
                aria-label="复制"
              >
                <Copy className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>

          <p className="message-content">{message.content}</p>

          {message.route && (
            <div className={cn("route-badge", `route-${message.route.intent}`)}>
              {(() => {
                const Icon = intentIcon(message.route.intent);
                return <Icon className="h-3.5 w-3.5" aria-hidden="true" />;
              })()}
              <span>{intentLabel(message.route.intent)}</span>
              <span className="route-divider" />
              <span>{(message.route.confidence * 100).toFixed(1)}% match</span>
            </div>
          )}

          {message.error && (
            <div className="message-error">
              {message.error}
            </div>
          )}

          {!isUser && message.result !== undefined && <ResultTable data={message.result} />}
          {!isUser && message.route?.intent === "database_query" && (
            <details className="execution-details">
              <summary>LangGraph 执行轨迹</summary>
              <StepRail steps={message.steps} />
            </details>
          )}

          <div
            className="message-time"
          >
            <span>{formatTime(message.createdAt)}</span>
            {!isUser && message.status === "done" && <Check className="h-3 w-3" aria-hidden="true" />}
          </div>
        </div>
      </div>

      {isUser && (
        <div className="message-avatar user-avatar">
          <UserRound className="h-4 w-4" aria-hidden="true" />
        </div>
      )}
    </article>
  );
}
