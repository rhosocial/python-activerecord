# tests/rhosocial/activerecord_test/feature/basic/ddl/test_create_table_layout.py
"""Contracts for the create-table layout suggestion and the two-step builder."""

import dataclasses

try:  # Python 3.8 has no typing.Annotated
    from typing import Annotated, Optional
except ImportError:  # pragma: no cover - only on 3.8
    from typing import Optional

    from typing_extensions import Annotated

from rhosocial.activerecord.base.derivation import (
    build_column_definitions,
    build_create_table_statement,
    build_create_table_statements,
)
from rhosocial.activerecord.backend.dialect.capabilities import build_suggestion_report
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.suggestion import protocols, definitions
from rhosocial.activerecord.base import (
    IdentityAttribute,
    UseColumnAttributes,
    UseComment,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.model import ActiveRecord


class LayoutUser(ActiveRecord):
    __primary_key__ = "id"

    @classmethod
    def table_name(cls):
        return "layout_users"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    email: Annotated[
        Optional[str],
        UseSqlType(VarCharType(length=255)),
        UseIndex("ix_layout_users_email"),
        UseComment("email address"),
    ] = None


DIALECT = SQLiteDialect()


def test_old_dead_suggestion_gone():
    assert not hasattr(protocols, "TableSuggestionSupport")
    assert not hasattr(definitions, "TableStatementSuggestion")


def test_layout_suggestion_is_frozen_value():
    s = definitions.CreateTableLayoutSuggestion(
        strategy="split", inline_index=False, inline_comment=False, state="actions"
    )
    assert dataclasses.is_dataclass(s)
    try:
        s.strategy = "single"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("CreateTableLayoutSuggestion must be frozen")


def test_dialect_reports_layout():
    assert isinstance(DIALECT, protocols.CreateTableLayoutSuggestionSupport)
    layout = DIALECT.suggest_create_table_layout()
    assert layout.strategy == "split"
    assert layout.inline_index is False
    assert layout.inline_comment is False
    assert layout.state == "actions"


def test_build_column_definitions_is_tuple():
    cols = build_column_definitions(LayoutUser, DIALECT)
    assert isinstance(cols, tuple)
    assert len(cols) == 2


def test_build_create_table_statement_unchanged():
    stmt = build_create_table_statement(LayoutUser, DIALECT)
    sql, _ = stmt.to_sql()
    assert "CREATE TABLE" in sql


def test_split_layout_emits_standalone_statements():
    # SQLite cannot inline index/comment -> three statements (create + index + comment).
    stmts = build_create_table_statements(LayoutUser, DIALECT)
    names = [type(s).__name__ for s in stmts]
    assert names[0] == "CreateTableStatement"
    assert "CreateIndexStatement" in names


def test_inline_override_is_single_statement():
    # Forcing inline on SQLite builds one statement (it may fail at render time,
    # but the builder must honour the override).
    stmts = build_create_table_statements(LayoutUser, DIALECT, prefer_inline=True)
    assert len(stmts) == 1
    assert type(stmts[0]).__name__ == "CreateTableStatement"


def test_suggestion_report_includes_new_protocol():
    report = build_suggestion_report(DIALECT)
    assert "CreateTableLayoutSuggestionSupport" in report
    assert report["CreateTableLayoutSuggestionSupport"]["supported"] is True
