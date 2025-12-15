# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_dialect.py
"""
Test cases for SQLite dialect formatting methods.
These tests specifically focus on the correct parameterization of values,
and implicitly test for SQL injection vulnerabilities by ensuring values
are passed as parameters rather than embedded directly into the SQL string.
"""
from typing import List, Any, Tuple

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLiteFormatLimitOffset:
    # Discussion Point: Should format_limit_offset actively validate input as non-zero integers?
    #
    # Rationale against active validation within this method:
    # 1. Separation of Concerns: This method's primary role is low-level SQL formatting and parameterization.
    #    Input validation (e.g., ensuring non-negative integers) belongs to higher-level components,
    #    such as the ORM's query builder or Pydantic models, to maintain clear responsibility boundaries.
    # 2. Flexibility: Strict internal checks could limit future flexibility or support for database-specific
    #    behaviors (e.g., SQLite's 'LIMIT -1' for no limit). Such flexibility is essential in a dialect.
    # 3. Avoid Redundant Validation: Performing checks here might duplicate validation already handled
    #    at higher layers, leading to unnecessary overhead and code repetition.
    # 4. SQL Injection Protection: SQL injection is mitigated by parameterization (using '?'), which is
    #    already in place. Active integer checks are redundant for this specific security concern.
    # 5. Pydantic's Role: For high-level ORM usage, Pydantic is the appropriate tool for robust type and
    #    value validation (e.g., `Field(ge=0)`), ensuring valid data reaches this formatting layer.
    #
    # Therefore, this method should focus purely on SQL dialect specific formatting and parameterization,
    # relying on upstream components for input validity.
    @pytest.fixture
    def dialect(self):
        return SQLiteDialect()

    def test_format_limit_only(self, dialect: SQLiteDialect):
        sql, params = dialect.format_limit_offset(limit=10)
        assert sql == "LIMIT ?"
        assert params == [10]

    def test_format_offset_only(self, dialect: SQLiteDialect):
        sql, params = dialect.format_limit_offset(offset=5)
        assert sql == "LIMIT ? OFFSET ?"
        assert params == [-1, 5]  # SQLite uses -1 for no effective limit

    def test_format_limit_and_offset(self, dialect: SQLiteDialect):
        sql, params = dialect.format_limit_offset(limit=10, offset=5)
        assert sql == "LIMIT ? OFFSET ?"
        assert params == [10, 5]

    def test_format_no_limit_or_offset(self, dialect: SQLiteDialect):
        sql, params = dialect.format_limit_offset()
        assert sql is None
        assert params == []

    def test_format_limit_zero(self, dialect: SQLiteDialect):
        sql, params = dialect.format_limit_offset(limit=0)
        assert sql == "LIMIT ?"
        assert params == [0]

    def test_format_offset_zero(self, dialect: SQLiteDialect):
        sql, params = dialect.format_limit_offset(offset=0)
        assert sql == "LIMIT ? OFFSET ?"
        assert params == [-1, 0] # SQLite uses -1 for no effective limit

    def test_format_limit_sql_injection(self, dialect: SQLiteDialect):
        malicious_limit = "10; DROP TABLE users;"
        sql, params = dialect.format_limit_offset(limit=malicious_limit)
        assert sql == "LIMIT ?"
        assert params == [malicious_limit]

    def test_format_offset_sql_injection(self, dialect: SQLiteDialect):
        malicious_offset = "5 UNION SELECT 1, 2, 3"
        sql, params = dialect.format_limit_offset(offset=malicious_offset)
        assert sql == "LIMIT ? OFFSET ?"  # SQLite's behavior when only offset is given
        assert params == [-1, malicious_offset] # SQLite uses -1 for no effective limit

    def test_format_limit_offset_sql_injection_combined(self, dialect: SQLiteDialect):
        malicious_limit = "10; SELECT SLEEP(5)"
        malicious_offset = "5 OR 1=1"
        sql, params = dialect.format_limit_offset(limit=malicious_limit, offset=malicious_offset)
        assert sql == "LIMIT ? OFFSET ?"
        assert params == [malicious_limit, malicious_offset]
