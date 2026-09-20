# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_column_attributes.py
"""Tests for dialect-free column attribute declarations."""

import pytest

from rhosocial.activerecord.base import UseColumnAttributes
from rhosocial.activerecord.base.ddl.attributes import (
    CharacterSetAttribute,
    CollationAttribute,
    IdentityAttribute,
)


def test_use_column_attributes_marker():
    marker = UseColumnAttributes(
        IdentityAttribute(generation="ALWAYS"),
        CollationAttribute(name="utf8mb4_bin"),
    )
    assert [attr.kind for attr in marker.attributes] == ["identity", "collation"]
    assert "IdentityAttribute" in repr(marker)


def test_identity_generation_validation():
    with pytest.raises(ValueError):
        IdentityAttribute(generation="NOPE")


def test_collation_requires_name():
    with pytest.raises(ValueError):
        CollationAttribute(name="")


def test_character_set_requires_name():
    with pytest.raises(ValueError):
        CharacterSetAttribute(name="")
