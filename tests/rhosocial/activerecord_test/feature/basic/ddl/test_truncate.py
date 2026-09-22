# tests/rhosocial/activerecord_test/feature/basic/ddl/test_truncate.py
"""Model-level ``truncate()`` operation (§5.18).

``truncate`` is a model operation (it executes), built on the deriver's
``TRUNCATE TABLE`` expression; backends that lack the statement raise through
their render gate rather than silently degrading.
"""

import pytest

from rhosocial.activerecord.base.ddl import TableDDLDeriver
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateExpression,
)
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.model import ActiveRecord


class Event(ActiveRecord):
    __table_name__ = "events"

    id: int


def test_deriver_builds_truncate_expression():
    expression = TableDDLDeriver(Event, DummyDialect()).truncate()
    assert isinstance(expression, TruncateExpression)
    assert expression.table_name == "events"
    assert expression.restart_identity is False
    assert expression.cascade is False


def test_truncate_renders_options():
    sql, _ = TableDDLDeriver(Event, DummyDialect()).truncate(
        restart_identity=True, cascade=True
    ).to_sql()
    assert "TRUNCATE TABLE" in sql
    assert "RESTART IDENTITY" in sql
    assert "CASCADE" in sql


def test_model_truncate_unsupported_raises():
    Event.__backend__ = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
    with pytest.raises(UnsupportedFeatureError):
        Event.truncate()
