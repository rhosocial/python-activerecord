# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/expressions/test_expr_literal_surface.py
"""SQLite's tier-2 literals: bytes as a blob, UUID as quoted text.

``SQLDialectBase.format_literal`` resolves in three tiers. This file pins the
second one -- the types SQLite spells for itself -- and checks that everything
else still reaches the portable tier.
"""

import uuid

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

DIALECT = SQLiteDialect(version=(3, 53, 0))


def test_bytes_render_as_uppercase_hex_blob():
    assert DIALECT.format_literal(b"\x01\x02\xff") == "X'0102FF'"


def test_bytearray_renders_as_the_same_blob():
    assert DIALECT.format_literal(bytearray(b"\xde\xad\xbe\xef")) == "X'DEADBEEF'"


def test_uuid_renders_as_quoted_text():
    value = uuid.UUID("12345678-1234-5678-1234-567812345678")
    assert DIALECT.format_literal(value) == "'12345678-1234-5678-1234-567812345678'"


def test_portable_scalars_still_reach_the_base_tier():
    assert DIALECT.format_literal("it's") == "'it''s'"
    assert DIALECT.format_literal(42) == "42"
    # The portable tier spells booleans as keywords; SQLite accepts TRUE/FALSE
    # since 3.23.0. DDL defaults take SQLite's ``1``/``0`` spelling separately.
    assert DIALECT.format_literal(True) == "TRUE"
