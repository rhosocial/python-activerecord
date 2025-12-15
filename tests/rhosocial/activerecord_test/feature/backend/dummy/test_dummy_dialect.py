# tests/rhosocial/activerecord_test/feature/backend/dummy/test_dialect.py
"""
Test cases for Dummy dialect formatting methods.
These tests specifically focus on the correct parameterization of values,
and implicitly test for SQL injection vulnerabilities by ensuring values
are passed as parameters rather than embedded directly into the SQL string.
"""
from typing import List, Any, Tuple

import pytest

from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestDummyFormatLimitOffset:
    @pytest.fixture
    def dialect(self):
        return DummyDialect()

    def test_format_limit_only(self, dialect: DummyDialect):
        sql, params = dialect.format_limit_offset(limit=10)
        assert sql == "LIMIT ?"
        assert params == [10]

    def test_format_offset_only(self, dialect: DummyDialect):
        sql, params = dialect.format_limit_offset(offset=5)
        assert sql == "OFFSET ?"
        assert params == [5]

    def test_format_limit_and_offset(self, dialect: DummyDialect):
        sql, params = dialect.format_limit_offset(limit=10, offset=5)
        assert sql == "LIMIT ? OFFSET ?"
        assert params == [10, 5]

    def test_format_no_limit_or_offset(self, dialect: DummyDialect):
        sql, params = dialect.format_limit_offset()
        assert sql is None
        assert params == []

    def test_format_limit_zero(self, dialect: DummyDialect):
        sql, params = dialect.format_limit_offset(limit=0)
        assert sql == "LIMIT ?"
        assert params == [0]

    def test_format_offset_zero(self, dialect: DummyDialect):
        sql, params = dialect.format_limit_offset(offset=0)
        assert sql == "OFFSET ?"
        assert params == [0]

    def test_format_limit_sql_injection(self, dialect: DummyDialect):
        malicious_limit = "10; DROP TABLE users;"
        sql, params = dialect.format_limit_offset(limit=malicious_limit)
        assert sql == "LIMIT ?"
        assert params == [malicious_limit]

    def test_format_offset_sql_injection(self, dialect: DummyDialect):
        malicious_offset = "5 UNION SELECT 1, 2, 3"
        sql, params = dialect.format_limit_offset(offset=malicious_offset)
        assert sql == "OFFSET ?"
        assert params == [malicious_offset]

    def test_format_limit_offset_sql_injection_combined(self, dialect: DummyDialect):
        malicious_limit = "10; SELECT SLEEP(5)"
        malicious_offset = "5 OR 1=1"
        sql, params = dialect.format_limit_offset(limit=malicious_limit, offset=malicious_offset)
        assert sql == "LIMIT ? OFFSET ?"
        assert params == [malicious_limit, malicious_offset]
