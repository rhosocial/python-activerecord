# tests/rhosocial/activerecord_test/feature/backend/dialect/test_schema_not_silently_ignored.py
"""
Schema must never be silently dropped (C20).

The rule these tests lock down: a dialect that cannot express a namespace must
*raise* when one is supplied, never quietly render an unqualified name. A
silently unqualified reference is worse than an error, because the statement
still runs -- against whichever namespace the session happened to resolve,
which on PostgreSQL is whatever ``search_path`` selects.

Two directions are covered:

- SQLite is the one real dialect with ``supports_schema() == False``. Its view
  mixin implements the statement formatters itself, so it is the place a
  dropped ``schema_name`` actually hides. Both CREATE and DROP VIEW are driven
  through the real formatter, not a stub.
- A source scan (T-20) fails the build if any future formatter renders a
  schema-bearing object name through ``format_identifier`` alone, which is the
  shape that drops it.
"""
import ast
from pathlib import Path

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    CreateViewExpression,
    DropViewExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression

#: ``.../activerecord_test/feature/backend/dialect/<this file>`` -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[6]
SRC = REPO_ROOT / "src" / "rhosocial" / "activerecord"

SCHEMA = "app"


@pytest.fixture
def dialect() -> SQLiteDialect:
    return SQLiteDialect()


class TestSQLiteRejectsSchema:
    """SQLite has no namespace, so a supplied schema must be refused."""

    def test_supports_schema_is_false(self, dialect):
        """The precondition: SQLite reports no namespace support."""
        assert dialect.supports_schema() is False

    def test_table_reference_with_schema_raises(self, dialect):
        with pytest.raises(UnsupportedFeatureError):
            TableExpression(dialect, "orders", schema_name=SCHEMA).to_sql()

    def test_table_reference_without_schema_renders(self, dialect):
        sql, params = TableExpression(dialect, "orders").to_sql()
        assert sql == '"orders"'
        assert params == ()

    def test_drop_view_with_schema_raises(self, dialect):
        """SQLite's own mixin implements this formatter, so drive it directly.

        This is the regression: the mixin used to render the bare view name and
        return, producing `DROP VIEW "v"` for an expression that had been given
        a schema.
        """
        expr = DropViewExpression(dialect, "v_users", schema_name=SCHEMA)
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "schema" in str(exc.value).lower()

    def test_drop_view_without_schema_renders(self, dialect):
        sql, params = DropViewExpression(dialect, "v_users").to_sql()
        assert sql == 'DROP VIEW "v_users"'
        assert params == ()

    def test_create_view_with_schema_raises(self, dialect):
        query = QueryExpression(dialect=dialect, select=[TableExpression(dialect, "orders")])
        expr = CreateViewExpression(dialect, "v_users", query, schema_name=SCHEMA)
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_view_without_schema_renders(self, dialect):
        query = QueryExpression(dialect=dialect, select=[TableExpression(dialect, "orders")])
        sql, _ = CreateViewExpression(dialect, "v_users", query).to_sql()
        assert sql.startswith('CREATE VIEW "v_users"')


class TestNoFormatterDropsSchema:
    """T-20: a formatter must not render a schema-bearing name unqualified.

    ``format_identifier(name)`` on its own cannot express a namespace, so a
    statement formatter that carries a ``schema_name`` and renders its object
    name that way is dropping the schema. Going through ``TableExpression``
    performs the qualification *and* the refusal, so that is the shape
    required instead.
    """

    #: Expressions whose names can be schema-qualified, and the attribute each
    #: one carries the schema in.
    NAMESPACE_OBJECTS = {
        "view_name": "view DDL",
        "materialized_view_name": "materialized view DDL",
        "index_name": "index DDL",
        "sequence_name": "sequence DDL",
        "type_name": "type DDL",
        "domain_name": "domain DDL",
        "function_name": "function DDL",
        "trigger_name": "trigger DDL",
    }

    def _formatting_functions(self):
        """Yield ``(path, function)`` for every ``format_*_statement`` in src/."""
        for path in sorted(SRC.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if not node.name.startswith("format_"):
                    continue
                yield path, node

    def test_no_formatter_renders_namespace_name_unqualified(self):
        offenders = []
        for path, func in self._formatting_functions():
            src = ast.get_source_segment(path.read_text(encoding="utf-8"), func) or ""
            # A formatter that reads a schema-bearing attribute must not also
            # be the one that renders that object name through
            # format_identifier: that combination drops the schema.
            reads_schema = "schema_name" in src
            for attr, kind in self.NAMESPACE_OBJECTS.items():
                if not reads_schema:
                    continue
                if f"format_identifier(expr.{attr})" in src:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{func.lineno} {kind}")
        assert not offenders, (
            "These formatters read a schema_name but render the object name "
            "through format_identifier, which drops it. Render the name via "
            "TableExpression(self, expr.<name>, schema_name=expr.schema_name) "
            "so the qualification and the refusal both happen:\n  "
            + "\n  ".join(offenders)
        )

    def test_table_expression_performs_the_refusal(self):
        """The mechanism the rule relies on must itself hold.

        Guards against a future change to ``format_table`` that starts
        dropping an unusable schema instead of refusing it, which would leave
        every test above passing for the wrong reason.
        """
        dialect = SQLiteDialect()
        with pytest.raises(UnsupportedFeatureError):
            dialect.format_table(TableExpression(dialect, "orders", schema_name=SCHEMA))
