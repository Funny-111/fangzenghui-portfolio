/**
 * 澄清追问面板组件
 * PRD 四.4：用户问题模糊时前端展示提示，引导用户补全信息；
 * need_clarification=true 的 error 事件渲染为本面板，补充后带上下文重新提问
 */
import { HelpCircle, SendHorizonal } from "lucide-react";
import { useState } from "react";

const suggestions = ["时间范围：最近一个月", "统计口径：按销售额统计", "维度：按大区拆分"];

type ClarifyPanelProps = {
  question: string;
  disabled?: boolean;
  onSubmit: (supplement: string) => void;
};

export function ClarifyPanel({ question, disabled = false, onSubmit }: ClarifyPanelProps) {
  const [text, setText] = useState("");

  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSubmit(value);
    setText("");
  };

  return (
    <section
      className="mt-3 rounded-xl border border-warning/35 bg-warning/8 px-4 py-3"
      aria-label="需要补充信息"
    >
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-warning">
        <HelpCircle className="h-4 w-4" aria-hidden="true" />
        需要补充一点信息
      </div>
      <p className="mb-3 text-sm leading-6 text-ink/80">{question}</p>

      <div className="mb-2 flex flex-wrap gap-1.5">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            disabled={disabled}
            onClick={() => setText(suggestion)}
            className="border border-warning/30 bg-white/70 px-2 py-1 text-xs text-warning transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {suggestion}
          </button>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          value={text}
          disabled={disabled}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") submit();
          }}
          placeholder="补充信息后继续查询…"
          className="min-h-9 flex-1 border border-ink/15 bg-white/80 px-3 text-sm text-ink outline-none transition placeholder:text-ink/35 focus:border-warning/50 disabled:opacity-55"
        />
        <button
          type="button"
          disabled={disabled || !text.trim()}
          onClick={submit}
          className="inline-flex min-h-9 items-center gap-1.5 bg-ink px-3 text-sm font-semibold text-parchment transition hover:bg-soot disabled:cursor-not-allowed disabled:bg-ink/30"
        >
          继续查询
          <SendHorizonal className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </div>
      <p className="mt-2 text-xs text-ink/45">补充后将基于原问题重新查询。</p>
    </section>
  );
}
