"""
generate_sql 输出解析测试（PRD 四.4：生成失败 / 澄清追问 / 拒答）
"""
import pytest

from app.agent.generation_parser import parse_generation_output
from app.core.errors import ClarificationNeededError, RecallEmptyError, SqlGenerationError


class TestParseGenerationOutput:
    """LLM 输出四形态：SQL / CLARIFY / REJECT / 空"""

    def test_normal_sql_returned(self):
        sql = "SELECT SUM(order_amount) FROM fact_order"
        assert parse_generation_output(sql) == sql

    def test_normal_sql_with_whitespace_stripped(self):
        assert parse_generation_output("  SELECT 1  \n") == "SELECT 1"

    def test_empty_output_raises_sql_generation_error(self):
        with pytest.raises(SqlGenerationError):
            parse_generation_output("")
        with pytest.raises(SqlGenerationError):
            parse_generation_output(None)
        with pytest.raises(SqlGenerationError):
            parse_generation_output("   \n  ")

    def test_clarify_raises_with_dynamic_message(self):
        with pytest.raises(ClarificationNeededError) as exc:
            parse_generation_output("CLARIFY: 请补充时间范围和对比维度")
        assert exc.value.message == "请补充时间范围和对比维度"
        assert exc.value.need_clarification is True
        assert exc.value.code == "need_clarification"

    def test_clarify_without_text_falls_back_to_default_message(self):
        with pytest.raises(ClarificationNeededError) as exc:
            parse_generation_output("CLARIFY:")
        assert "补充必要信息" in exc.value.message

    def test_clarify_prefix_is_case_sensitive_and_exact(self):
        # 只有严格以 CLARIFY: 开头才算澄清，普通 SQL 不受影响
        sql = "SELECT 'CLARIFY: hint' AS note"
        assert parse_generation_output(sql) == sql

    def test_reject_raises_recall_empty_with_prd_message(self):
        # 拒答必须用 PRD 固定话术，不采信模型自拟文本
        with pytest.raises(RecallEmptyError) as exc:
            parse_generation_output("REJECT")
        assert exc.value.code == "recall_empty"
        assert exc.value.message == "【未找到相关数据表或字段，请尝试换一种表述】"

    def test_reject_with_trailing_text_still_uses_prd_message(self):
        with pytest.raises(RecallEmptyError) as exc:
            parse_generation_output("REJECT: 该字段不存在")
        assert exc.value.message == "【未找到相关数据表或字段，请尝试换一种表述】"

    def test_reject_does_not_match_select_sql(self):
        # SELECT 语句里出现 REJECT 字样不能误判
        sql = "SELECT 'REJECT' AS flag FROM fact_order"
        assert parse_generation_output(sql) == sql
