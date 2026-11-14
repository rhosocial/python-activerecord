# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/capabilities/test_cap_surface_matrix.py
"""Surface matrix for SQLiteDialect: every probe and formatter is exercised."""

from unittest.mock import MagicMock

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.advanced_functions import (
    JSONDocumentValue,
    TrimExpression,
)
from rhosocial.activerecord.backend.expression.predicates import DistinctFromPredicate
from rhosocial.activerecord.backend.expression.query_parts import GroupingClause
from rhosocial.activerecord.backend.expression.query_sources import ValuesExpression
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

LOW = (3, 8, 0)
HIGH = (3, 53, 0)


def _dialect(version=LOW):
    return SQLiteDialect(version=version)


ALWAYS_TRUE = (
    "supports_create_table",
    "supports_drop_table",
    "supports_alter_table",
    "supports_temporary_table",
    "supports_if_not_exists_table",
    "supports_if_exists_table",
    "supports_transactional_ddl",
    "supports_rename_table",
    "supports_deferrable_constraint",
    "supports_create_index",
    "supports_drop_index",
    "supports_unique_index",
    "supports_index_if_exists",
    "supports_index_if_not_exists",
    "supports_partial_index",
    "supports_functional_index",
    "supports_fulltext_search",
    "supports_union",
    "supports_union_all",
    "supports_intersect",
    "supports_except",
    "supports_explain_analyze",
    "supports_on_conflict_clause",
)

ALWAYS_FALSE = (
    "supports_drop_table_cascade",
    "supports_drop_table_restrict",
    "supports_table_partitioning",
    "supports_table_tablespace",
    "supports_fk_match",
    "supports_concurrent_index",
    "supports_index_type",
    "supports_index_tablespace",
    "supports_drop_index_on_table",
    "supports_fulltext_index",
    "supports_fulltext_boolean_mode",
    "supports_fulltext_parser",
    "supports_fulltext_query_expansion",
    "supports_index_include",
    "supports_sequence",
    "supports_ilike",
    "supports_fetch_with_ties",
    "supports_nulls_first_last",
    "supports_json_table",
    "supports_rollup",
    "supports_cube",
    "supports_grouping_sets",
    "supports_array_type",
    "supports_array_constructor",
    "supports_array_access",
    "supports_graph_match",
    "supports_for_update_skip_locked",
    "supports_for_update_nowait",
    "supports_for_update",
    "supports_merge_statement",
    "supports_temporal_tables",
    "supports_qualify_clause",
    "supports_ordered_set_aggregation",
    "supports_truncate",
)


def test_constant_supports_matrix():
    dialect = _dialect()
    for name in ALWAYS_TRUE:
        assert getattr(dialect, name)() is True, name
    for name in ALWAYS_FALSE:
        assert getattr(dialect, name)() is False, name


def test_version_dependent_supports_matrix():
    low = _dialect(LOW)
    high = _dialect(HIGH)

    assert low.supports_basic_cte() is False
    assert high.supports_basic_cte() is True
    assert low.supports_recursive_cte() is False
    assert high.supports_recursive_cte() is True
    assert low.supports_materialized_cte() is False
    assert high.supports_materialized_cte() is True
    assert low.supports_returning_insert() is False
    assert high.supports_returning_insert() is True
    assert low.supports_returning_update() is False
    assert high.supports_returning_update() is True
    assert low.supports_returning_delete() is False
    assert high.supports_returning_delete() is True
    assert low.supports_window_functions() is False
    assert high.supports_window_functions() is True
    assert low.supports_window_frame_clause() is False
    assert high.supports_window_frame_clause() is True
    assert low.supports_filter_clause() is False
    assert high.supports_filter_clause() is True
    assert low.supports_json_type() is False
    assert high.supports_json_type() is True
    assert low.supports_json_arrow_operators() is False
    assert high.supports_json_arrow_operators() is True
    assert low.supports_upsert() is False
    assert high.supports_upsert() is True
    assert low.supports_multiple_on_conflict_clauses() is False
    assert high.supports_multiple_on_conflict_clauses() is True
    assert low.supports_distinct_from() is False
    assert high.supports_distinct_from() is True
    assert low.supports_generated_columns() is False
    assert high.supports_generated_columns() is True
    assert low.supports_stored_generated_columns() is False
    assert high.supports_stored_generated_columns() is True
    assert low.supports_virtual_generated_columns() is False
    assert high.supports_virtual_generated_columns() is True
    assert low.supports_rename_column() is False
    assert high.supports_rename_column() is True
    assert low.supports_drop_column() is False
    assert high.supports_drop_column() is True
    assert low.supports_add_constraint() is False
    assert high.supports_add_constraint() is True
    assert low.supports_drop_constraint() is False
    assert high.supports_drop_constraint() is True


def test_declared_version_and_backend_helpers():
    assert _dialect()._declared_version() == tuple(__import__("sqlite3").sqlite_version_info[:3])
    differ = _dialect().create_schema_differ()
    assert differ.__class__.__name__ == "SQLiteSchemaDiffer"
    suggested = _dialect().suggested_data_types()
    assert set(suggested) == {"uuid", "enum", "xml", "array", "binary", "varbinary"}
    assert _dialect().get_json_access_operator() == "->"


def test_lateral_probe_caches_both_outcomes(monkeypatch):
    class _FakeConnection:
        def execute(self, sql):
            self.sql = sql

        def close(self):
            pass

    # The probe caches on the class. monkeypatch restores whatever was there
    # before this test, so a fabricated outcome cannot leak into later tests.
    monkeypatch.setattr(SQLiteDialect, "_lateral_support", None)
    monkeypatch.setattr("sqlite3.connect", lambda *a, **k: _FakeConnection())
    assert _dialect().supports_lateral_join() is True

    SQLiteDialect._lateral_support = None

    def _fail(*args, **kwargs):
        raise RuntimeError("no lateral")

    monkeypatch.setattr("sqlite3.connect", _fail)
    assert _dialect().supports_lateral_join() is False


def test_json_function_expression_string_column_and_alias():
    dialect = _dialect((3, 38, 0))
    expr = JSONDocumentValue(dialect, "json_col", "$.name", alias="n")
    sql, params = dialect.format_json_function_expression(expr)
    assert sql == 'json_extract("json_col", \'$.name\') AS "n"'
    assert params == ()

    expr = JSONDocumentValue(dialect, Column(dialect, "json_col"), "$.name")
    sql, params = dialect.format_json_function_expression(expr)
    assert sql == "json_extract(\"json_col\", '$.name')"
    assert params == ()


def test_distinct_from_formatter_and_refusal():
    dialect = _dialect((3, 39, 0))
    expr = DistinctFromPredicate(dialect, Column(dialect, "a"), Literal(dialect, 1), is_not=True)
    sql, params = dialect.format_distinct_from_predicate(expr)
    assert "IS NOT DISTINCT FROM" in sql
    assert params == (1,)

    old = _dialect((3, 38, 0))
    with pytest.raises(UnsupportedFeatureError):
        old.format_distinct_from_predicate(
            DistinctFromPredicate(old, Column(old, "a"), Literal(old, 1))
        )


def test_trim_expression_with_and_without_chars_and_alias():
    dialect = _dialect()
    expr = TrimExpression(dialect, Literal(dialect, "  x  "), Literal(dialect, "x"), alias="t")
    sql, params = dialect.format_trim_expression(expr)
    assert sql == 'TRIM(?, ?) AS "t"'
    assert params == ("  x  ", "x")

    bare = TrimExpression(dialect, Literal(dialect, "  x  "))
    sql, params = dialect.format_trim_expression(bare)
    assert sql == "TRIM(?)"
    assert params == ("  x  ",)


def test_values_formatter_alias_and_no_alias():
    dialect = _dialect()
    aliased = ValuesExpression(dialect, [(1, "a")], "v", ["id", "n"])
    sql, params = dialect.format_values_expression(aliased)
    assert sql == '(VALUES (?, ?)) AS "v"'
    assert params == (1, "a")

    plain = ValuesExpression(dialect, [(1,)])
    sql, params = dialect.format_values_expression(plain)
    assert sql == "VALUES (?)"
    assert params == (1,)


def test_truncate_and_grouping_refusals():
    dialect = _dialect()
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_truncate_statement(MagicMock())
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_grouping_clause(GroupingClause(dialect, "UNKNOWN", []))


@pytest.mark.parametrize(
    "operation,method",
    [
        ("ROLLUP", "supports_rollup"),
        ("CUBE", "supports_cube"),
        ("GROUPING SETS", "supports_grouping_sets"),
    ],
)
def test_grouping_unsupported_reaches_final_refusal(monkeypatch, operation, method):
    monkeypatch.setattr(SQLiteDialect, method, lambda self: True)
    dialect = _dialect()
    with pytest.raises(UnsupportedFeatureError) as exc:
        dialect.format_grouping_clause(GroupingClause(dialect, operation, []))
    assert "not supported by SQLite" in str(exc.value)
