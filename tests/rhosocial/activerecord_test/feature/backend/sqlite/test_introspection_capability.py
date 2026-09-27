# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_introspection_capability.py
"""Explicit SQLite introspection capability assertions."""

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def test_ddl_extraction_supported():
    assert SQLiteDialect().supports_ddl_extraction() is True


def test_ddl_extraction_native_unsupported():
    assert SQLiteDialect().supports_ddl_extraction_native() is False


def test_unused_indexes_detection_unsupported():
    assert SQLiteDialect().supports_unused_indexes_detection() is False
