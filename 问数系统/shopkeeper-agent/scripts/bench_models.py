"""
链路延迟与稳定性基准测试 —— 「调预算/优化 vs 换模型」对比实验工具

背景（面试素材）：问数链路为 3~4 轮串行 LLM 往返，MiMo API 延迟抖动大，
原 30s 总预算下超时频繁。本脚本对同一组查询跑 N 轮，产出延迟/稳定性对比数据。

用法：
  # 基线（当前模型，MiMo）
  python scripts/bench_models.py --label mimo --runs 2

  # 对比组（换模型）：通过环境变量切换，改完需重启后端
  #   set LLM_PROVIDER=openai
  #   set LLM_MODEL=<模型名>
  #   set LLM_BASE_URL=<接口地址>
  #   set LLM_API_KEY=<密钥>
  #   重启 uvicorn 后：
  python scripts/bench_models.py --label alt --runs 2

输出：
  - stdout 摘要表
  - outputs/bench_<label>.md 明细（含「若按 30s 预算的超时率」反事实计算）
  - 成本（token）不在本脚本内：后端日志 logs/app.log 每请求一行「查询结束：… tokens(...)」
"""
import argparse
import json
import statistics
import time
import urllib.request
from datetime import datetime
from pathlib import Path

QUERIES = [
    ("主链-简单", "华北地区的销售总额是多少"),
    ("主链-多条件", "统计 2025 年第一季度各大区的 GMV，并按 GMV 从高到低排序"),
    ("边界-澄清", "销售额怎么样"),
    ("边界-拒答", "各门店的库存周转率是多少"),
]


def run_one(base_url: str, query: str, http_timeout: float) -> dict:
    """执行一次查询，解析 SSE，返回结局与耗时"""
    payload = json.dumps({"query": query}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/query",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    start = time.monotonic()
    outcome = "unknown"
    error_code = None
    try:
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    event = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                etype = event.get("type")
                if etype == "result":
                    outcome = "success"
                elif etype == "error":
                    error_code = event.get("code")
                    outcome = {
                        "query_timeout": "timeout",
                        "need_clarification": "clarify",
                        "recall_empty": "recall_empty",
                    }.get(error_code, f"error:{error_code}")
    except Exception as e:  # noqa: BLE001 — 网络层失败也记为结局
        outcome = f"network_error:{type(e).__name__}"
    return {
        "outcome": outcome,
        "elapsed_s": round(time.monotonic() - start, 1),
        "error_code": error_code,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="问数链路延迟与稳定性基准测试")
    parser.add_argument("--label", required=True, help="实验标签，如 mimo / alt")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=2, help="每条查询重复次数")
    parser.add_argument("--http-timeout", type=float, default=90.0, help="单请求 HTTP 超时（需大于后端总预算）")
    args = parser.parse_args()

    rows = []
    print(f"== bench label={args.label} runs={args.runs} start={datetime.now().isoformat(timespec='seconds')} ==")
    for name, query in QUERIES:
        for i in range(1, args.runs + 1):
            r = run_one(args.base_url, query, args.http_timeout)
            r.update({"query_name": name, "run": i, "query": query})
            rows.append(r)
            print(f"  [{name} #{i}] outcome={r['outcome']} elapsed={r['elapsed_s']}s")

    completed = [r["elapsed_s"] for r in rows if r["outcome"] in ("success", "clarify", "recall_empty")]
    n = len(rows)
    by_outcome: dict[str, int] = {}
    for r in rows:
        by_outcome[r["outcome"]] = by_outcome.get(r["outcome"], 0) + 1
    timeout_rate = by_outcome.get("timeout", 0) / n
    over30 = sum(1 for e in completed if e > 30) / len(completed) if completed else 0.0
    p50 = statistics.median(completed) if completed else float("nan")

    lines = [
        f"# 基准测试 · {args.label}",
        "",
        f"- 时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 后端：{args.base_url}，每条查询 {args.runs} 轮，共 {n} 次请求",
        f"- 结局分布：{json.dumps(by_outcome, ensure_ascii=False)}",
        f"- 实际超时率（后端预算内）：{timeout_rate:.0%}",
        f"- 完成请求耗时 p50：{p50:.1f}s",
        f"- **反事实：若按旧 30s 预算，完成请求中 {over30:.0%} 会超时**",
        "",
        "| 查询 | 轮次 | 结局 | 耗时(s) |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['query_name']} | {r['run']} | {r['outcome']} | {r['elapsed_s']} |")

    out_dir = Path(__file__).parents[1] / "outputs"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / f"bench_{args.label}.md"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n超时率={timeout_rate:.0%}  p50={p50:.1f}s  若按30s预算={over30:.0%}会超时")
    print(f"明细已写入 {out_file}")


if __name__ == "__main__":
    main()
