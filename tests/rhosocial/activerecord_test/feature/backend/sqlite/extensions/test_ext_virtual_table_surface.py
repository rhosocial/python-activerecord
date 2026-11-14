# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_ext_virtual_table_surface.py
"""Virtual-table probes: version floors and compile-option precedence.

Each of FTS5, R-Tree and Geopoly has its own ``ENABLE_*`` compile option. When
the build reports options, they decide; when it reports none, the version floor
is the only evidence available.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.fts5 import (
    SQLiteFTS5MatchPredicate,
)
from rhosocial.activerecord.backend.impl.sqlite.mixins.virtual_table import (
    SQLiteVirtualTableMixin,
)


def test_virtual_table_version_floor():
    assert SQLiteDialect(version=(3, 8, 7)).supports_virtual_table() is False
    assert SQLiteDialect(version=(3, 8, 8)).supports_virtual_table() is True


@pytest.mark.parametrize(
    "method,option,minimum",
    [
        ("supports_fts5", "ENABLE_FTS5", (3, 9, 0)),
        ("supports_rtree", "ENABLE_RTREE", (3, 6, 0)),
        ("supports_geopoly", "ENABLE_GEOPOLY", (3, 26, 0)),
    ],
)
def test_compile_options_decide_before_version(method, option, minimum):
    dialect = SQLiteDialect(version=minimum)

    # An empty mapping means "the build said nothing": fall back to version.
    dialect.set_runtime_param("compile_options", {})
    assert getattr(dialect, method)() is True

    dialect.set_runtime_param("compile_options", {option: True})
    assert getattr(dialect, method)() is True

    dialect.set_runtime_param("compile_options", {"ENABLE_OTHER": True})
    assert getattr(dialect, method)() is False


def test_format_match_predicate_delegates_to_fts5():
    dialect = SQLiteDialect(version=(3, 53, 0))
    predicate = SQLiteFTS5MatchPredicate(dialect, "docs", "python")
    delegated = SQLiteVirtualTableMixin.format_match_predicate(dialect, predicate)
    assert delegated == dialect.format_fts5_match_expression(predicate)
