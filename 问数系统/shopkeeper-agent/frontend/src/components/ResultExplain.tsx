/**
 * AI 解析面板组件
 * 展示 PRD 五a.3 输出格式中的可解释字段：生成的 SQL、校验/纠错/置信状态、
 * 关键词与三路召回证据（matched_*）、unclear 待确认提示
 */
import { Check, Copy, Sparkles } from "lucide-react";
import { useState } from "react";
import { cn, toClipboardText } from "../lib/format";
import type { ResultPayload } from "../types/agent";

function Chip({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "ok" | "warn" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 border px-2 py-0.5 text-xs",
        tone === "ok" && "border-moss/30 bg-moss/10 text-moss",
        tone === "warn" && "border-tomato/30 bg-tomato/10 text-tomato",
        tone === "neutral" && "border-ink/15 bg-ink/5 text-ink/65",
      )}
    >
      {children}
    </span>
  );
}

function confidenceLabel(value?: string) {
  if (value === "high") return "高";
  if (value === "medium") return "中";
  if (value === "low") return "低";
  return value ?? "-";
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-ink/45">{label}</div>
      {children}
    </div>
  );
}

export function ResultExplain({ payload }: { payload: ResultPayload }) {
  const [copied, setCopied] = useState(false);

  const copySql = async () => {
    if (!payload.generated_sql) return;
    await navigator.clipboard.writeText(payload.generated_sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const hasEvidence =
    (payload.keywords?.length ?? 0) > 0 ||
    (payload.matched_tables?.length ?? 0) > 0 ||
    (payload.matched_columns?.length ?? 0) > 0 ||
    (payload.matched_metrics?.length ?? 0) > 0 ||
    (payload.matched_values?.length ?? 0) > 0;

  return (
    <section className="mt-3 rounded-xl border border-line bg-white px-4 py-3 shadow-card" aria-label="查询解析">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-ink/60">
          <Sparkles className="h-3.5 w-3.5 text-moss" aria-hidden="true" />
          查询解析
        </span>
        <Chip tone={payload.validation_status === "pass" ? "ok" : "warn"}>
          SQL 校验 {payload.validation_status === "pass" ? "通过" : payload.validation_status ?? "-"}
        </Chip>
        <Chip tone={(payload.correction_count ?? 0) > 0 ? "warn" : "neutral"}>
          自动修正 {payload.correction_count ?? 0} 次
        </Chip>
        <Chip>置信度 {confidenceLabel(payload.confidence)}</Chip>
        <Chip tone="ok">
          {payload.execution_status === "success" ? "执行成功" : `执行 ${payload.execution_status ?? "-"}`}
        </Chip>
      </div>

      {payload.generated_sql && (
        <div className="mb-3">
          <div className="mb-1.5 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-[0.12em] text-ink/45">生成 SQL</span>
            <button
              type="button"
              onClick={copySql}
              className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-ink/50 transition hover:bg-ink/5 hover:text-ink"
              title="复制 SQL"
            >
              {copied ? <Check className="h-3 w-3" aria-hidden="true" /> : <Copy className="h-3 w-3" aria-hidden="true" />}
              {copied ? "已复制" : "复制"}
            </button>
          </div>
          <pre className="overflow-x-auto border border-ink/10 bg-surface-sunken px-3 py-2 font-mono text-[13px] leading-6 text-ink">
            {payload.generated_sql}
          </pre>
        </div>
      )}

      {(payload.unclear?.length ?? 0) > 0 && (
        <div className="mb-3 border border-warning/30 bg-warning/10 px-3 py-2 text-xs leading-5 text-warning">
          {payload.unclear!.map((note) => (
            <p key={note}>{note}</p>
          ))}
        </div>
      )}

      {hasEvidence && (
        <details className="group">
          <summary className="cursor-pointer list-none text-xs font-semibold uppercase tracking-[0.12em] text-ink/45 transition hover:text-ink">
            <span className="mr-1 inline-block transition group-open:rotate-90">▸</span>
            检索依据
          </summary>
          <div className="mt-2.5 space-y-3">
            {(payload.keywords?.length ?? 0) > 0 && (
              <Section label="关键词">
                <div className="flex flex-wrap gap-1.5">
                  {payload.keywords!.map((kw) => (
                    <Chip key={kw}>{kw}</Chip>
                  ))}
                </div>
              </Section>
            )}

            {(payload.matched_tables?.length ?? 0) > 0 && (
              <Section label="命中表">
                <div className="flex flex-wrap gap-1.5">
                  {payload.matched_tables!.map((t) => (
                    <Chip key={t} tone="ok">
                      {t}
                    </Chip>
                  ))}
                </div>
              </Section>
            )}

            {(payload.matched_columns?.length ?? 0) > 0 && (
              <Section label="命中字段">
                <div className="flex flex-wrap gap-1.5">
                  {payload.matched_columns!.map((c) => (
                    <Chip key={c}>{c}</Chip>
                  ))}
                </div>
              </Section>
            )}

            {(payload.matched_metrics?.length ?? 0) > 0 && (
              <Section label="命中指标">
                <ul className="space-y-1 text-sm text-ink/75">
                  {payload.matched_metrics!.map((m) => (
                    <li key={m.name} className="flex flex-wrap gap-x-2">
                      <span className="font-medium text-ink">{m.name}</span>
                      {m.source && <span className="text-xs text-ink/50">口径来源：{m.source}</span>}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {(payload.matched_values?.length ?? 0) > 0 && (
              <Section label="命中取值">
                <div className="flex flex-wrap gap-1.5">
                  {payload.matched_values!.map((v) => (
                    <Chip key={`${v.value}-${v.column ?? ""}`}>
                      {v.value}
                      {v.column && <span className="text-ink/40"> → {v.column}</span>}
                    </Chip>
                  ))}
                </div>
              </Section>
            )}
          </div>
        </details>
      )}
    </section>
  );
}
