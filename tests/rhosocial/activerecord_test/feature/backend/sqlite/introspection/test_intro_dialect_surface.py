# tests/rhosocial/activerecord_test/feature/backend/sqlite/introspection/test_intro_dialect_surface.py
"""Dialect-level introspection probes and the PRAGMA argument spelling."""

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
    SQLitePragmaSetStatement,
)
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


def test_structure_probes_are_false():
    dialect = SQLiteDialect(version=(3, 53, 0))
    assert dialect.supports_partition_info() is False
    assert dialect.supports_extensions() is False


def test_foreign_key_scope_is_gated_by_version():
    old = SQLiteDialect(version=(3, 6, 18))
    assert IntrospectionScope.FOREIGN_KEY not in old.get_supported_introspection_scopes()

    new = SQLiteDialect(version=(3, 6, 19))
    assert IntrospectionScope.FOREIGN_KEY in new.get_supported_introspection_scopes()


def test_pragma_set_with_an_argument_spells_it_before_the_equals():
    dialect = SQLiteDialect(version=(3, 53, 0))
    sql, params = SQLitePragmaSetStatement(dialect, "cache_size", 1000, argument="main").to_sql()
    assert sql == "PRAGMA cache_size(main) = 1000"
    assert params == ()
