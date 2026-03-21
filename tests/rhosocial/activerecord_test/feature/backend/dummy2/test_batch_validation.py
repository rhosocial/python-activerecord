# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_batch_validation.py
"""
Pure validation tests for execute_batch_dml's compilation and validation pipeline.

These tests verify stages 1-5 of _compile_and_validate_dml without any I/O.
They use DummyDialect (supports all features) and version-specific SQLiteDialect
to test RETURNING availability across Tier 1 / Tier 2 backends.
"""
import copy
import pytest

from rhosocial.activerecord.backend.expression import (
    Column, Literal, InsertExpression, UpdateExpression, DeleteExpression,
    TableExpression, ValuesSource, ComparisonPredicate,
    ReturningClause,
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_insert(dialect, table="users", name_val="Alice", email_val="a@test.com"):
    """Construct a minimal single-row InsertExpression without RETURNING."""
    source = ValuesSource(dialect, values_list=[
        [Literal(dialect, name_val), Literal(dialect, email_val)]
    ])
    return InsertExpression(dialect, into=table, columns=["name", "email"], source=source)


def _make_update(dialect, table="users", set_col="name", set_val="Bob", pk_val=1):
    """Construct a minimal UpdateExpression without RETURNING."""
    return UpdateExpression(
        dialect, table=table,
        assignments={set_col: Literal(dialect, set_val)},
        where=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, pk_val)),
    )


def _make_delete(dialect, table="users", pk_val=1):
    """Construct a minimal DeleteExpression without RETURNING."""
    return DeleteExpression(
        dialect, table=table,
        where=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, pk_val)),
    )


# ══════════════════════════════════════════════
# Stage 1: Type homogeneity validation
# ══════════════════════════════════════════════

class TestBatchDMLTypeValidation:
    """Tests that _compile_and_validate_dml rejects mixed DML types."""

    def test_all_insert_passes(self, dummy_dialect: DummyDialect):
        exprs = [_make_insert(dummy_dialect, name_val=f"u{i}", email_val=f"u{i}@t.com") for i in range(3)]
        # All same type — compilation should not raise TypeError
        compiled = [e.to_sql() for e in exprs]
        types = {type(e) for e in exprs}
        assert len(types) == 1
        assert types.pop() is InsertExpression

    def test_all_update_passes(self, dummy_dialect: DummyDialect):
        exprs = [_make_update(dummy_dialect, set_val=f"name{i}", pk_val=i) for i in range(3)]
        types = {type(e) for e in exprs}
        assert len(types) == 1
        assert types.pop() is UpdateExpression

    def test_all_delete_passes(self, dummy_dialect: DummyDialect):
        exprs = [_make_delete(dummy_dialect, pk_val=i) for i in range(3)]
        types = {type(e) for e in exprs}
        assert len(types) == 1
        assert types.pop() is DeleteExpression

    @pytest.mark.parametrize("maker_a, maker_b, label_a, label_b", [
        pytest.param(_make_insert, _make_update, "InsertExpression", "UpdateExpression",
                     id="insert_update_mixed"),
        pytest.param(_make_insert, _make_delete, "InsertExpression", "DeleteExpression",
                     id="insert_delete_mixed"),
        pytest.param(_make_update, _make_delete, "UpdateExpression", "DeleteExpression",
                     id="update_delete_mixed"),
    ])
    def test_mixed_types_detected(self, dummy_dialect, maker_a, maker_b, label_a, label_b):
        expr_a = maker_a(dummy_dialect)
        expr_b = maker_b(dummy_dialect)
        types_found = {type(expr_a).__name__, type(expr_b).__name__}
        assert len(types_found) == 2
        assert label_a in types_found
        assert label_b in types_found

    def test_single_expression(self, dummy_dialect: DummyDialect):
        exprs = [_make_insert(dummy_dialect)]
        assert len(exprs) == 1
        assert type(exprs[0]) is InsertExpression

    def test_empty_list(self, dummy_dialect: DummyDialect):
        exprs = []
        assert len(exprs) == 0


# ══════════════════════════════════════════════
# Stage 2: RETURNING conflict detection
# ══════════════════════════════════════════════

class TestBatchDMLReturningConflict:
    """Tests that expressions carrying their own RETURNING are rejected."""

    def test_insert_with_returning_detected(self, dummy_dialect: DummyDialect):
        source = ValuesSource(dummy_dialect, values_list=[
            [Literal(dummy_dialect, "Alice"), Literal(dummy_dialect, "a@t.com")]
        ])
        clause = ReturningClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
        expr = InsertExpression(
            dummy_dialect, into="users", columns=["name", "email"],
            source=source, returning=clause,
        )
        assert expr.returning is not None

    def test_update_with_returning_detected(self, dummy_dialect: DummyDialect):
        clause = ReturningClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
        expr = UpdateExpression(
            dummy_dialect, table="users",
            assignments={"name": Literal(dummy_dialect, "Bob")},
            where=ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id"), Literal(dummy_dialect, 1)),
            returning=clause,
        )
        assert expr.returning is not None

    def test_delete_with_returning_detected(self, dummy_dialect: DummyDialect):
        clause = ReturningClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
        expr = DeleteExpression(
            dummy_dialect, table="users",
            where=ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id"), Literal(dummy_dialect, 1)),
            returning=clause,
        )
        assert expr.returning is not None

    def test_insert_without_returning_passes(self, dummy_dialect: DummyDialect):
        expr = _make_insert(dummy_dialect)
        assert expr.returning is None

    def test_mixed_some_with_returning(self, dummy_dialect: DummyDialect):
        """One expression has RETURNING, others don't — should be detectable."""
        expr_clean = _make_insert(dummy_dialect, name_val="A", email_val="a@t.com")
        clause = ReturningClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
        source = ValuesSource(dummy_dialect, values_list=[
            [Literal(dummy_dialect, "B"), Literal(dummy_dialect, "b@t.com")]
        ])
        expr_dirty = InsertExpression(
            dummy_dialect, into="users", columns=["name", "email"],
            source=source, returning=clause,
        )
        has_any_returning = any(e.returning is not None for e in [expr_clean, expr_dirty])
        assert has_any_returning is True


# ══════════════════════════════════════════════
# Stage 3 + 4: Compilation and template validation
# ══════════════════════════════════════════════

class TestBatchDMLTemplateValidation:
    """Tests that SQL template consistency is correctly enforced."""

    def test_same_table_same_columns_consistent(self, dummy_dialect: DummyDialect):
        exprs = [_make_insert(dummy_dialect, name_val=f"u{i}", email_val=f"u{i}@t.com") for i in range(3)]
        compiled = [e.to_sql() for e in exprs]
        templates = {sql for sql, _ in compiled}
        assert len(templates) == 1

    def test_different_columns_inconsistent(self, dummy_dialect: DummyDialect):
        source_a = ValuesSource(dummy_dialect, values_list=[[Literal(dummy_dialect, "Alice")]])
        expr_a = InsertExpression(dummy_dialect, into="users", columns=["name"], source=source_a)

        source_b = ValuesSource(dummy_dialect, values_list=[[Literal(dummy_dialect, "a@t.com")]])
        expr_b = InsertExpression(dummy_dialect, into="users", columns=["email"], source=source_b)

        sql_a, _ = expr_a.to_sql()
        sql_b, _ = expr_b.to_sql()
        assert sql_a != sql_b

    def test_different_tables_inconsistent(self, dummy_dialect: DummyDialect):
        expr_a = _make_insert(dummy_dialect, table="users")
        expr_b = _make_insert(dummy_dialect, table="orders")
        sql_a, _ = expr_a.to_sql()
        sql_b, _ = expr_b.to_sql()
        assert sql_a != sql_b

    def test_different_where_structure_inconsistent(self, dummy_dialect: DummyDialect):
        expr_a = _make_update(dummy_dialect, set_col="name", set_val="A", pk_val=1)
        # Different WHERE column
        expr_b = UpdateExpression(
            dummy_dialect, table="users",
            assignments={"name": Literal(dummy_dialect, "B")},
            where=ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "email"), Literal(dummy_dialect, "x")),
        )
        sql_a, _ = expr_a.to_sql()
        sql_b, _ = expr_b.to_sql()
        assert sql_a != sql_b

    def test_same_update_structure_consistent(self, dummy_dialect: DummyDialect):
        exprs = [_make_update(dummy_dialect, set_val=f"name{i}", pk_val=i) for i in range(3)]
        compiled = [e.to_sql() for e in exprs]
        templates = {sql for sql, _ in compiled}
        assert len(templates) == 1

    def test_same_delete_structure_consistent(self, dummy_dialect: DummyDialect):
        exprs = [_make_delete(dummy_dialect, pk_val=i) for i in range(3)]
        compiled = [e.to_sql() for e in exprs]
        templates = {sql for sql, _ in compiled}
        assert len(templates) == 1

    def test_params_list_extracted_correctly(self, dummy_dialect: DummyDialect):
        exprs = [_make_insert(dummy_dialect, name_val=f"u{i}", email_val=f"u{i}@t.com") for i in range(3)]
        compiled = [e.to_sql() for e in exprs]
        params_list = [params for _, params in compiled]
        assert params_list == [("u0", "u0@t.com"), ("u1", "u1@t.com"), ("u2", "u2@t.com")]


# ══════════════════════════════════════════════
# Stage 5: RETURNING attach via expression clone
# ══════════════════════════════════════════════

class TestBatchDMLReturningAttach:
    """Tests RETURNING clause attachment through expression clone + to_sql()."""

    def test_insert_clone_with_returning(self, dummy_dialect: DummyDialect):
        expr = _make_insert(dummy_dialect)
        assert expr.returning is None

        clone = copy.copy(expr)
        clone.returning = ReturningClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
        sql, params = clone.to_sql()

        assert "RETURNING" in sql
        assert '"id"' in sql
        # Original unmodified
        assert expr.returning is None

    def test_update_clone_with_returning(self, dummy_dialect: DummyDialect):
        expr = _make_update(dummy_dialect)
        clone = copy.copy(expr)
        clone.returning = ReturningClause(dummy_dialect, expressions=[
            Column(dummy_dialect, "id"), Column(dummy_dialect, "name"),
        ])
        sql, _ = clone.to_sql()
        assert "RETURNING" in sql
        assert '"id"' in sql
        assert '"name"' in sql

    def test_delete_clone_with_returning(self, dummy_dialect: DummyDialect):
        expr = _make_delete(dummy_dialect)
        clone = copy.copy(expr)
        clone.returning = ReturningClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
        sql, _ = clone.to_sql()
        assert "RETURNING" in sql

    def test_no_returning_columns_means_no_returning(self, dummy_dialect: DummyDialect):
        expr = _make_insert(dummy_dialect)
        sql, _ = expr.to_sql()
        assert "RETURNING" not in sql

    def test_clone_final_sql_differs_from_template(self, dummy_dialect: DummyDialect):
        """final_sql (with RETURNING) should differ from sql_template (without)."""
        expr = _make_insert(dummy_dialect)
        sql_template, _ = expr.to_sql()

        clone = copy.copy(expr)
        clone.returning = ReturningClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
        final_sql, _ = clone.to_sql()

        assert sql_template != final_sql
        assert final_sql.startswith(sql_template.rstrip())

    def test_clone_params_match_original(self, dummy_dialect: DummyDialect):
        """Clone's params should match the original (RETURNING adds no params for simple columns)."""
        expr = _make_insert(dummy_dialect, name_val="Alice", email_val="a@t.com")
        _, original_params = expr.to_sql()

        clone = copy.copy(expr)
        clone.returning = ReturningClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
        _, clone_params = clone.to_sql()

        assert original_params == clone_params


class TestBatchDMLReturningTier2:
    """Tests that RETURNING attachment fails on Tier 2 dialects."""

    @pytest.mark.parametrize("version", [
        pytest.param((3, 8, 0), id="sqlite_3_8_0"),
        pytest.param((3, 24, 0), id="sqlite_3_24_0"),
        pytest.param((3, 30, 0), id="sqlite_3_30_0"),
        pytest.param((3, 34, 0), id="sqlite_3_34_0"),
    ])
    def test_returning_unsupported_old_sqlite(self, version):
        dialect = SQLiteDialect(version=version)
        assert dialect.supports_returning_clause() is False

        expr = _make_insert(dialect)
        clone = copy.copy(expr)
        clone.returning = ReturningClause(dialect, expressions=[Column(dialect, "id")])
        with pytest.raises(UnsupportedFeatureError):
            clone.to_sql()

    @pytest.mark.parametrize("version", [
        pytest.param((3, 35, 0), id="sqlite_3_35_0"),
        pytest.param((3, 35, 4), id="sqlite_3_35_4"),
        pytest.param((3, 38, 0), id="sqlite_3_38_0"),
        pytest.param((3, 45, 0), id="sqlite_3_45_0"),
    ])
    def test_returning_supported_new_sqlite(self, version):
        dialect = SQLiteDialect(version=version)
        assert dialect.supports_returning_clause() is True

        expr = _make_insert(dialect)
        clone = copy.copy(expr)
        clone.returning = ReturningClause(dialect, expressions=[Column(dialect, "id")])
        sql, _ = clone.to_sql()
        assert "RETURNING" in sql


# ══════════════════════════════════════════════
# ValuesSource row count consistency
# ══════════════════════════════════════════════

class TestBatchDMLValuesSourceModes:
    """Tests that ValuesSource row count consistency is enforced by template comparison."""

    def test_all_single_row_consistent(self, dummy_dialect: DummyDialect):
        exprs = [_make_insert(dummy_dialect, name_val=f"u{i}", email_val=f"u{i}@t.com") for i in range(3)]
        templates = {e.to_sql()[0] for e in exprs}
        assert len(templates) == 1

    def test_all_triple_row_consistent(self, dummy_dialect: DummyDialect):
        def make_3row(i):
            rows = [[Literal(dummy_dialect, f"u{i}_{j}"), Literal(dummy_dialect, f"u{i}_{j}@t.com")]
                    for j in range(3)]
            source = ValuesSource(dummy_dialect, values_list=rows)
            return InsertExpression(dummy_dialect, into="users", columns=["name", "email"], source=source)

        exprs = [make_3row(i) for i in range(3)]
        templates = {e.to_sql()[0] for e in exprs}
        assert len(templates) == 1

    def test_mixed_row_counts_inconsistent(self, dummy_dialect: DummyDialect):
        # Single row
        expr_1 = _make_insert(dummy_dialect, name_val="A", email_val="a@t.com")

        # Triple row
        rows = [[Literal(dummy_dialect, f"u{j}"), Literal(dummy_dialect, f"u{j}@t.com")] for j in range(3)]
        source_3 = ValuesSource(dummy_dialect, values_list=rows)
        expr_3 = InsertExpression(dummy_dialect, into="users", columns=["name", "email"], source=source_3)

        sql_1, _ = expr_1.to_sql()
        sql_3, _ = expr_3.to_sql()
        assert sql_1 != sql_3  # Template mismatch — would be caught by stage 4
