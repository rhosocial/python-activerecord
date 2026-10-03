# tests/rhosocial/activerecord_test/feature/backend/dialect/test_schema_not_silently_ignored.py
"""
A schema that was supplied must never be silently dropped.

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
- A source scan fails the build if any formatter renders a schema-bearing
  object name through ``format_identifier`` alone, which is the shape that
  drops it.
"""
import ast
from pathlib import Path

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.expression.statements import TriggerEvent, TriggerTiming
from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
    CreateTriggerExpression,
    DropTriggerExpression,
)
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

    def test_create_trigger_with_schema_raises(self, dialect):
        """The trigger formatter is SQLite's own, so it needed the same fix.

        A trigger names three things -- itself, the table it is on, and the
        function it calls -- and every other backend qualifies all three from
        the one ``schema_name``. This mixin rendered all three with bare
        ``format_identifier``, so ``schema_name`` was accepted by the expression,
        stored, and then went nowhere: SQLite emitted a statement that looked
        unqualified because it was unqualified.
        """
        expr = CreateTriggerExpression(
            dialect,
            "trg_orders_ai",
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.INSERT],
            table=TableExpression(dialect, "orders"),
            function_name=TableExpression(dialect, "fn_orders_ai"),
            schema_name=SCHEMA,
        )
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "schema" in str(exc.value).lower()

    def test_drop_trigger_with_schema_raises(self, dialect):
        expr = DropTriggerExpression(dialect, "trg_orders_ai", schema_name=SCHEMA)
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "schema" in str(exc.value).lower()

    def test_create_trigger_without_schema_renders(self, dialect):
        """The unqualified form must come out exactly as it did before.

        Routing the names through TableExpression was the fix, not a rewrite:
        a SQLite trigger that omits the schema has to render byte for byte as
        before, or the change fixed the drop and introduced one.
        """
        expr = CreateTriggerExpression(
            dialect,
            "trg_orders_ai",
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.INSERT],
            table=TableExpression(dialect, "orders"),
            function_name=TableExpression(dialect, "fn_orders_ai"),
        )
        sql, params = expr.to_sql()
        assert sql == (
            'CREATE TRIGGER "trg_orders_ai" AFTER INSERT ON "orders" '
            'FOR EACH ROW BEGIN SELECT "fn_orders_ai"(); END'
        )
        assert params == ()

    def test_drop_trigger_without_schema_renders(self, dialect):
        sql, params = DropTriggerExpression(dialect, "trg_orders_ai").to_sql()
        assert sql == 'DROP TRIGGER "trg_orders_ai"'
        assert params == ()


class TestNoFormatterDropsSchema:
    """A formatter must not render a schema-bearing name unqualified.

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


class TestTruncateQualifiesLikeEverythingElse:
    """TRUNCATE was the last statement carrying its schema under another name.

    It took ``schema`` where every other object took ``schema_name``, and stored
    it without validating -- so an empty string was caught only during rendering,
    by the TableExpression the formatter built, and the error named that object
    rather than the one the caller had constructed.
    """

    @pytest.fixture
    def dialect(self):
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        # SQLite refuses TRUNCATE outright, so the generic rendering path is
        # exercised through the dummy dialect, which supports it.
        return DummyDialect()

    def test_carries_schema_name(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
            TruncateExpression,
        )

        assert (
            TruncateExpression(
                dialect, TableExpression(dialect, "orders", schema_name=SCHEMA)
            ).to_sql()[0]
            == f'TRUNCATE TABLE "{SCHEMA}"."orders"'
        )

    def test_construction_collects_and_rendering_rejects(self, dialect):
        """An expression collects parameters; the dialect judges them.

        At construction the parameters may still be incomplete and the dialect
        may not be settled, so an empty schema is stored rather than refused.
        Strict validation happens when the statement is rendered -- the first
        moment the schema is used -- and it names the expression the caller
        built, which is now the TableExpression the caller passed in.
        """
        from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
            TruncateExpression,
        )

        expr = TruncateExpression(dialect, TableExpression(dialect, "orders", schema_name=""))
        assert expr.table.schema_name == "", "construction must not judge the value"
        with pytest.raises(ValueError) as exc:
            expr.to_sql()
        assert "schema_name" in str(exc.value), exc.value
        assert "non-empty" in str(exc.value), (
            f"the message must say what is wrong and what to do instead: {exc.value}"
        )

    def test_the_old_parameter_name_is_gone(self, dialect):
        """A clean break rather than a silent alias.

        Accepting ``schema`` as a deprecated alias would mean a caller who kept
        using it gets no error at all -- which is the failure this branch is
        about. A TypeError is the honest outcome for a renamed keyword.
        """
        import inspect

        from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
            TruncateExpression,
        )

        assert "schema" not in inspect.signature(TruncateExpression.__init__).parameters
        with pytest.raises(TypeError):
            TruncateExpression(dialect, "orders", schema="app")
