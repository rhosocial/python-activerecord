# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_new_data_types.py
"""Tests for the generic EnumType / BinaryType / VarBinaryType data types.

Covers:
- EnumType: values validation, rendering, equality / hashing, options
- BinaryType / VarBinaryType: rendering (parameterised and bare), equality
- DummyDialect dispatch: supports_data_types() exposes the new generic names
"""

import pytest

from rhosocial.activerecord.backend.expression.types import (
    BinaryType,
    EnumType,
    VarBinaryType,
)


def _dummy_dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    return DummyDialect()


# ---------------------------------------------------------------------------
# EnumType
# ---------------------------------------------------------------------------


class TestEnumType:
    """ENUM — enumerated string values."""

    def test_values_required(self):
        with pytest.raises(ValueError):
            EnumType(None)

    def test_values_must_not_be_empty(self):
        with pytest.raises(ValueError):
            EnumType(None, [])

    def test_values_stored_as_tuple(self):
        assert EnumType(None, ["a", "b"]).values == ("a", "b")

    def test_render_with_values(self):
        dialect = _dummy_dialect()
        assert EnumType(dialect, ["a", "b"]).to_sql() == ("ENUM('a','b')", ())

    def test_render_single_value(self):
        dialect = _dummy_dialect()
        assert EnumType(dialect, ["x"]).to_sql() == ("ENUM('x')", ())

    def test_equality_ignores_dialect(self):
        assert EnumType(None, ["a", "b"]) == EnumType(_dummy_dialect(), ["a", "b"])

    def test_equality_on_values(self):
        assert EnumType(None, ["a", "b"]) != EnumType(None, ["a", "c"])
        assert EnumType(None, ["a"]) != EnumType(None, ["a", "b"])

    def test_hash_matches_equality(self):
        assert hash(EnumType(None, ["a", "b"])) == hash(EnumType(None, ["a", "b"]))

    def test_options_participate_in_equality(self):
        with_options = EnumType(None, ["a"], dialect_options={"charset": "utf8"})
        without_options = EnumType(None, ["a"])
        assert with_options != without_options
        assert with_options == EnumType(None, ["a"], dialect_options={"charset": "utf8"})

    def test_options_do_not_break_hash(self):
        assert hash(EnumType(None, ["a"], dialect_options={"charset": "utf8"})) == \
               hash(EnumType(None, ["a"]))


# ---------------------------------------------------------------------------
# BinaryType / VarBinaryType
# ---------------------------------------------------------------------------


class TestBinaryType:
    """BINARY(n) — fixed-length byte string."""

    def test_render_with_length(self):
        dialect = _dummy_dialect()
        assert BinaryType(dialect, 16).to_sql() == ("BINARY(16)", ())

    def test_render_bare(self):
        dialect = _dummy_dialect()
        assert BinaryType(dialect).to_sql() == ("BINARY", ())

    def test_equality(self):
        assert BinaryType(None, 16) == BinaryType(_dummy_dialect(), 16)
        assert BinaryType(None, 16) != BinaryType(None, 32)
        assert BinaryType(None) != BinaryType(None, 16)
        assert BinaryType(None) != VarBinaryType(None)

    def test_hash_matches_equality(self):
        assert hash(BinaryType(None, 16)) == hash(BinaryType(None, 16))


class TestVarBinaryType:
    """VARBINARY(n) — variable-length byte string."""

    def test_render_with_length(self):
        dialect = _dummy_dialect()
        assert VarBinaryType(dialect, 255).to_sql() == ("VARBINARY(255)", ())

    def test_render_bare(self):
        dialect = _dummy_dialect()
        assert VarBinaryType(dialect).to_sql() == ("VARBINARY", ())

    def test_equality(self):
        assert VarBinaryType(None, 255) == VarBinaryType(_dummy_dialect(), 255)
        assert VarBinaryType(None, 255) != VarBinaryType(None, 100)
        assert VarBinaryType(None) != VarBinaryType(None, 255)
        assert VarBinaryType(None) != BinaryType(None)

    def test_hash_matches_equality(self):
        assert hash(VarBinaryType(None, 255)) == hash(VarBinaryType(None, 255))


# ---------------------------------------------------------------------------
# Dummy dialect dispatch
# ---------------------------------------------------------------------------


class TestDummyDispatch:
    """supports_data_types() exposes the new generic names."""

    def test_new_names_in_supported_mapping(self):
        supported = _dummy_dialect().supports_data_types()
        assert supported["enum"] is EnumType
        assert supported["binary"] is BinaryType
        assert supported["varbinary"] is VarBinaryType

    def test_new_names_support_checks(self):
        dialect = _dummy_dialect()
        assert dialect.supports_data_type_enum() is True
        assert dialect.supports_data_type_binary() is True
        assert dialect.supports_data_type_varbinary() is True
