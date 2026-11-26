/**
 * 侧栏数据域卡片
 * 展示已接入的电商经营数仓（真实 meta_config 口径：5 表 / 24 字段 / 2 指标）
 */
import { Database } from "lucide-react";

const TABLES = ["fact_order", "dim_product", "dim_customer", "dim_region", "dim_date"];
const METRICS = ["GMV", "AOV"];

export function SidebarDataDomain() {
  return (
    <section>
      <div className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold text-secondary">
        <Database className="h-3.5 w-3.5" aria-hidden="true" />
        数据域
      </div>
      <div className="rounded-xl border border-line bg-white p-4 shadow-line">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-ink">电商经营数仓</span>
          <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-600">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-500" aria-hidden="true" />
            已同步
          </span>
        </div>
        <p className="mt-1.5 text-xs text-secondary">5 张表 · 24 字段 · 2 个核心指标</p>
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {TABLES.map((table) => (
            <code
              key={table}
              className="rounded bg-surface-muted px-1.5 py-0.5 text-[11px] text-secondary"
            >
              {table}
            </code>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {METRICS.map((metric) => (
            <span
              key={metric}
              className="rounded bg-brand-50 px-1.5 py-0.5 text-[11px] font-medium text-brand-600"
            >
              {metric}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
