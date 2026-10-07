# tests/rhosocial/activerecord_test/feature/backend/test_execution_confirmation_helper.py
"""The execution-confirmation helper distinguishes all three outcomes.

Rendering is not execution: PostgreSQL 9 and ClickHouse rendered well-formed
identity clauses their servers refused. The helper exists to make that
distinction reusable, and this file proves each of its three states against a
live connection (SQLite in memory, so no external server is needed):

* the server accepts the rendered SQL -> ``ACCEPTED``;
* the server rejects it -> ``ExecutionConfirmationError`` carrying the SQL and
  the server error;
* the expression itself refuses to render (``UnsupportedFeatureError``) ->
  ``NOT_RENDERED``, returned so the caller can skip -- and explicitly *not* the
  same state as a rejection.

Each verdict is preceded by a sentinel: a deliberately invalid statement must
come back ``REJECTED``, or a null result could be read as acceptance.
"""

import pytest

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.execution_testing import (
    ExecutionConfirmationError,
    ExecutionOutcome,
    classify_execution,
    confirm_expression_execution,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
    IdentityClause,
    InsertExpression,
    QueryExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


@pytest.fixture
def backend():
    backend = SQLiteBackend(database=":memory:")
    yield backend
    backend.disconnect()


class TestSentinels:
    """The classifier must see both answers before any confirmation is trusted."""

    def test_invalid_statement_is_rejected(self, backend):
        """A deliberately wrong statement must be classified REJECTED.

        Without this sentinel, a classifier that swallowed every error and
        returned ACCEPTED would make every later confirmation vacuous.
        """
        assert (
            classify_execution(backend, "THIS IS NOT SQL")
            is ExecutionOutcome.REJECTED
        )

    def test_valid_statement_is_accepted(self, backend):
        """The same path must see acceptance, or the sentinel above proves nothing."""
        assert (
            classify_execution(backend, "CREATE TABLE sentinel_ok (id INTEGER)")
            is ExecutionOutcome.ACCEPTED
        )


class TestDdlConfirmation:
    """A rendered CREATE TABLE is executed, confirmed, and torn down."""

    def test_accepted_ddl_runs_teardown(self, backend):
        dialect = SQLiteDialect()
        table = Table(dialect, "probe_accepted")
        expression = CreateTableExpression(
            dialect, table, [ColumnDefinition(dialect, "id", IntegerType(dialect))]
        )

        outcome = confirm_expression_execution(
            backend, expression, teardown=[DropTableExpression(dialect, table)]
        )

        assert outcome is ExecutionOutcome.ACCEPTED
        # The teardown really ran: the table is gone, and selecting from a
        # missing table is itself a rejection the classifier can see.
        assert (
            classify_execution(backend, "SELECT * FROM probe_accepted")
            is ExecutionOutcome.REJECTED
        )

    def test_rejected_expression_raises_with_context(self, backend):
        """Rendered-but-refused SQL is the failure this helper exists to catch."""
        dialect = SQLiteDialect()
        expression = InsertExpression(
            dialect,
            into=Table(dialect, "missing_table"),
            source=ValuesSource(dialect, [[Literal(dialect, 1)]]),
        )

        with pytest.raises(ExecutionConfirmationError) as exc_info:
            confirm_expression_execution(backend, expression)

        message = str(exc_info.value)
        assert "missing_table" in message
        assert "server error" in message
        assert exc_info.value.__cause__ is not None


class TestNotRenderedIsNotARejection:
    """Fail-closed rendering is the third state, and must not look like failure."""

    def test_unsupported_expression_returns_not_rendered(self, backend):
        """SQLite has no identity grammar, so the expression refuses to render.

        The helper returns ``NOT_RENDERED`` instead of executing anything:
        treating this as a rejection would fail a dialect for behaving
        correctly, and treating a rejection as this would hide a defect.
        """
        outcome = confirm_expression_execution(backend, IdentityClause(SQLiteDialect()))
        assert outcome is ExecutionOutcome.NOT_RENDERED

    def test_not_rendered_is_a_distinct_state(self, backend):
        """The enum has three distinct members, not two aliases."""
        assert ExecutionOutcome.ACCEPTED is not ExecutionOutcome.REJECTED
        assert ExecutionOutcome.REJECTED is not ExecutionOutcome.NOT_RENDERED
        assert ExecutionOutcome.ACCEPTED is not ExecutionOutcome.NOT_RENDERED


class TestQueryShapedConfirmation:
    """Query-shaped expressions use the prepare channel for their schema."""

    def test_select_over_prepared_schema_is_accepted(self, backend):
        dialect = SQLiteDialect()
        expression = QueryExpression(
            dialect,
            select=[Column(dialect, "id")],
            from_=Table(dialect, "probe_query"),
        )

        outcome = confirm_expression_execution(
            backend,
            expression,
            prepare=[("CREATE TABLE probe_query (id INTEGER)", ())],
            teardown=[("DROP TABLE probe_query", ())],
        )

        assert outcome is ExecutionOutcome.ACCEPTED
        assert (
            classify_execution(backend, "SELECT * FROM probe_query")
            is ExecutionOutcome.REJECTED
        )
