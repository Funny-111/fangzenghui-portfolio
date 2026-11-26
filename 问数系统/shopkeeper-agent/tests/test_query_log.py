"""结构化查询日志测试（PRD 七.1 回流 + 七.3 脱敏红线）"""
import json
from uuid import uuid4

from app.core.context import request_id_ctx_var
from app.core.query_log import record_query_log


def _read_lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def _base_kwargs(**over):
    kwargs = dict(
        query="华北地区的销售总额是多少",
        outcome="success",
        elapsed_s=6.1,
        llm_calls=6,
        input_tokens=1196,
        output_tokens=118,
        error_code=None,
        keywords=["华北", "销售总额"],
        generated_sql="SELECT SUM(amount) FROM fact_order",
        validation_status="pass",
        correction_count=0,
        matched_tables=["fact_order", "dim_region"],
    )
    kwargs.update(over)
    return kwargs


def test_record_success_entry_has_all_fields(tmp_path):
    target = tmp_path / "query.jsonl"
    record_query_log(path=target, **_base_kwargs())
    entry = _read_lines(target)[0]
    for key in ("time", "request_id", "query", "outcome", "error_code",
                "elapsed_s", "llm_calls", "input_tokens", "output_tokens",
                "cost_yuan_idle", "cost_yuan_peak",
                "keywords", "generated_sql", "validation_status",
                "correction_count", "matched_tables"):
        assert key in entry, f"缺字段 {key}"
    assert entry["outcome"] == "success"
    assert entry["generated_sql"].startswith("SELECT")
    # 成本 = 真实 token × 官方单价（空闲：输入 ¥1/M、输出 ¥4/M）
    assert entry["cost_yuan_idle"] == round(1196 * 1e-6 * 1 + 118 * 1e-6 * 4, 6)
    assert entry["cost_yuan_peak"] == round(1196 * 1e-6 * 2 + 118 * 1e-6 * 8, 6)


def test_sensitive_field_redacts_sql(tmp_path):
    # PRD 七.3 红线：敏感字段拦截不落 SQL 原文
    target = tmp_path / "query.jsonl"
    record_query_log(path=target, **_base_kwargs(
        outcome="flow_error:sensitive_field",
        error_code="sensitive_field",
        generated_sql="SELECT phone FROM user",
        validation_status=None,
        correction_count=None,
        matched_tables=None,
        keywords=None,
    ))
    entry = _read_lines(target)[0]
    assert entry["generated_sql"] is None
    assert entry["redacted"] is True
    assert entry["error_code"] == "sensitive_field"


def test_timeout_entry_keeps_cost_metrics(tmp_path):
    target = tmp_path / "query.jsonl"
    record_query_log(path=target, **_base_kwargs(
        outcome="timeout", error_code="query_timeout",
        keywords=None, generated_sql=None, validation_status=None,
        correction_count=None, matched_tables=None,
    ))
    entry = _read_lines(target)[0]
    # 超时也要留账：烧了多少 token 是成本分析的数据源
    assert entry["outcome"] == "timeout"
    assert entry["llm_calls"] == 6
    assert entry["output_tokens"] == 118


def test_record_with_uuid_request_id(tmp_path):
    target = tmp_path / "query.jsonl"
    token = request_id_ctx_var.set(uuid4())
    try:
        record_query_log(path=target, **_base_kwargs())
    finally:
        request_id_ctx_var.reset(token)
    assert isinstance(_read_lines(target)[0]["request_id"], str)


def test_record_survives_bad_path(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    record_query_log(path=blocker / "q.jsonl", **_base_kwargs())
