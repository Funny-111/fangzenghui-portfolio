/**
 * 执行步骤组件（可折叠）
 * 默认：6 段业务摘要条（12 个 LangGraph 节点归并），点开才显示完整拓扑图（限高滚动）
 */
import { useState } from "react";
import { Check, ChevronDown, ChevronUp, Circle, LoaderCircle, X } from "lucide-react";
import { cn } from "../lib/format";
import type { ProgressStatus, StepState } from "../types/agent";

type FlowStatus = ProgressStatus | "pending";

type FlowNode = {
  step: string;
  x: number;
  y: number;
  w?: number;
};

const nodes: FlowNode[] = [
  { step: "抽取关键词", x: 410, y: 20 },
  { step: "召回字段信息", x: 150, y: 112 },
  { step: "召回指标信息", x: 410, y: 112 },
  { step: "召回字段取值", x: 670, y: 112 },
  { step: "合并召回信息", x: 410, y: 214 },
  { step: "过滤指标信息", x: 290, y: 318 },
  { step: "过滤表信息", x: 530, y: 318 },
  { step: "添加额外上下文", x: 410, y: 422, w: 176 },
  { step: "生成SQL", x: 410, y: 526 },
  { step: "校验SQL", x: 410, y: 630 },
  { step: "校正SQL", x: 670, y: 630 },
  { step: "执行SQL", x: 410, y: 724 },
];

const connectors = [
  "M410 60 L410 84 L150 84 L150 106",
  "M410 60 L410 106",
  "M410 60 L410 84 L670 84 L670 106",
  "M150 152 L150 178 L410 178 L410 208",
  "M410 152 L410 208",
  "M670 152 L670 178 L410 178 L410 208",
  "M410 254 L410 282 L290 282 L290 312",
  "M410 254 L410 282 L530 282 L530 312",
  "M290 358 L290 386 L410 386 L410 416",
  "M530 358 L530 386 L410 386 L410 416",
  "M410 462 L410 520",
  "M410 566 L410 624",
  "M410 670 L410 718",
  "M488 650 L586 650",
  "M670 670 L670 696 L410 696 L410 718",
];

const branchLabels = [
  { text: "有误", x: 530, y: 642 },
  { text: "无误", x: 366, y: 704 },
];

/** 12 节点归并为 6 段业务步骤；校正SQL 仅在出错分支执行（optional） */
const SEGMENTS: { label: string; steps: string[]; optional?: string[] }[] = [
  { label: "理解问题", steps: ["抽取关键词"] },
  { label: "知识召回", steps: ["召回字段信息", "召回指标信息", "召回字段取值", "合并召回信息"] },
  { label: "信息过滤", steps: ["过滤指标信息", "过滤表信息", "添加额外上下文"] },
  { label: "生成 SQL", steps: ["生成SQL"] },
  { label: "校验修正", steps: ["校验SQL"], optional: ["校正SQL"] },
  { label: "执行 SQL", steps: ["执行SQL"] },
];

function getStatusMap(steps: StepState[]) {
  return steps.reduce<Record<string, StepState>>((map, item) => {
    map[item.step] = item;
    return map;
  }, {});
}

function statusFor(step: string, map: Record<string, StepState>): FlowStatus {
  return map[step]?.status ?? "pending";
}

function segmentStatus(
  segment: (typeof SEGMENTS)[number],
  map: Record<string, StepState>,
): FlowStatus {
  const all = [...segment.steps, ...(segment.optional ?? [])];
  const statuses = all.map((step) => map[step]?.status);
  if (statuses.some((status) => status === "error")) return "error";
  if (statuses.some((status) => status === "running")) return "running";
  if (segment.steps.every((step) => map[step]?.status === "success")) return "success";
  if (statuses.some((status) => status === "success")) return "running";
  return "pending";
}

const SEGMENT_TONE: Record<FlowStatus, string> = {
  pending: "border-line bg-white text-ink/45",
  running: "border-warning/40 bg-warning/10 text-warning",
  success: "border-brand-200 bg-brand-50 text-brand-600",
  error: "border-tomato/35 bg-tomato/10 text-tomato",
};

function StatusIcon({ status }: { status: FlowStatus }) {
  if (status === "running") {
    return <LoaderCircle className="h-3 w-3 animate-spin" aria-hidden="true" />;
  }
  if (status === "success") {
    return <Check className="h-3 w-3" aria-hidden="true" />;
  }
  if (status === "error") {
    return <X className="h-3 w-3" aria-hidden="true" />;
  }
  return <Circle className="h-3 w-3" aria-hidden="true" />;
}

function FlowNodeCard({ node, status }: { node: FlowNode; status: FlowStatus }) {
  const width = node.w ?? 156;

  return (
    <div
      className="absolute -translate-x-1/2"
      style={{ left: node.x, top: node.y, width }}
    >
      <div
        className={cn(
          "flex h-10 items-center gap-2 border px-3 text-sm font-semibold shadow-line transition",
          status === "pending" && "border-line bg-white text-ink/45",
          status === "running" && "border-warning/45 bg-warning/15 text-ink",
          status === "success" && "border-brand-200 bg-brand-50 text-ink",
          status === "error" && "border-tomato/35 bg-tomato/10 text-tomato",
        )}
      >
        <span
          className={cn(
            "grid h-6 w-6 shrink-0 place-items-center rounded-full",
            status === "pending" && "bg-ink/5 text-ink/35",
            status === "running" && "bg-warning/20 text-warning",
            status === "success" && "bg-brand-100 text-brand-600",
            status === "error" && "bg-tomato/15 text-tomato",
          )}
        >
          <StatusIcon status={status} />
        </span>
        <span className="min-w-0 flex-1 truncate">{node.step}</span>
      </div>
    </div>
  );
}

export function StepRail({ steps = [] }: { steps?: StepState[] }) {
  const [open, setOpen] = useState(false);
  if (steps.length === 0) return null;

  const statusMap = getStatusMap(steps);
  const doneCount = SEGMENTS.filter(
    (segment) => segmentStatus(segment, statusMap) === "success",
  ).length;

  return (
    <section className="mt-4 rounded-xl border border-line bg-white px-4 py-3 shadow-card">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold text-ink">执行步骤</div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-tertiary">
            {doneCount}/{SEGMENTS.length}
          </span>
          <button
            type="button"
            onClick={() => setOpen((current) => !current)}
            aria-expanded={open}
            className="inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-secondary transition hover:bg-surface-muted hover:text-ink"
          >
            {open ? (
              <>
                收起
                <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
              </>
            ) : (
              <>
                展开完整流程
                <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
              </>
            )}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {SEGMENTS.map((segment) => {
          const status = segmentStatus(segment, statusMap);
          return (
            <span
              key={segment.label}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
                SEGMENT_TONE[status],
              )}
            >
              <StatusIcon status={status} />
              {segment.label}
            </span>
          );
        })}
      </div>

      {open && (
        <div className="mt-3 max-h-[420px] overflow-auto border-t border-line pt-3">
          <div className="relative mx-auto h-[780px] w-[820px]">
            <svg
              className="pointer-events-none absolute inset-0 h-full w-full"
              viewBox="0 0 820 780"
              fill="none"
              aria-hidden="true"
            >
              <defs>
                <marker
                  id="flow-arrow"
                  markerHeight="8"
                  markerWidth="8"
                  orient="auto"
                  refX="6"
                  refY="4"
                >
                  <path d="M0 0 L8 4 L0 8 Z" fill="rgba(17, 24, 39, 0.55)" />
                </marker>
              </defs>
              {connectors.map((path) => (
                <path
                  key={path}
                  d={path}
                  stroke="rgba(17, 24, 39, 0.45)"
                  strokeWidth="1.5"
                  markerEnd="url(#flow-arrow)"
                />
              ))}
              {branchLabels.map((label) => (
                <text
                  key={label.text}
                  x={label.x}
                  y={label.y}
                  fill="rgba(17, 24, 39, 0.6)"
                  fontSize="13"
                  fontWeight="600"
                >
                  {label.text}
                </text>
              ))}
            </svg>

            {nodes.map((node) => (
              <FlowNodeCard
                key={node.step}
                node={node}
                status={statusFor(node.step, statusMap)}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
