# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_pragma_dialect_integration.py
"""
Tests for SQLite Dialect integration with Extension and Pragma frameworks.

Two categories:
1. Dialect-extension integration: protocol conformance, detection, registration
2. Dialect-pragma integration: pragma query/format/set on the dialect
"""


import pytest

from rhosocial.activerecord.backend.impl.sqlite import (
    SQLiteDialect,
    PragmaCategory,
)
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    SQLiteFTS5CreateVirtualTable,
    SQLiteFTS5RankExpression,
    SQLiteFTS5HighlightExpression,
    SQLiteFTS5SnippetExpression,
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class TestDialectExtensionIntegration:
    """Extension detection and feature-checking through the dialect."""

    def test_has_extension_methods(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert hasattr(d, "detect_extensions")
        assert hasattr(d, "is_extension_available")
        assert hasattr(d, "get_extension_info")
        assert hasattr(d, "check_extension_feature")

    def test_detect_extensions(self):
        exts = SQLiteDialect(version=(3, 35, 0)).detect_extensions()
        assert isinstance(exts, dict)
        assert "fts5" in exts

    def test_fts5_available(self):
        assert SQLiteDialect(version=(3, 35, 0)).is_extension_available("fts5") is True

    def test_fts5_not_available_old_version(self):
        assert SQLiteDialect(version=(3, 8, 0)).is_extension_available("fts5") is False

    def test_check_feature(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.check_extension_feature("fts5", "full_text_search") is True
        assert d.check_extension_feature("fts5", "bm25_ranking") is True

    def test_fts5_capability_methods(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.supports_fts5() is True
        assert d.supports_fts5_bm25() is True
        assert d.supports_fts5_highlight() is True
        assert d.supports_fts5_snippet() is True

    def test_rtree_capability(self):
        assert SQLiteDialect(version=(3, 35, 0)).supports_rtree() is True
        assert SQLiteDialect(version=(3, 5, 0)).supports_rtree() is False

    def test_geopoly_capability(self):
        assert SQLiteDialect(version=(3, 35, 0)).supports_geopoly() is True
        assert SQLiteDialect(version=(3, 25, 0)).supports_geopoly() is False

    def test_math_functions_capability(self):
        assert SQLiteDialect(version=(3, 35, 0)).supports_math_functions() is True
        assert SQLiteDialect(version=(3, 34, 0)).supports_math_functions() is False

    def test_json1_capability(self):
        assert SQLiteDialect(version=(3, 38, 0)).supports_json1_extension() is True
        assert SQLiteDialect(version=(3, 37, 0)).supports_json1_extension() is False


class TestDialectPragmaIntegration:
    """Pragma support through the dialect."""

    def test_has_pragma_methods(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert hasattr(d, "get_pragma_info")
        assert hasattr(d, "get_pragma_sql")
        assert hasattr(d, "set_pragma_sql")
        assert hasattr(d, "is_pragma_available")
        assert hasattr(d, "get_pragmas_by_category")
        assert hasattr(d, "get_all_pragma_infos")

    def test_get_pragma_info(self):
        info = SQLiteDialect(version=(3, 35, 0)).get_pragma_info("foreign_keys")
        assert info is not None
        assert info.name == "foreign_keys"

    def test_get_pragma_sql(self):
        sql = SQLiteDialect(version=(3, 35, 0)).get_pragma_sql("foreign_keys")
        assert sql == "PRAGMA foreign_keys"

    def test_get_pragma_sql_with_argument(self):
        sql = SQLiteDialect(version=(3, 35, 0)).get_pragma_sql("table_info", argument="users")
        assert "table_info" in sql
        assert "users" in sql

    def test_set_pragma_sql(self):
        sql = SQLiteDialect(version=(3, 35, 0)).set_pragma_sql("foreign_keys", 1)
        assert "foreign_keys" in sql
        assert "1" in sql

    def test_is_pragma_available(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.is_pragma_available("foreign_keys") is True
        assert d.is_pragma_available("journal_mode") is True

    def test_get_pragmas_by_category(self):
        pragmas = SQLiteDialect(version=(3, 35, 0)).get_pragmas_by_category(PragmaCategory.CONFIGURATION)
        assert len(pragmas) > 0
        for p in pragmas:
            assert p.category == PragmaCategory.CONFIGURATION

    def test_get_all_pragma_infos(self):
        all_pragmas = SQLiteDialect(version=(3, 35, 0)).get_all_pragma_infos()
        assert isinstance(all_pragmas, dict)
        assert len(all_pragmas) > 0


class TestDialectVirtualTableFormatting:
    """Virtual table formatting methods on the dialect (generic + extension-specific)."""

    def test_format_create_virtual_table(self):
        d = SQLiteDialect(version=(3, 35, 0))
        sql, params = d.format_create_virtual_table(
            module="rtree", table="places",
            columns=["id", "minx", "maxx", "miny", "maxy"]
        )
        assert sql == 'CREATE VIRTUAL TABLE "places" USING rtree("id", "minx", "maxx", "miny", "maxy")'
        assert params == ()

    def test_format_drop_virtual_table(self):
        d = SQLiteDialect(version=(3, 35, 0))
        sql, params = d.format_drop_virtual_table("my_table")
        assert sql == 'DROP TABLE "my_table"'
        assert params == ()

    def test_format_drop_virtual_table_if_exists(self):
        d = SQLiteDialect(version=(3, 35, 0))
        sql, params = d.format_drop_virtual_table("my_table", if_exists=True)
        assert sql == 'DROP TABLE IF EXISTS "my_table"'

    def test_format_drop_virtual_table_quotes_malicious_name(self):
        d = SQLiteDialect(version=(3, 35, 0))
        sql, params = d.format_drop_virtual_table('t"; DROP TABLE users--')
        assert sql.count('"') % 2 == 0  # balanced quotes prevent injection
        assert sql.startswith('DROP TABLE "')

    def test_format_drop_virtual_table_with_special_chars(self):
        d = SQLiteDialect(version=(3, 35, 0))
        sql, _ = d.format_drop_virtual_table("my table")
        assert '"my table"' in sql

    def test_fts5_expressions_via_dialect(self):
        """Format methods accept expression objects and produce correct SQL."""
        d = SQLiteDialect(version=(3, 35, 0))

        sql, _ = d.format_fts5_create_virtual_table(
            SQLiteFTS5CreateVirtualTable(d, table="articles", columns=["title"])
        )
        assert "CREATE VIRTUAL TABLE" in sql
        assert "fts5" in sql
        assert '"articles"' in sql

        sql, params = d.format_fts5_match_expression(
            table="articles", query="python"
        )
        assert "MATCH" in sql
        assert params == ("python",)

        sql, _ = d.format_fts5_rank_expression(
            SQLiteFTS5RankExpression(d, table="articles")
        )
        assert "bm25" in sql.lower()

        sql, params = d.format_fts5_highlight_expression(
            SQLiteFTS5HighlightExpression(d, table="articles", column="title")
        )
        assert "highlight(" in sql
        assert len(params) == 2

        sql, params = d.format_fts5_snippet_expression(
            SQLiteFTS5SnippetExpression(d, table="articles", column="body")
        )
        assert "snippet(" in sql
        assert len(params) == 4

    def test_rtree_expressions_via_dialect(self):
        d = SQLiteDialect(version=(3, 35, 0))

        sql, _ = d.format_rtree_create_virtual_table(
            SQLiteRTreeCreateVirtualTable(d, table="places")
        )
        assert "CREATE VIRTUAL TABLE" in sql
        assert "rtree" in sql

        sql, params = d.format_rtree_range_query(
            SQLiteRTreeRangeQuery(d, table="places", ranges=[(0.0, 1.0), (0.0, 1.0)])
        )
        assert "min0" in sql
        assert len(params) == 4

    def test_geopoly_expressions_via_dialect(self):
        d = SQLiteDialect(version=(3, 35, 0))

        sql, _ = d.format_geopoly_create_virtual_table(
            SQLiteGeopolyCreateVirtualTable(d, table="zones")
        )
        assert "CREATE VIRTUAL TABLE" in sql
        assert "geopoly" in sql

        sql, params = d.format_geopoly_contains_query(
            SQLiteGeopolyContainsExpression(d, table="zones", longitude=1.0, latitude=2.0)
        )
        assert "geopoly_contains_point" in sql
        assert params == (1.0, 2.0)

        sql, _ = d.format_geopoly_area_expression(
            SQLiteGeopolyAreaExpression(d, table="zones")
        )
        assert "geopoly_area" in sql

    def test_format_create_virtual_table_safe_unknown_module_allowed(self):
        d = SQLiteDialect(version=(3, 35, 0))
        sql, _ = d.format_create_virtual_table(
            module="my_module", table="t", columns=["c"]
        )
        assert 'USING my_module("c")' in sql

    def test_format_create_virtual_table_rejects_malicious_module(self):
        d = SQLiteDialect(version=(3, 35, 0))
        with pytest.raises(ValueError, match="Unsafe virtual table module"):
            d.format_create_virtual_table(
                module="malicious' DROP TABLE users; --",
                table="t", columns=["c"]
            )

    def test_unsupported_versions_raise_error(self):
        with pytest.raises(UnsupportedFeatureError):
            d = SQLiteDialect(version=(3, 8, 0))
            d.format_fts5_create_virtual_table(
                SQLiteFTS5CreateVirtualTable(d, table="t", columns=["c"])
            )

        with pytest.raises(UnsupportedFeatureError):
            d = SQLiteDialect(version=(3, 5, 0))
            d.format_rtree_create_virtual_table(
                SQLiteRTreeCreateVirtualTable(d, table="t")
            )

        with pytest.raises(UnsupportedFeatureError):
            d = SQLiteDialect(version=(3, 25, 0))
            d.format_geopoly_create_virtual_table(
                SQLiteGeopolyCreateVirtualTable(d, table="z")
            )
