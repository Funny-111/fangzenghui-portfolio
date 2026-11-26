/**
 * 顶栏：产品名 + 服务状态 pill + 当前会话标题 + 清空
 */
import { BarChart3, Eraser } from "lucide-react";
import { cn } from "../lib/format";

type TopBarProps = {
  sessionTitle: string;
  isStreaming: boolean;
  canClear: boolean;
  onClear: () => void;
};

export function TopBar({ sessionTitle, isStreaming, canClear, onClear }: TopBarProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-white px-4 lg:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-ink text-parchment lg:hidden">
          <BarChart3 className="h-4 w-4" aria-hidden="true" />
        </div>
        <span className="text-sm font-semibold text-ink">电商问数</span>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
            isStreaming
              ? "border-warning/30 bg-warning/10 text-warning"
              : "border-brand-200 bg-brand-50 text-brand-600",
          )}
        >
          <span
            className={cn("h-1.5 w-1.5 rounded-full bg-current", isStreaming && "animate-pulse")}
            aria-hidden="true"
          />
          {isStreaming ? "查询中" : "服务在线"}
        </span>
      </div>
      <div className="flex min-w-0 items-center gap-3">
        <span className="hidden max-w-[260px] truncate text-xs text-secondary sm:block">{sessionTitle}</span>
        <button
          type="button"
          onClick={onClear}
          disabled={!canClear}
          className="grid h-9 w-9 shrink-0 place-items-center rounded-full text-secondary transition hover:bg-surface-muted hover:text-ink disabled:cursor-not-allowed disabled:opacity-35"
          title="清空"
          aria-label="清空"
        >
          <Eraser className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
