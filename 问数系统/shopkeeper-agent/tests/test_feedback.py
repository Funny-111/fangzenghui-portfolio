"""用户反馈测试（PRD 七.2）"""
import json

import pytest
from pydantic import ValidationError

from app.api.schemas.feedback_schema import FeedbackSchema
from app.core.feedback import record_feedback


def _read_lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]


def test_record_feedback_writes_entry(tmp_path):
    target = tmp_path / "feedback.jsonl"
    record_feedback(
        query_id="qid-1", query="华北地区的销售总额是多少",
        rating="up", path=target,
    )
    entry = _read_lines(target)[0]
    assert entry["query_id"] == "qid-1"
    assert entry["rating"] == "up"
    assert entry["reason"] is None
    assert "time" in entry


def test_record_feedback_down_with_reason(tmp_path):
    target = tmp_path / "feedback.jsonl"
    record_feedback(
        query_id="qid-2", query="库存周转率",
        rating="down", reason="SQL 生成错误", path=target,
    )
    entry = _read_lines(target)[0]
    assert entry["rating"] == "down"
    assert entry["reason"] == "SQL 生成错误"


def test_schema_allows_up_without_reason():
    fb = FeedbackSchema(query_id="q", query="query", rating="up")
    assert fb.reason is None


def test_schema_rejects_down_without_reason():
    with pytest.raises(ValidationError):
        FeedbackSchema(query_id="q", query="query", rating="down")


def test_schema_rejects_invalid_rating():
    with pytest.raises(ValidationError):
        FeedbackSchema(query_id="q", query="query", rating="meh")


def test_record_feedback_survives_bad_path(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    record_feedback(
        query_id="q", query="query", rating="up",
        path=blocker / "f.jsonl",
    )
