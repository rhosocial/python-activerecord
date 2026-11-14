# tests/rhosocial/activerecord_test/feature/backend/sqlite/introspection/test_intro_capability.py
"""Explicit SQLite introspection capability assertions."""

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def test_ddl_extraction_unsupported_until_a_formatter_exists():
    """The probe is False because no formatter stands behind it.

    It used to answer True on the strength of ``sqlite_master`` alone, while
    ``format_ddl_statement_query_statement`` resolved only to the protocol
    stub -- so ``get_ddl_statement()`` raised. A probe answered True with
    nothing behind it is a broken promise, and False is the honest answer
    until a formatter that can produce faithful DDL exists.
    """
    assert SQLiteDialect().supports_ddl_extraction() is False


def test_ddl_extraction_native_unsupported():
    assert SQLiteDialect().supports_ddl_extraction_native() is False


def test_unused_indexes_detection_unsupported():
    assert SQLiteDialect().supports_unused_indexes_detection() is False
