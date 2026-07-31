# tests/rhosocial/activerecord_test/feature/backend/dialect/test_insert_on_conflict_capabilities.py
"""
Tests for the ON CONFLICT capability switches in the generic INSERT path.

Covers:
- Default UpsertMixin capability switch values.
- Gating: multiple ON CONFLICT clauses rejected when unsupported.
- Gating: any ON CONFLICT clause rejected when the clause form is unsupported.
- Serialization round-trip of an InsertExpression with multiple clauses.
"""

import pytest

from rhosocial.activerecord.backend.dialect import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    Literal,
    OnConflictClause,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.serialization import serialize, deserialize
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class SingleConflictDialect(DummyDialect):
    """Dialect that supports ON CONFLICT but only a single clause per INSERT."""

    def supports_multiple_on_conflict_clauses(self) -> bool:
        return False


class NoOnConflictClauseDialect(DummyDialect):
    """Dialect that rejects the ON CONFLICT clause form entirely (e.g. Oracle MERGE)."""

    def supports_on_conflict_clause(self) -> bool:
        return False


class TestOnConflictCapabilitySwitches:
    """Tests for the capability switches and their defaults."""

    def test_upsert_mixin_default_switches(self):
        """UpsertMixin defaults: on_conflict clause supported, multiple clauses not."""
        dialect = SingleConflictDialect()
        assert dialect.supports_on_conflict_clause() is True
        assert dialect.supports_multiple_on_conflict_clauses() is False

    def test_dummy_dialect_supports_multiple_clauses(self):
        """The dummy test dialect supports multiple ON CONFLICT clauses."""
        dialect = DummyDialect()
        assert dialect.supports_on_conflict_clause() is True
        assert dialect.supports_multiple_on_conflict_clauses() is True

    def test_single_conflict_dialect_rejects_multiple_clauses(self):
        """Multiple ON CONFLICT clauses raise UnsupportedFeatureError when unsupported."""
        dialect = SingleConflictDialect()
        source = ValuesSource(dialect, values_list=[[Literal(dialect, 1)]])
        clause1 = OnConflictClause(dialect, conflict_target=["a"], do_nothing=True)
        clause2 = OnConflictClause(dialect, conflict_target=["b"], do_nothing=True)
        expr = InsertExpression(dialect, into="t", source=source, on_conflict=[clause1, clause2])

        with pytest.raises(UnsupportedFeatureError, match="multiple ON CONFLICT clauses"):
            expr.to_sql()

    def test_single_conflict_dialect_accepts_single_clause(self):
        """A single ON CONFLICT clause still renders when multiple clauses are unsupported."""
        dialect = SingleConflictDialect()
        source = ValuesSource(dialect, values_list=[[Literal(dialect, 1)]])
        clause = OnConflictClause(dialect, conflict_target=["a"], do_nothing=True)
        expr = InsertExpression(dialect, into="t", source=source, on_conflict=clause)

        sql, params = expr.to_sql()
        assert "ON CONFLICT" in sql
        assert params == (1,)

    def test_no_on_conflict_clause_dialect_rejects_any_clause(self):
        """Any ON CONFLICT clause raises UnsupportedFeatureError when the form is unsupported."""
        dialect = NoOnConflictClauseDialect()
        source = ValuesSource(dialect, values_list=[[Literal(dialect, 1)]])
        clause = OnConflictClause(dialect, conflict_target=["a"], do_nothing=True)
        expr = InsertExpression(dialect, into="t", source=source, on_conflict=clause)

        with pytest.raises(UnsupportedFeatureError, match="does not support ON CONFLICT"):
            expr.to_sql()


class TestOnConflictSerialization:
    """Serialization round-trip for multiple ON CONFLICT clauses."""

    def test_multiple_on_conflict_serialization_roundtrip(self):
        """An InsertExpression with multiple clauses survives serialize/deserialize."""
        dialect = DummyDialect()
        source = ValuesSource(dialect, values_list=[[Literal(dialect, 1), Literal(dialect, "x")]])
        clause1 = OnConflictClause(dialect, conflict_target=["id"], do_nothing=True)
        clause2 = OnConflictClause(
            dialect,
            conflict_target=["name"],
            update_assignments={"name": Literal(dialect, "y")},
        )
        expr = InsertExpression(
            dialect,
            into="users",
            columns=["id", "name"],
            source=source,
            on_conflict=[clause1, clause2],
        )

        expected_sql, expected_params = expr.to_sql()

        spec = serialize(expr)
        assert "on_conflict" in spec["params"]
        assert isinstance(spec["params"]["on_conflict"], list)
        assert len(spec["params"]["on_conflict"]) == 2

        restored = deserialize(spec, dialect)
        sql, params = restored.to_sql()

        assert sql == expected_sql
        assert params == expected_params
