"""结构化查询日志 —— PRD 七.1 回流设计、七.3 日志脱敏红线

每次提问落一条 JSON 行到 logs/query.jsonl（一行一事件），字段与
PRD 七.1 对齐，供评测回流 / 采纳率统计 / badcase 分析使用。

脱敏红线（PRD 七.3）：因敏感字段被拦截的请求，不落 SQL 与结果原文，
只落拦截类型与问题文本。
"""
import json
from datetime import datetime
from pathlib import Path

from app.conf.app_config import app_config
from app.core.context import request_id_ctx_var
from app.core.cost import cost_yuan
from app.core.log import logger

QUERY_LOG_PATH = Path(app_config.logging.file.path) / "query.jsonl"


def record_query_log(
    *,
    query: str,
    outcome: str,
    elapsed_s: float,
    llm_calls: int,
    input_tokens: int,
    output_tokens: int,
    query_id: str | None = None,
    error_code: str | None = None,
    keywords: list | None = None,
    generated_sql: str | None = None,
    validation_status: str | None = None,
    correction_count: int | None = None,
    matched_tables: list | None = None,
    path: Path | None = None,
) -> None:
    """追加一条查询流水账。脱敏：sensitive_field 拦截不落 SQL 原文。"""
    entry = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "request_id": str(request_id_ctx_var.get()),
        "query_id": query_id,  # 与反馈/结果消息同一 ID，可关联 feedback.jsonl
        "query": query,
        "outcome": outcome,          # success / blocked / clarify / timeout / ...
        "error_code": error_code,
        "elapsed_s": round(elapsed_s, 1),
        "llm_calls": llm_calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        # 单任务成本按真实 token 实算（app/core/cost.py 官方单价），空闲/高峰两列
        "cost_yuan_idle": round(cost_yuan(input_tokens, output_tokens, "idle"), 6),
        "cost_yuan_peak": round(cost_yuan(input_tokens, output_tokens, "peak"), 6),
        "keywords": keywords,
        "generated_sql": generated_sql,
        "validation_status": validation_status,
        "correction_count": correction_count,
        "matched_tables": matched_tables,
    }
    # PRD 七.3 红线：敏感字段拦截 → SQL 原文不落盘
    if error_code == "sensitive_field":
        entry["generated_sql"] = None
        entry["redacted"] = True

    target = path or QUERY_LOG_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.error(f"查询日志落盘失败：{e}")
        return
    logger.info(f"查询日志落盘：outcome={outcome} elapsed={elapsed_s:.1f}s")
