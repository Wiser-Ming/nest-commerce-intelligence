import { ArrowUpRight, BarChart3, BrainCircuit, Database, Sparkles } from "lucide-react";

export type ExamplePrompt = {
  query: string;
  label: string;
  description: string;
};

type EmptyStateProps = {
  examples: ExamplePrompt[];
  onUseExample: (example: string) => void;
};

const highlights = [
  { label: "意图分流", copy: "先判断，再调用工具", icon: BrainCircuit, tone: "lime" },
  { label: "SQL 闭环", copy: "从自然语言到结果表", icon: Database, tone: "blue" },
  { label: "流式洞察", copy: "看见每一步如何发生", icon: BarChart3, tone: "orange" },
];

export function EmptyState({ examples, onUseExample }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <section className="hero-card">
        <div className="hero-copy">
          <div className="hero-eyebrow"><span className="eyebrow-dot" /> ROUTING-FIRST ANALYTICS</div>
          <h1>把业务问题，<br /><em>变成可执行的判断。</em></h1>
          <p>
            NEST 先理解问题，再选择最合适的分析路径。让 SQL、检索和模型资源只在真正需要时被调用。
          </p>
          <div className="hero-meta">
            <span><Sparkles className="h-3.5 w-3.5" aria-hidden="true" /> Laya intent router</span>
            <span><Database className="h-3.5 w-3.5" aria-hidden="true" /> SQL Agent ready</span>
          </div>
        </div>
        <div className="hero-visual" aria-hidden="true">
          <div className="visual-label">LIVE / DECISION LAYER</div>
          <div className="signal-orbit orbit-one"><span /></div>
          <div className="signal-orbit orbit-two"><span /></div>
          <div className="signal-core"><span className="core-pulse" /><span>01</span></div>
          <div className="visual-readout readout-top">intent <b>→</b> route</div>
          <div className="visual-readout readout-bottom">query / insight / action</div>
          <div className="signal-bars"><i /><i /><i /><i /><i /></div>
        </div>
      </section>

      <div className="section-heading">
        <div>
          <span className="section-eyebrow">SYSTEM CAPABILITIES</span>
          <h2>一套更克制的问数工作流</h2>
        </div>
        <span className="section-index">01 — 03</span>
      </div>

      <section className="capability-grid">
        {highlights.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className={`capability-card ${item.tone}`}>
              <div className="capability-icon"><Icon className="h-5 w-5" aria-hidden="true" /></div>
              <div>
                <div className="capability-label">{item.label}</div>
                <div className="capability-copy">{item.copy}</div>
              </div>
              <ArrowUpRight className="capability-arrow h-4 w-4" aria-hidden="true" />
            </div>
          );
        })}
      </section>

      <div className="section-heading prompts-heading">
        <div>
          <span className="section-eyebrow">START WITH A SIGNAL</span>
          <h2>从一个业务问题开始</h2>
        </div>
        <span className="section-note">点击模板，或直接在下方输入</span>
      </div>

      <section className="prompt-grid">
        {examples.map((example, index) => (
          <button
            key={example.query}
            type="button"
            onClick={() => onUseExample(example.query)}
            className="prompt-card"
          >
            <span className="prompt-number">0{index + 1}</span>
            <span className="prompt-card-body">
              <span className="prompt-card-label">{example.label}</span>
              <span className="prompt-card-description">{example.description}</span>
              <span className="prompt-card-query">{example.query}</span>
            </span>
            <ArrowUpRight className="prompt-arrow h-5 w-5" aria-hidden="true" />
          </button>
        ))}
      </section>
    </div>
  );
}
