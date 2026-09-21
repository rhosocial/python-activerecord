# tests/rhosocial/activerecord_test/feature/basic/ddl/test_table_inherits_tablespace.py
"""ActiveRecord-level tests for the table-level ``table_inherits()`` /
``table_tablespace()`` interfaces (§5.15).

Both are backend-specific (PostgreSQL) declarations with no framework
default; the deriver passes them through to ``CreateTableExpression`` and the
generic renderer gates them on ``supports_table_inherits()`` /
``supports_table_tablespace()`` (never silently dropped).
"""

import pytest

from rhosocial.activerecord.base.ddl import TableDDLDeriver
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.model import ActiveRecord


class Inheriting(ActiveRecord):
    __table_name__ = "child"

    id: int

    @classmethod
    def table_inherits(cls):
        return ["parent_a", "parent_b"]


class Tablespaced(ActiveRecord):
    __table_name__ = "spaced"

    id: int

    @classmethod
    def table_tablespace(cls):
        return "ts_data"


SQLITE = SQLiteDialect((3, 53, 0))


def test_table_inherits_is_carried_and_rendered():
    expression = TableDDLDeriver(Inheriting, DummyDialect()).create_table()
    assert expression.inherits == ["parent_a", "parent_b"]
    sql, _ = expression.to_sql()
    assert 'INHERITS ("parent_a", "parent_b")' in sql


def test_table_tablespace_is_carried_and_rendered():
    expression = TableDDLDeriver(Tablespaced, DummyDialect()).create_table()
    assert expression.tablespace == "ts_data"
    sql, _ = expression.to_sql()
    assert 'TABLESPACE "ts_data"' in sql


def test_defaults_are_absent():
    class Plain(ActiveRecord):
        __table_name__ = "plain"

        id: int

    expression = TableDDLDeriver(Plain, DummyDialect()).create_table()
    assert expression.inherits == []
    assert expression.tablespace is None


def test_table_inherits_unsupported_raises():
    with pytest.raises(UnsupportedFeatureError, match="INHERITS"):
        TableDDLDeriver(Inheriting, SQLITE).create_table().to_sql()


def test_table_tablespace_unsupported_raises():
    with pytest.raises(UnsupportedFeatureError, match="TABLESPACE"):
        TableDDLDeriver(Tablespaced, SQLITE).create_table().to_sql()
