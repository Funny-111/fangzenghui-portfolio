/**
 * 侧栏：顶栏之外的全局导航
 * 品牌区 + 新会话 + 历史会话 + 推荐问题 + 数据域 + 服务目标
 */
import { BarChart3, MessageSquarePlus, Sparkles } from "lucide-react";
import { SidebarDataDomain } from "./SidebarDataDomain";
import { SidebarHistory, type SessionMeta } from "./SidebarHistory";

export type { SessionMeta };

type SidebarProps = {
  examples: string[];
  sessions: SessionMeta[];
  activeId: string | null;
  isStreaming: boolean;
  onNewSession: () => void;
  onUseExample: (question: string) => void;
  onSelectSession: (id: string) => void;
};

export function Sidebar({
  examples,
  sessions,
  activeId,
  isStreaming,
  onNewSession,
  onUseExample,
  onSelectSession,
}: SidebarProps) {
  return (
    <aside className="hidden min-h-0 flex-col border-r border-line bg-surface-subtle lg:flex">
      <div className="flex items-center gap-3 border-b border-line px-5 py-4">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-ink text-parchment">
          <BarChart3 className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0">
          <div className="text-base font-semibold tracking-[0.02em] text-ink">电商问数</div>
          <div className="text-xs text-secondary">经营数据分析</div>
        </div>
      </div>

      <div className="px-4 pt-4">
        <button
          type="button"
          onClick={onNewSession}
          disabled={isStreaming}
          aria-label="新会话"
          className="flex h-10 w-full items-center justify-center gap-2 rounded-lg border border-line bg-white text-sm font-medium text-ink shadow-line transition hover:bg-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
          新会话
        </button>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4">
        <SidebarHistory sessions={sessions} activeId={activeId} disabled={isStreaming} onSelect={onSelectSession} />

        <section>
          <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold text-secondary">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            推荐问题
          </div>
          <div className="space-y-2">
            {examples.map((example) => (
              <button
                key={example}
                type="button"
                disabled={isStreaming}
                onClick={() => onUseExample(example)}
                className="w-full rounded-lg border border-line bg-white/70 px-3 py-2.5 text-left text-sm leading-5 text-ink/75 transition hover:border-brand-200 hover:bg-white disabled:cursor-not-allowed disabled:opacity-55"
              >
                {example}
              </button>
            ))}
          </div>
        </section>

        <SidebarDataDomain />
      </div>

      <div className="border-t border-line px-4 py-3">
        <div className="mb-1 text-[11px] font-semibold text-tertiary">服务目标</div>
        <div className="text-[11px] leading-5 text-tertiary">SQL 成功率 ≥85% · 采纳率 ≥60% · 单次 ≤8s</div>
      </div>
    </aside>
  );
}
