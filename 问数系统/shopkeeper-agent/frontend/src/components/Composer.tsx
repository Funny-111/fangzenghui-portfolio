/**
 * 聊天输入区（双形态）
 * variant="hero"：欢迎页大输入卡（空状态渲染，含模型/数据域展示钮）
 * variant="bar"：会话底部输入条（有消息时渲染）
 * 两形态互斥渲染，保证页面任一时刻只有一个 textarea（截图脚本依赖）
 */
import { ArrowUp, Square } from "lucide-react";
import { FormEvent, KeyboardEvent, useRef } from "react";
import { cn } from "../lib/format";

const PLACEHOLDER = "例如：统计 2025 年 Q1 各大区 GMV，并按销售额排序";

type ComposerProps = {
  variant?: "bar" | "hero";
  value: string;
  disabled: boolean;
  isStreaming: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
};

export function Composer({
  variant = "bar",
  value,
  disabled,
  isStreaming,
  onChange,
  onSubmit,
  onStop,
}: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!disabled) onSubmit();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!disabled) onSubmit();
    }
  };

  const sendButton = (
    <button
      type={isStreaming ? "button" : "submit"}
      onClick={isStreaming ? onStop : undefined}
      disabled={!isStreaming && disabled}
      title={isStreaming ? "停止" : "发送"}
      aria-label={isStreaming ? "停止" : "发送"}
      className={cn(
        "grid shrink-0 place-items-center text-white transition focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:ring-offset-2",
        variant === "hero" ? "h-10 w-10 rounded-xl" : "h-11 w-11 rounded-full",
        isStreaming
          ? "bg-tomato hover:bg-tomato/90"
          : "bg-ink hover:bg-soot disabled:cursor-not-allowed disabled:bg-ink/25",
      )}
    >
      {isStreaming ? (
        <Square className="h-4 w-4 fill-current" aria-hidden="true" />
      ) : (
        <ArrowUp className="h-5 w-5" aria-hidden="true" />
      )}
    </button>
  );

  if (variant === "hero") {
    return (
      <form onSubmit={submit} className="rounded-2xl border border-line bg-white p-3 shadow-panel">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          rows={3}
          placeholder={PLACEHOLDER}
          className="max-h-48 min-h-[72px] w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-6 text-ink outline-none placeholder:text-tertiary"
        />
        <div className="mt-1 flex items-center justify-between gap-3 border-t border-line px-1 pt-3">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full border border-line bg-surface-subtle px-2.5 py-1 text-secondary">
              分析模型
            </span>
            <span className="rounded-full border border-line bg-surface-subtle px-2.5 py-1 text-secondary">
              经营数仓
            </span>
          </div>
          {sendButton}
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={submit} className="border-t border-line bg-white/80 px-4 py-4 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-end gap-3 rounded-xl border border-line bg-white p-2 shadow-line">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder={PLACEHOLDER}
          className="max-h-36 min-h-11 flex-1 resize-none bg-transparent px-2 py-3 text-[15px] leading-6 text-ink outline-none placeholder:text-tertiary"
        />
        {sendButton}
      </div>
    </form>
  );
}
