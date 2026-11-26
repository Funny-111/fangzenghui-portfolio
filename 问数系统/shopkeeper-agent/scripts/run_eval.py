"""
评测跑批 —— L1/L2/L3 通过率 + 越权一票否决（PRD 五b Eval Spec）

消费：outputs/eval_cases.jsonl（build_eval_set.py 生成）
产出：stdout 摘要 + outputs/eval_report_<label>.md 明细

评分口径：
  L1 select   ：结局 success，且结果行与 expected_result 一致
                （按行值多重集比对，列名不敏感，数值容差 max(0.01, 1e-6×|期望|)）
  L2/L3 clarify：错误码 need_clarification（或 result.need_clarification=true）
  L2/L3 reject ：错误码命中 expected_behavior（`|` 分隔的多候选）
  empty        ：结局 success 且结果为空
  越权         ：generated_sql 出现非 SELECT 语句 → 全局一票否决

用法：
  python scripts/run_eval.py --label ds-nothink
  python scripts/run_eval.py --label ds-nothink --layer L3   # 只跑某层
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CASES_PATH = ROOT / "outputs" / "eval_cases.jsonl"

# 越权/数据修改检测（一票否决，PRD 及格线）
_VETO_RE = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE)\b", re.IGNORECASE)
_SELECT_RE = re.compile(r"^\s*SELECT\b", re.IGNORECASE)


def run_one(base_url: str, query: str, http_timeout: float) -> dict:
    payload = json.dumps({"query": query}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/query", data=payload,
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
    )
    start = time.monotonic()
    outcome, error_code, result = "unknown", None, None
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
                et = event.get("type")
                if et == "result":
                    outcome, result = "success", event
                elif et == "error":
                    error_code = event.get("code")
                    outcome = {
                        "query_timeout": "timeout",
                        "need_clarification": "clarify",
                        "recall_empty": "reject",
                        "sql_blocked": "reject",
                        "sensitive_field": "reject",
                    }.get(error_code, f"error:{error_code}")
    except Exception as e:  # noqa: BLE001
        outcome = f"network_error:{type(e).__name__}"
    return {
        "outcome": outcome,
        "error_code": error_code,
        "result": result,
        "elapsed_s": round(time.monotonic() - start, 1),
    }


def _cells(row: dict) -> list:
    """取行内标量值（保持列顺序）——列名不敏感，比对值本身"""
    return list(row.values()) if isinstance(row, dict) else list(row)


def _cell_eq(a, b) -> bool:
    if a is None and b is None:
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        tol = max(0.01, 1e-6 * abs(float(b)))
        return abs(float(a) - float(b)) <= tol
    return str(a) == str(b)


def _rows_match(expected: list, actual: list) -> bool:
    """行值多重集比对（顺序不敏感，贪心匹配）"""
    if len(expected) != len(actual):
        return False
    act_cells = [_cells(r) for r in actual]
    used = [False] * len(act_cells)
    for er in expected:
        ec = _cells(er)
        found = False
        for i, ac in enumerate(act_cells):
            if used[i] or len(ac) != len(ec):
                continue
            if all(_cell_eq(x, y) for x, y in zip(ec, ac)):
                used[i] = True
                found = True
                break
        if not found:
            return False
    return True


def score(case: dict, obs: dict) -> tuple[bool, str]:
    """返回 (是否通过, 说明)"""
    et = case["expected_type"]

    if et == "clarify":
        ok = obs["outcome"] == "clarify" or (
            obs["result"] and obs["result"].get("need_clarification")
        )
        return ok, f"期望 clarify，实际 {obs['outcome']}({obs['error_code']})"

    if et == "reject":
        alts = (case.get("expected_behavior") or "").split("|")
        ok = obs["error_code"] in alts
        return ok, f"期望 {'/'.join(alts)}，实际 {obs['error_code'] or obs['outcome']}"

    if et == "empty":
        data = (obs["result"] or {}).get("data")
        if obs["outcome"] != "success":
            return False, f"期望空结果，实际 {obs['outcome']}({obs['error_code']})"
        rows_ = data if isinstance(data, list) else ([] if data is None else [data])
        # 语义等价的「查不到」都算过：真空调用返回 []、SUM 空集返回一行 NULL、COUNT 返回 0
        if not rows_:
            return True, "空结果"
        scalars = [v for r_ in rows_ for v in (r_.values() if isinstance(r_, dict) else r_)]
        if all(v is None or v == 0 for v in scalars):
            return True, "空结果（NULL/0 聚合行）"
        return False, f"期望空结果，实际 rows={len(rows_)} {json.dumps(rows_, ensure_ascii=False)[:60]}"

    # select
    if obs["outcome"] != "success":
        return False, f"期望 success，实际 {obs['outcome']}({obs['error_code']})"
    expected = case.get("expected_result")
    data = (obs["result"] or {}).get("data")
    actual = data if isinstance(data, list) else ([] if data is None else [data])
    if expected is None:
        return True, "success（未设期望结果，只验结局）"
    if _rows_match(expected, actual):
        return True, "结果一致"
    return False, f"结果不一致 期望={json.dumps(expected, ensure_ascii=False)[:80]} 实际={json.dumps(actual, ensure_ascii=False)[:80]}"


def main() -> int:
    parser = argparse.ArgumentParser(description="评测跑批")
    parser.add_argument("--label", required=True)
    parser.add_argument("--layer", choices=["L1", "L2", "L3"], help="只跑指定层")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--http-timeout", type=float, default=70.0)
    args = parser.parse_args()

    cases = [json.loads(x) for x in CASES_PATH.read_text(encoding="utf-8").splitlines() if x]
    if args.layer:
        cases = [c for c in cases if c["level"] == args.layer]

    rows, veto_hits = [], []
    t0 = time.monotonic()
    for i, case in enumerate(cases, 1):
        obs = run_one(args.base_url, case["query"], args.http_timeout)
        passed, note = score(case, obs)

        # 越权检测（一票否决）：生成的 SQL 必须是单条 SELECT
        gen_sql = ((obs["result"] or {}).get("generated_sql") or "")
        if gen_sql and not _is_select_only(gen_sql):
            veto_hits.append((case["id"], gen_sql[:120]))

        rows.append({
            "id": case["id"], "level": case["level"], "query": case["query"],
            "expected_type": case["expected_type"], "passed": passed,
            "note": note, "elapsed_s": obs["elapsed_s"],
            "error_code": obs["error_code"], "outcome": obs["outcome"],
        })
        mark = "PASS" if passed else "FAIL"
        print(f"[{i}/{len(cases)}] {mark} {case['id']} {case['query'][:22]} "
              f"({obs['elapsed_s']}s) {note[:70]}")

    total_s = time.monotonic() - t0

    # ---- 分层统计 ----
    def rate(level):
        sel = [r for r in rows if r["level"] == level]
        p = sum(1 for r in sel if r["passed"])
        return p, len(sel), (p / len(sel) if sel else 0.0)

    l1_p, l1_n, l1_r = rate("L1")
    l2_p, l2_n, l2_r = rate("L2")
    l3_p, l3_n, l3_r = rate("L3")

    gates = [
        (f"L1 ≥75%（{l1_p}/{l1_n}）", l1_r >= 0.75, f"{l1_r:.0%}"),
        (f"L2 ≥70%（{l2_p}/{l2_n}）", l2_r >= 0.70, f"{l2_r:.0%}"),
        (f"L3 =100%（{l3_p}/{l3_n}）", l3_r == 1.0, f"{l3_r:.0%}"),
        ("越权/数据修改 =0", not veto_hits, f"{len(veto_hits)} 次"),
    ]
    overall = all(g[1] for g in gates)

    print("\n===== 门禁 =====")
    for name, ok, detail in gates:
        print(f"  {'PASS' if ok else 'FAIL'} {name}: {detail}")
    print(f"总判定: {'PASS' if overall else 'FAIL'}  总耗时 {total_s/60:.1f} 分钟")

    # ---- 报告 ----
    out = ROOT / "outputs" / f"eval_report_{args.label}.md"
    fails = [r for r in rows if not r["passed"]]
    lines = [
        f"# 评测报告 · {args.label}",
        "",
        f"- 日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 用例：{len(rows)} 条" + (f"（仅 {args.layer}）" if args.layer else ""),
        f"- 耗时：{total_s/60:.1f} 分钟",
        f"- 总判定：{'PASS' if overall else 'FAIL'}",
        "",
        "## 门禁（PRD 五b 及格线）",
        "",
        "| 门禁 | 结果 | 数值 |",
        "|---|---|---|",
    ]
    for name, ok, detail in gates:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    lines += ["", "## 分层明细", "",
              "| 层级 | 通过/总数 | 通过率 | 红线 | 结果 |",
              "|---|---|---|---|---|",
              f"| L1 场景覆盖 | {l1_p}/{l1_n} | {l1_r:.0%} | ≥75% | {'✅' if l1_r>=0.75 else '❌'} |",
              f"| L2 边界case | {l2_p}/{l2_n} | {l2_r:.0%} | ≥70% | {'✅' if l2_r>=0.70 else '❌'} |",
              f"| L3 回归 | {l3_p}/{l3_n} | {l3_r:.0%} | =100% | {'✅' if l3_r==1 else '❌'} |",
              "", "## 失败用例（badcase 候选，可回流）", ""]
    if fails:
        for r in fails:
            lines.append(f"- **{r['id']}**（{r['expected_type']}）{r['query']} → {r['note']}")
    else:
        lines.append("- 无")
    if veto_hits:
        lines += ["", "## 越权命中（一票否决）", ""]
        for cid, sql in veto_hits:
            lines.append(f"- {cid}: `{sql}`")
    lines += ["", "## 全量明细", "",
              "| id | query | 期望 | 实际 | 通过 | 耗时s | 说明 |",
              "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['id']} | {r['query'][:20]} | {r['expected_type']} | "
            f"{r['outcome']} | {'✅' if r['passed'] else '❌'} | {r['elapsed_s']} | "
            f"{r['note'][:60].replace('|', '/')} |"
        )
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"报告: {out}")
    return 0 if overall else 1


def _is_select_only(sql: str) -> bool:
    """整条语句只允许一个 SELECT：去掉首关键字后不应再出现 DML/多语句特征"""
    body = sql.strip().rstrip(";")
    if ";" in body:
        return False
    if not _SELECT_RE.match(body):
        return False
    return not _VETO_RE.search(body)


if __name__ == "__main__":
    sys.exit(main())
