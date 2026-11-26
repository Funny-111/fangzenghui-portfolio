/**
 * 用户反馈条组件
 * 结果卡 👍/👎（PRD 七.2）：点踩先选原因（召回错/生成错/理解错），
 * 提交到 POST /api/feedback 落盘，作为采纳率埋点数据源
 */
import { CheckCircle2, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";
import { cn } from "../lib/format";

const DOWN_REASONS = ["召回结果不对", "SQL 生成错误", "问题理解有误"] as const;

type FeedbackBarProps = {
  queryId: string;
  query: string;
};

type FeedbackState = "idle" | "picking" | "sent" | "error";

export function FeedbackBar({ queryId, query }: FeedbackBarProps) {
  const [state, setState] = useState<FeedbackState>("idle");
  const [pickedReason, setPickedReason] = useState<string | null>(null);

  const submit = async (rating: "up" | "down", reason?: string) => {
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query_id: queryId, query, rating, reason }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setPickedReason(reason ?? null);
      setState("sent");
    } catch {
      setState("error");
    }
  };

  if (state === "sent") {
    return (
      <div className="mt-2 inline-flex items-center gap-1.5 text-xs text-moss">
        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
        感谢反馈{pickedReason ? `（${pickedReason}）` : ""}
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="mt-2 text-xs text-tomato">
        反馈提交失败，
        <button
          type="button"
          className="underline underline-offset-2"
          onClick={() => setState("idle")}
        >
          重试
        </button>
      </div>
    );
  }

  if (state === "picking") {
    return (
      <div className="mt-2 flex flex-wrap items-center gap-2" aria-label="选择点踩原因">
        <span className="text-xs text-ink/50">哪里不对？</span>
        {DOWN_REASONS.map((reason) => (
          <button
            key={reason}
            type="button"
            onClick={() => submit("down", reason)}
            className="border border-ink/15 bg-white/60 px-2.5 py-1 text-xs text-ink/70 transition hover:border-tomato/40 hover:bg-tomato/5 hover:text-tomato"
          >
            {reason}
          </button>
        ))}
        <button
          type="button"
          onClick={() => setState("idle")}
          className="px-1 text-xs text-ink/40 transition hover:text-ink"
        >
          取消
        </button>
      </div>
    );
  }

  return (
    <div className="mt-2 flex items-center gap-3 text-xs text-ink/45" aria-label="结果反馈">
      <span>这条结果有帮助吗？</span>
      <button
        type="button"
        onClick={() => submit("up")}
        className="inline-flex items-center gap-1 rounded px-2 py-1 transition hover:bg-moss/10 hover:text-moss"
        aria-label="点赞"
        title="有帮助"
      >
        <ThumbsUp className="h-3.5 w-3.5" aria-hidden="true" />
        有帮助
      </button>
      <button
        type="button"
        onClick={() => setState("picking")}
        className="inline-flex items-center gap-1 rounded px-2 py-1 transition hover:bg-tomato/10 hover:text-tomato"
        aria-label="点踩"
        title="没帮助"
      >
        <ThumbsDown className="h-3.5 w-3.5" aria-hidden="true" />
        没帮助
      </button>
    </div>
  );
}
