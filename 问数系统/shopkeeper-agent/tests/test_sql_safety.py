"""
SQL 安全闸口单元测试
"""
import pytest

from app.core.sql_safety import check_query_input, check_sql


class TestCheckSql:
    """check_sql 测试"""

    def test_select_passes(self):
        result = check_sql("SELECT * FROM fact_order LIMIT 10")
        assert result.ok is True

    def test_select_with_joins_passes(self):
        result = check_sql(
            "SELECT SUM(f.order_amount) FROM fact_order f "
            "JOIN dim_region r ON f.region_id = r.region_id "
            "WHERE r.region_name = '华北'"
        )
        assert result.ok is True

    def test_update_blocked(self):
        result = check_sql("UPDATE fact_order SET order_amount = 100 WHERE order_id = 'X'")
        assert result.ok is False
        assert result.code == "sql_blocked"

    def test_delete_blocked(self):
        result = check_sql("DELETE FROM fact_order WHERE order_id = 'X'")
        assert result.ok is False
        assert result.code == "sql_blocked"

    def test_insert_blocked(self):
        result = check_sql("INSERT INTO fact_order (order_id) VALUES ('X')")
        assert result.ok is False

    def test_drop_blocked(self):
        result = check_sql("DROP TABLE fact_order")
        assert result.ok is False

    def test_multi_statement_blocked(self):
        result = check_sql("SELECT 1; DROP TABLE fact_order")
        assert result.ok is False
        assert result.code == "sql_blocked"

    def test_trailing_semicolon_allowed(self):
        result = check_sql("SELECT * FROM fact_order;")
        assert result.ok is True

    def test_empty_sql_blocked(self):
        result = check_sql("")
        assert result.ok is False

    def test_none_sql_blocked(self):
        result = check_sql(None)
        assert result.ok is False

    def test_sleep_blocked(self):
        result = check_sql("SELECT SLEEP(10) FROM fact_order")
        assert result.ok is False

    def test_union_select_blocked(self):
        result = check_sql("SELECT * FROM fact_order UNION SELECT * FROM dim_customer")
        assert result.ok is False


class TestCheckQueryInput:
    """check_query_input 测试"""

    def test_normal_query_passes(self):
        result = check_query_input("统计华北地区的销售总额")
        assert result.ok is True

    def test_semicolon_injection_blocked(self):
        result = check_query_input("帮我查一下；DROP TABLE fact_order")
        assert result.ok is False
        assert result.code == "sql_blocked"

    def test_comment_injection_blocked(self):
        result = check_query_input("查一下销售--注释")
        assert result.ok is False

    def test_union_select_injection_blocked(self):
        result = check_query_input("查 UNION SELECT password FROM users")
        assert result.ok is False

    def test_or_1_1_blocked(self):
        result = check_query_input("' OR 1=1 --")
        assert result.ok is False

    def test_drop_table_injection_blocked(self):
        result = check_query_input("查询 drop table fact_order")
        assert result.ok is False

    def test_empty_query_passes(self):
        result = check_query_input("")
        assert result.ok is True
