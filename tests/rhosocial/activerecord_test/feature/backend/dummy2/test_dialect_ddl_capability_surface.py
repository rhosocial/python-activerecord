# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_dialect_ddl_capability_surface.py
"""Explicit DDL capability-surface assertions for the reference dialect."""

from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def test_database_ddl_capabilities():
    dialect = DummyDialect()
    assert dialect.supports_create_database() is True
    assert dialect.supports_drop_database() is True
    assert dialect.supports_alter_database() is True
    assert dialect.supports_database_if_not_exists() is True
    assert dialect.supports_database_if_exists() is True
    assert dialect.supports_database_owner() is True
    assert dialect.supports_database_encoding() is True
    assert dialect.supports_database_collation() is True
    assert dialect.supports_database_comment() is True
    assert dialect.supports_database_tablespace() is True
    assert dialect.supports_database_or_replace() is True


def test_trigger_capabilities():
    dialect = DummyDialect()
    assert dialect.supports_trigger() is True
    assert dialect.supports_create_trigger() is True
    assert dialect.supports_drop_trigger() is True
    assert dialect.supports_trigger_referencing() is True
    assert dialect.supports_trigger_when() is True
    assert dialect.supports_trigger_if_not_exists() is True
    assert dialect.supports_trigger_if_exists() is True
