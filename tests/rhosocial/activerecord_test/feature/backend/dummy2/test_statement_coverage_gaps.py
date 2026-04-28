# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statement_coverage_gaps.py
"""
Tests to cover missing lines in expression statements and transaction modules.
Targets:
  - dml.py:118 (MergeExpression.statement_type)
  - dml.py:310 (DeleteExpression.statement_type)
  - dml.py:439 (UpdateExpression.statement_type)
  - dml.py:615 (InsertExpression.statement_type)
  - dql.py:303 (QueryExpression.statement_type)
  - explain.py:128 (ExplainExpression.statement_type)
  - transaction.py:135-136,152 (begin_type setter and get_params)
  - ddl_alter.py:61,63 (MODIFY_COLUMN and CHANGE_COLUMN action types)
"""

import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.expression.core import Column, Literal, TableExpression
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements.dml import (
    InsertExpression, UpdateExpression, DeleteExpression, MergeExpression,
)
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
from rhosocial.activerecord.backend.expression.statements.explain import ExplainExpression
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AlterTableExpression, AlterTableActionType, ModifyColumn, ChangeColumn,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import ColumnDefinition
from rhosocial.activerecord.backend.expression.transaction import BeginTransactionExpression


class TestDmlStatementTypes:
    """Cover statement_type properties in dml.py."""

    def test_insert_statement_type(self, dummy_dialect):
        expr = InsertExpression(
            dummy_dialect,
            into=TableExpression(dummy_dialect, "users"),
            source=[Literal(dummy_dialect, "Alice")],
            columns=["name"],
        )
        assert expr.statement_type == StatementType.INSERT

    def test_update_statement_type(self, dummy_dialect):
        expr = UpdateExpression(
            dummy_dialect,
            table=TableExpression(dummy_dialect, "users"),
            assignments={"name": Literal(dummy_dialect, "Bob")},
        )
        assert expr.statement_type == StatementType.UPDATE

    def test_delete_statement_type(self, dummy_dialect):
        expr = DeleteExpression(
            dummy_dialect,
            table=TableExpression(dummy_dialect, "users"),
        )
        assert expr.statement_type == StatementType.DELETE

    def test_merge_statement_type(self, dummy_dialect):
        col = Column(dummy_dialect, "id")
        condition = ComparisonPredicate(dummy_dialect, "=", col, Literal(dummy_dialect, 1))
        expr = MergeExpression(
            dummy_dialect,
            target_table=TableExpression(dummy_dialect, "users"),
            source=TableExpression(dummy_dialect, "new_users"),
            on_condition=condition,
        )
        assert expr.statement_type == StatementType.MERGE


class TestDqlStatementType:
    """Cover dql.py:303 — QueryExpression.statement_type."""

    def test_query_statement_type(self, dummy_dialect):
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users"),
        )
        assert query.statement_type == StatementType.DQL


class TestExplainStatementType:
    """Cover explain.py:128 — ExplainExpression.statement_type."""

    def test_explain_statement_type(self, dummy_dialect):
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users"),
        )
        explain = ExplainExpression(dummy_dialect, query)
        assert explain.statement_type == StatementType.EXPLAIN


class TestTransactionBeginType:
    """Cover transaction.py:135-136,152 — begin_type setter and get_params."""

    def test_begin_type_setter(self, dummy_dialect):
        expr = BeginTransactionExpression(dummy_dialect)
        result = expr.begin_type("DEFERRED")
        assert result is expr  # Returns self for chaining

    def test_get_params_with_begin_type(self, dummy_dialect):
        expr = BeginTransactionExpression(dummy_dialect)
        expr.begin_type("IMMEDIATE")
        params = expr.get_params()
        assert params["begin_type"] == "IMMEDIATE"

    def test_get_params_without_begin_type(self, dummy_dialect):
        expr = BeginTransactionExpression(dummy_dialect)
        params = expr.get_params()
        assert "begin_type" not in params


class TestAlterTableModifyChangeColumn:
    """Cover ddl_alter.py:61,63 — MODIFY_COLUMN and CHANGE_COLUMN action types.

    These are MySQL-specific actions that DummyDialect doesn't support.
    We mock the format methods to cover the condition branches.
    """

    def test_modify_column_action(self, dummy_dialect):
        from unittest.mock import patch
        col_def = ColumnDefinition("name", "VARCHAR(255)")
        action = ModifyColumn(column=col_def)
        expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[action],
        )
        with patch.object(dummy_dialect, 'format_modify_column_action', return_value=('MODIFY name VARCHAR(255)', ())):
            sql, params = expr.to_sql()
            assert "MODIFY" in sql

    def test_change_column_action(self, dummy_dialect):
        from unittest.mock import patch
        col_def = ColumnDefinition("new_name", "VARCHAR(255)")
        action = ChangeColumn(old_name="old_name", column=col_def)
        expr = AlterTableExpression(
            dummy_dialect,
            table_name="users",
            actions=[action],
        )
        with patch.object(dummy_dialect, 'format_change_column_action', return_value=('CHANGE old_name new_name VARCHAR(255)', ())):
            sql, params = expr.to_sql()
            assert "CHANGE" in sql
