# tests/rhosocial/activerecord_test/feature/backend/schema/test_suggested_data_types.py
"""Tests for the suggested_data_types() type-consistency suggestion map.

Covers:
- Values are DataType **classes** (same value type as supports_data_types —
  no import resolution needed by consumers)
- Keys are generic type names (the format_data_type_* dispatch namespace)
- SQLite suggestions point at the expected SQLite type classes
- Honesty: no self-suggestion; a fully-capable dummy dialect suggests nothing
- Contract invariant: suggested keys and supported keys are disjoint
- DataTypeMixin base default returns {}

For backend authors — how to verify your own coverage
-----------------------------------------------------
Concept coverage (D9) is **per dialect and deliberately not audited from
core**: this file checks the mechanism (value types, key namespaces,
disjointness, honesty), not any backend's completeness — backends differ
too much for one shared shape.  Each backend should keep its own coverage
test that walks the core concepts (**discovered, not listed**, so a
concept added to core later cannot slip past a stale list) and asserts:

- every concept is rendered or suggested — silence is not an answer
  (a concept that is neither reaches the caller as a bare TypeError with
  no route forward);
- rendered and suggested keys are disjoint;
- every substitute actually renders on the dialect;
- every suggested key still names an existing concept, so a core rename
  cannot leave dead entries.

BigQuery's ``test_every_core_concept_is_declared`` is the pattern to
copy.  The full statement of the rule lives on the ``DataTypeSupport``
protocol (:mod:`...dialect.protocols.query.data_type`).
"""

import re

import pytest

from rhosocial.activerecord.backend.expression.types import DataType


def _sqlite_dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
    return SQLiteDialect(version=(3, 45, 0))


def _dummy_dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    return DummyDialect()


_GENERIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class TestSQLiteSuggestions:
    """SQLiteDialect.suggested_data_types() reflects SQLite's real storage."""

    @pytest.fixture
    def suggestions(self):
        return _sqlite_dialect().suggested_data_types()

    def test_values_are_data_type_classes(self, suggestions):
        assert suggestions
        for key, klass in suggestions.items():
            assert isinstance(klass, type), \
                f"suggestion for {key!r} must be a class, got {type(klass).__name__}"
            assert issubclass(klass, DataType)

    def test_keys_are_generic_names(self, suggestions):
        for key in suggestions:
            assert _GENERIC_NAME_RE.match(key), key

    def test_uuid_and_enum_point_at_sqlite_text(self, suggestions):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteTextType,
        )
        assert suggestions["uuid"] is SQLiteTextType
        assert suggestions["enum"] is SQLiteTextType

    def test_binary_and_varbinary_point_at_sqlite_blob(self, suggestions):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteBlobType,
        )
        assert suggestions["binary"] is SQLiteBlobType
        assert suggestions["varbinary"] is SQLiteBlobType

    def test_suggested_class_is_not_the_type_the_key_implies(self, suggestions):
        """The suggestion replaces the generic type — it is not that type."""
        for key, klass in suggestions.items():
            assert klass.name != key, f"self-suggestion for {key!r}"

    def test_rendered_types_are_not_suggested(self, suggestions):
        """Types SQLite's type mixin renders natively get no suggestion."""
        dialect = _sqlite_dialect()
        rendered = set(dialect.supports_data_types())
        assert "json" in rendered and "jsonb" in rendered
        assert not {"json", "jsonb", "varchar", "date"} & set(suggestions)

    def test_suggested_and_supported_keys_are_disjoint(self):
        """Contract invariant: a type the dialect renders needs no suggestion."""
        dialect = _sqlite_dialect()
        supported = set(dialect.supports_data_types())
        suggested = set(dialect.suggested_data_types())
        overlap = supported & suggested
        assert not overlap, f"keys appear in both maps: {sorted(overlap)}"


class TestDummyHonesty:
    """A dialect that formats everything it knows has nothing to suggest."""

    def test_dummy_suggests_nothing(self):
        assert _dummy_dialect().suggested_data_types() == {}

    def test_mixin_default_is_empty(self):
        from rhosocial.activerecord.backend.dialect.mixins.data_type import DataTypeMixin
        assert DataTypeMixin().suggested_data_types() == {}
