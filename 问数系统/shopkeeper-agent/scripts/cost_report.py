"""
单任务成本重算 —— 用 logs/query.jsonl 的真实 token × 官方单价，替换 PRD 的拍脑袋估算

背景：PRD 原文写 ¥0.005/次、修订 2 改为按 token 估算 ¥0.006/次，两者都是
假设值（每次输入 500 / 输出 200 tokens）。本脚本用每请求日志里真实采集的
input_tokens / output_tokens 重算，产出可直接贴进 PRD 与面试口述的数字。

价格表（DeepSeek-V4.1-Flash-1017 官方，2026-11-05 Funny 提供）：
  输入（缓存未命中）：空闲 ¥1/M、高峰 ¥2/M
  输入（缓存命中）  ：空闲 ¥0.02/M、高峰 ¥0.04/M
  输出              ：空闲 ¥4/M、高峰 ¥8/M
  → 单价与计算函数的唯一来源是 app/core/cost.py（与 query_log 落盘共用，防两处漂移）

口径假设（报告中同步声明）：
  - 日志无缓存命中标记 → 输入一律按「缓存未命中」计，得到的是成本上界；
  - 时段（空闲/高峰）无法从日志判定 → 两列并排给出，不做单一时段结论。

用法：
  python scripts/cost_report.py                 # 默认 logs/query.jsonl
  python scripts/cost_report.py --log path.jsonl --out outputs/cost_report.md

输出：
  - stdout 摘要表
  - outputs/cost_report.md（默认）
"""
import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Windows 控制台默认 GBK，输出 ✅ 等符号会 UnicodeEncodeError
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.cost import PRICES, cost_yuan  # noqa: E402 — 需先注入项目根路径

# PRD 对照锚点
PRD_ORIGINAL_YUAN = 0.005   # PRD 原文估算
PRD_REVISED_YUAN = 0.006    # 修订 2 按 token 估算（输入 ¥1 + 输出 ¥2 口径）
MONTHLY_QUERIES = 15_000    # PRD 月度成本假设


def percentile(values: list[float], p: float) -> float:
    """线性插值分位数（n=1 时退化为该值）。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    idx = (len(ordered) - 1) * p
    low = int(idx)
    high = min(low + 1, len(ordered) - 1)
    frac = idx - low
    return ordered[low] * (1 - frac) + ordered[high] * frac


def fmt(v: float, nd: int = 0) -> str:
    return f"{v:,.{nd}f}"


def load_rows(log_path: Path) -> list[dict]:
    if not log_path.exists():
        sys.exit(f"日志文件不存在：{log_path}")
    rows = []
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # 坏行跳过，不让整份报告失败
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="按真实 token 重算单任务成本")
    parser.add_argument("--log", default="logs/query.jsonl", help="查询日志路径")
    parser.add_argument("--out", default="outputs/cost_report.md", help="报告输出路径")
    args = parser.parse_args()

    log_path = Path(args.log)
    out_path = Path(args.out)
    rows = load_rows(log_path)
    if not rows:
        sys.exit("日志为空，无法计算")

    # 成本字段（每行都算，含 tokens=0 的拦截行）
    for r in rows:
        r["_in"] = int(r.get("input_tokens") or 0)
        r["_out"] = int(r.get("output_tokens") or 0)
        r["_calls"] = int(r.get("llm_calls") or 0)
        r["_cost_idle"] = cost_yuan(r["_in"], r["_out"], "idle")
        r["_cost_peak"] = cost_yuan(r["_in"], r["_out"], "peak")

    times = [r["time"] for r in rows if r.get("time")]
    with_llm = [r for r in rows if r["_calls"] > 0 or r["_in"] or r["_out"]]
    costs_idle = [r["_cost_idle"] for r in rows]
    costs_peak = [r["_cost_peak"] for r in rows]
    ins = [r["_in"] for r in rows]
    outs = [r["_out"] for r in rows]
    calls = [r["_calls"] for r in rows]

    # 按 outcome 分组
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r.get("outcome") or "unknown"].append(r)

    mean_idle = statistics.mean(costs_idle)
    mean_peak = statistics.mean(costs_peak)

    # ---------- stdout 摘要 ----------
    print(f"数据源：{log_path}（{len(rows)} 条，含 {len(rows) - len(with_llm)} 条零 token 拦截/失败行）")
    if times:
        print(f"时间范围：{min(times)} ~ {max(times)}")
    print(f"单次成本（空闲）：均值 ¥{mean_idle:.4f}  p50 ¥{percentile(costs_idle, 0.5):.4f}  p90 ¥{percentile(costs_idle, 0.9):.4f}")
    print(f"单次成本（高峰）：均值 ¥{mean_peak:.4f}  p50 ¥{percentile(costs_peak, 0.5):.4f}  p90 ¥{percentile(costs_peak, 0.9):.4f}")
    print(f"对照：PRD 原估 ¥{PRD_ORIGINAL_YUAN} / 修订估 ¥{PRD_REVISED_YUAN}")
    print(f"月度推算（{MONTHLY_QUERIES:,} 次）：空闲 ¥{mean_idle * MONTHLY_QUERIES:,.0f} / 高峰 ¥{mean_peak * MONTHLY_QUERIES:,.0f}")

    # ---------- 报告 ----------
    lines = []
    lines.append("# 单任务成本报告（按真实 token 重算）")
    lines.append("")
    lines.append(f"生成时间：{datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"数据源：`{log_path}`（{len(rows)} 条查询流水，含零 token 拦截行）")
    if times:
        lines.append(f"时间范围：{min(times)} ~ {max(times)}")
    lines.append("")
    lines.append("> 用途：替换 PRD「单次调用成本估算」中的假设值（原文 ¥0.005、修订估 ¥0.006），")
    lines.append("> 把估算变成**日志实测**。面试可讲「成本不是拍的，是日志算出来的」。")
    lines.append("")

    lines.append("## 一、价格表（DeepSeek-V4.1-Flash-1017 官方）")
    lines.append("")
    lines.append("| 项目 | 空闲时段 | 高峰时段 |")
    lines.append("|---|---|---|")
    lines.append("| 输入（缓存未命中） | ¥1/M | ¥2/M |")
    lines.append("| 输入（缓存命中） | ¥0.02/M | ¥0.04/M |")
    lines.append("| 输出 | ¥4/M | ¥8/M |")
    lines.append("")
    lines.append("**计价口径**：日志无缓存命中标记，输入一律按「缓存未命中」计 → 本报告为**成本上界**；")
    lines.append("时段（空闲/高峰）无法从日志判定，两列并排给出，不单取一时段下结论。")
    lines.append("")

    lines.append("## 二、真实用量分布（全部 {} 条）".format(len(rows)))
    lines.append("")
    lines.append("| 指标 | 均值 | p50 | p90 | max |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| 输入 tokens | {fmt(statistics.mean(ins))} | {fmt(percentile(ins, 0.5))} | {fmt(percentile(ins, 0.9))} | {fmt(max(ins))} |")
    lines.append(f"| 输出 tokens | {fmt(statistics.mean(outs))} | {fmt(percentile(outs, 0.5))} | {fmt(percentile(outs, 0.9))} | {fmt(max(outs))} |")
    lines.append(f"| LLM 调用次数 | {statistics.mean(calls):.1f} | {percentile(calls, 0.5):.0f} | {percentile(calls, 0.9):.0f} | {max(calls)} |")
    lines.append("")

    lines.append("## 三、单次查询成本（重算）")
    lines.append("")
    lines.append("| 时段 | 均值 | p50 | p90 | max |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| 空闲 | ¥{mean_idle:.4f} | ¥{percentile(costs_idle, 0.5):.4f} | ¥{percentile(costs_idle, 0.9):.4f} | ¥{max(costs_idle):.4f} |")
    lines.append(f"| 高峰 | ¥{mean_peak:.4f} | ¥{percentile(costs_peak, 0.5):.4f} | ¥{percentile(costs_peak, 0.9):.4f} | ¥{max(costs_peak):.4f} |")
    lines.append("")
    lines.append("| 对照 | 单次成本 | 说明 |")
    lines.append("|---|---|---|")
    lines.append(f"| PRD 原文估算 | ¥{PRD_ORIGINAL_YUAN:.3f} | 假设每次输入 500 / 输出 200 tokens |")
    lines.append(f"| PRD 修订 2 估算 | ¥{PRD_REVISED_YUAN:.3f} | 按 6 次调用假设 token 量（输出单价按 ¥2/M，与官方 ¥4/M 不符，见备注） |")
    lines.append(f"| **真实重算（空闲）** | **¥{mean_idle:.4f}** | {len(rows)} 条日志实测 |")
    lines.append(f"| **真实重算（高峰）** | **¥{mean_peak:.4f}** | {len(rows)} 条日志实测 |")
    lines.append("")

    lines.append("## 四、按 outcome 分组")
    lines.append("")
    lines.append("| outcome | 条数 | 平均输入 | 平均输出 | 平均成本（空闲） |")
    lines.append("|---|---|---|---|---|")
    for name in sorted(groups, key=lambda k: -len(groups[k])):
        g = groups[name]
        lines.append(
            f"| {name} | {len(g)} | {fmt(statistics.mean([r['_in'] for r in g]))} "
            f"| {fmt(statistics.mean([r['_out'] for r in g]))} "
            f"| ¥{statistics.mean([r['_cost_idle'] for r in g]):.4f} |"
        )
    lines.append("")

    lines.append(f"## 五、月度成本推算（PRD 假设 {MONTHLY_QUERIES:,} 次/月）")
    lines.append("")
    lines.append("| 时段 | 单次（均值） | 月度 |")
    lines.append("|---|---|---|")
    lines.append(f"| 空闲 | ¥{mean_idle:.4f} | **¥{mean_idle * MONTHLY_QUERIES:,.0f}** |")
    lines.append(f"| 高峰 | ¥{mean_peak:.4f} | **¥{mean_peak * MONTHLY_QUERIES:,.0f}** |")
    lines.append("")

    lines.append("## 六、口径与限制")
    lines.append("")
    lines.append("1. 单价为 DeepSeek-V4.1-Flash-1017 官方价格表（2026-11-05 提供）；换模型需改 `PRICES` 重跑。")
    lines.append("2. 输入按缓存未命中计价 → 报告值是上界；若命中缓存，输入成本可再降（¥0.02~0.04/M）。")
    lines.append("3. 混合日志含不同阶段（含评测跑批、拦截、失败），均值会被零成本行拉低——")
    lines.append(f"   仅统计有 LLM 调用的 {len(with_llm)} 条时，空闲均值为 "
                 f"¥{statistics.mean([r['_cost_idle'] for r in with_llm]):.4f}。")
    lines.append("4. PRD 修订 2 的输出单价写的是 ¥2/M，与官方价格表（空闲 ¥4/M）不符，需同步修正修订指引。")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"报告已写入：{out_path}")


if __name__ == "__main__":
    main()
