# tests/rhosocial/activerecord_test/feature/basic/ddl/test_use_sql_type_simulation.py
"""Multi-type ``UseSqlType`` selection across SIMULATED dialects.

Core must not reference backend packages, yet the selection algorithm needs to
be verified against dialects with *different* type-support profiles. These
test-only dialects derive from ``SQLiteDialect`` (full rendering machinery) and
deliberately adjust the support of a few types — including a test-only
"backend-specific" type — to stand in for real backends:

- ``JsonNativeDialect``       — native JSON, no JSONB  (sqlite / mysql 5.7+)
- ``JsonBOnlyDialect``        — JSONB only, no plain JSON (postgres)
- ``VersionGatedJsonDialect`` — JSON gated by version, LONG TEXT fallback
                                (mysql 5.6 vs 5.7)
- ``NoJsonDialect``           — no JSON support at all   (legacy backends)
- ``NoSuggestionDialect``     — no suggestion path

The rule under test: a declared type is selected iff the dialect can render
it; the first such type wins; otherwise the dialect's suggestion is used;
otherwise an error is raised.
"""

from typing import Annotated

import pytest

from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin
from rhosocial.activerecord.backend.expression.types import (
    DataType,
    JsonBType,
    JsonType,
    TextType,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.base import ModelSchemaGenerator
from rhosocial.activerecord.base.fields import UseSqlType
from rhosocial.activerecord.model import ActiveRecord


class SimLongTextType(TextType):
    """Test-only type mimicking a backend-specific long-text type."""


# ---------------------------------------------------------------------------
# Simulated dialects (derive from SQLiteDialect, tweak a few types)
# ---------------------------------------------------------------------------

def _cls(dt_or_cls):
    return dt_or_cls if isinstance(dt_or_cls, type) else type(dt_or_cls)


class JsonNativeDialect(SQLiteDialect):
    """Simulates a backend with native JSON but no JSONB."""

    @DDLTypeMixin.handles(JsonType)
    def format_json_native(self, data_type: JsonType):
        return "JSON", ()

    def suggest_column_type(self, python_type, version=None):
        if python_type is dict:
            return JsonType()
        return super().suggest_column_type(python_type, version)


class JsonBOnlyDialect(SQLiteDialect):
    """Simulates a backend preferring JSONB; plain JSON unsupported."""

    @DDLTypeMixin.handles(JsonBType)
    def format_jsonb_native(self, data_type: JsonBType):
        return "JSONB", ()

    def supports_data_type(self, data_type_or_class) -> bool:
        if _cls(data_type_or_class) is JsonType:
            return False
        return super().supports_data_type(data_type_or_class)

    def suggest_column_type(self, python_type, version=None):
        if python_type is dict:
            return JsonBType()
        return super().suggest_column_type(python_type, version)


class VersionGatedJsonDialect(SQLiteDialect):
    """Simulates MySQL: JSON native only on >= 5.7; LONG TEXT always."""

    def __init__(self, version=None):
        super().__init__()
        self._version = version

    @DDLTypeMixin.handles(JsonType)
    def format_json_native(self, data_type: JsonType):
        return "JSON", ()

    @DDLTypeMixin.handles(SimLongTextType)
    def format_long_text(self, data_type: SimLongTextType):
        return "LONGTEXT", ()

    def _json_supported(self) -> bool:
        if self._version is None:
            return True  # unknown version → optimistic
        return self._version >= (5, 7, 0)

    def supports_data_type(self, data_type_or_class) -> bool:
        if not super().supports_data_type(data_type_or_class):
            return False
        if issubclass(_cls(data_type_or_class), JsonType):
            return self._json_supported()
        return True

    def suggest_column_type(self, python_type, version=None):
        if python_type is dict:
            return TextType()
        return super().suggest_column_type(python_type, version)


class NoJsonDialect(SQLiteDialect):
    """Simulates a legacy backend with no JSON support at all."""

    def supports_data_type(self, data_type_or_class) -> bool:
        if issubclass(_cls(data_type_or_class), JsonType):
            return False
        return super().supports_data_type(data_type_or_class)

    def suggest_column_type(self, python_type, version=None):
        if python_type is dict:
            return TextType()
        return super().suggest_column_type(python_type, version)


class NoSuggestionDialect(SQLiteDialect):
    """Simulates a backend whose suggestion path yields nothing."""

    def supports_data_type(self, data_type_or_class) -> bool:
        if issubclass(_cls(data_type_or_class), JsonType):
            return False
        return super().supports_data_type(data_type_or_class)

    def suggest_column_type(self, python_type, version=None):
        return None


# ---------------------------------------------------------------------------
# Selection tests
# ---------------------------------------------------------------------------

def _resolve(model, dialect) -> DataType:
    expr = ModelSchemaGenerator.generate_create_table(model, dialect)
    return expr.columns[0].data_type


def _model(*types):
    class _M(ActiveRecord):
        payload: Annotated[dict, UseSqlType(*types)]

    return _M


def test_json_native_dialect_skips_jsonb():
    """Declared JsonBType (not renderable) is skipped; JsonType wins."""
    assert isinstance(_resolve(_model(JsonBType(), JsonType()), JsonNativeDialect()), JsonType)


def test_jsonb_only_dialect_skips_json():
    """The reverse profile: plain JsonType skipped, JsonBType wins."""
    assert isinstance(_resolve(_model(JsonBType(), JsonType()), JsonBOnlyDialect()), JsonBType)


def test_first_renderable_wins_when_both_supported():
    """Declaration order decides when several declared types are renderable."""
    assert isinstance(_resolve(_model(JsonBType(), JsonType()), JsonBOnlyDialect()), JsonBType)


def test_version_gated_dialect_prefers_json_on_57():
    assert isinstance(
        _resolve(_model(JsonType(), SimLongTextType()), VersionGatedJsonDialect((5, 7, 30))),
        JsonType,
    )


def test_version_gated_dialect_falls_through_on_56():
    """JsonType is not renderable pre-5.7 → the backend-specific LONG TEXT wins."""
    assert isinstance(
        _resolve(_model(JsonType(), SimLongTextType()), VersionGatedJsonDialect((5, 6, 50))),
        SimLongTextType,
    )


def test_version_gated_dialect_unknown_version_optimistic():
    assert isinstance(
        _resolve(_model(JsonType(), SimLongTextType()), VersionGatedJsonDialect()), JsonType
    )


def test_sim_long_text_not_absorbed_by_other_dialects():
    """A test-only backend type only renders where registered."""
    assert isinstance(_resolve(_model(SimLongTextType(), JsonType()), JsonNativeDialect()), JsonType)


def test_none_renderable_uses_suggestion():
    """JsonBType on a JsonNative dialect → suggestion (dict → JsonType)."""
    assert isinstance(_resolve(_model(JsonBType()), JsonNativeDialect()), JsonType)


def test_no_suggestion_and_no_renderable_raises():
    """No declared type renderable and no suggestion → clear error."""
    with pytest.raises(TypeError, match="none of the declared UseSqlType"):
        _resolve(_model(JsonType()), NoSuggestionDialect())


def test_no_json_dialect_falls_back_to_text():
    """A legacy (no-JSON) backend degrades the declared JSON to suggested TEXT."""
    assert isinstance(_resolve(_model(JsonType()), NoJsonDialect()), TextType)