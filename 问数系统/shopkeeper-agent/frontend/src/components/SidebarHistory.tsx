/**
 * 侧栏历史会话列表
 * 展示持久化的会话元信息（数据源 M4 接入 localStorage），支持选中切换
 */
import { History } from "lucide-react";
import { cn, relativeTime } from "../lib/format";
import type { SessionMeta } from "../lib/storage";

export type { SessionMeta };

type SidebarHistoryProps = {
  sessions: SessionMeta[];
  activeId: string | null;
  disabled?: boolean;
  onSelect: (id: string) => void;
};

export function SidebarHistory({ sessions, activeId, disabled = false, onSelect }: SidebarHistoryProps) {
  return (
    <section>
      <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold text-secondary">
        <History className="h-3.5 w-3.5" aria-hidden="true" />
        历史会话
      </div>
      {sessions.length === 0 ? (
        <p className="px-1 text-xs leading-5 text-tertiary">暂无历史会话，提问后自动生成</p>
      ) : (
        <div className="space-y-1">
          {sessions.map((session) => (
            <button
              key={session.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelect(session.id)}
              className={cn(
                "w-full rounded-xl px-3 py-2 text-left transition disabled:cursor-not-allowed disabled:opacity-55",
                session.id === activeId ? "bg-surface-muted" : "hover:bg-surface-muted/70",
              )}
            >
              <div className="truncate text-sm text-ink/80">{session.title}</div>
              <div className="mt-0.5 text-[11px] text-tertiary">{relativeTime(session.updatedAt)}</div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
