/**
 * 聊天消息组件
 * 用户消息：右侧深色圆角气泡；助手消息：品牌头像 + 无框正文 + 独立子卡片（报告式排版）
 */
import { Bot, Copy, UserRound } from "lucide-react";
import { ClarifyPanel } from "./ClarifyPanel";
import { FeedbackBar } from "./FeedbackBar";
import { ResultExplain } from "./ResultExplain";
import { ResultTable } from "./ResultTable";
import { StepRail } from "./StepRail";
import { cn, formatTime, toClipboardText } from "../lib/format";
import type { ChatMessage } from "../types/agent";

type MessageBubbleProps = {
  message: ChatMessage;
  /** 澄清面板提交补充信息后，携带原问题+补充重新提问（PRD 四.4） */
  onClarify?: (supplement: string) => void;
};

export function MessageBubble({ message, onClarify }: MessageBubbleProps) {
  const isUser = message.role === "user";

  const copy = async () => {
    const text = message.result ? toClipboardText(message.result) : message.content;
    await navigator.clipboard.writeText(text);
  };

  if (isUser) {
    return (
      <article className="group flex justify-end gap-3">
        <div className="flex max-w-[760px] justify-end">
          <div className="relative rounded-xl bg-ink px-5 py-4 text-parchment shadow-line">
            <p className="whitespace-pre-wrap text-[15px] leading-7">{message.content}</p>
            <div className="mt-3 text-right text-xs text-parchment/55">
              {formatTime(message.createdAt)}
            </div>
          </div>
        </div>
        <div className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-ink text-parchment">
          <UserRound className="h-4 w-4" aria-hidden="true" />
        </div>
      </article>
    );
  }

  return (
    <article className="group flex gap-3">
      <div className="mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-brand-500 text-white">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <p className="whitespace-pre-wrap text-[15px] leading-7 text-ink">{message.content}</p>
          {message.status !== "streaming" && (
            <button
              type="button"
              onClick={copy}
              className="shrink-0 rounded-lg p-1.5 text-tertiary opacity-0 outline-none transition hover:bg-surface-muted hover:text-ink focus:opacity-100 focus:ring-2 focus:ring-brand-500/40 group-hover:opacity-100"
              title="复制"
              aria-label="复制"
            >
              <Copy className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>

        {message.status === "clarifying" && message.clarification && (
          <ClarifyPanel
            question={message.clarification}
            disabled={!onClarify}
            onSubmit={(supplement) => onClarify?.(supplement)}
          />
        )}

        {message.error && (
          <div className="mt-3 rounded-xl border border-tomato/30 bg-tomato/10 px-3 py-2 text-sm text-tomato">
            {message.error}
          </div>
        )}

        <StepRail steps={message.steps} />
        {message.result !== undefined && <ResultTable data={message.result} />}
        {message.resultPayload && <ResultExplain payload={message.resultPayload} />}
        {message.status === "done" && message.resultPayload?.query_id && message.originalQuery && (
          <FeedbackBar queryId={message.resultPayload.query_id} query={message.originalQuery} />
        )}

        <div className="mt-3 text-xs text-tertiary">{formatTime(message.createdAt)}</div>
      </div>
    </article>
  );
}
