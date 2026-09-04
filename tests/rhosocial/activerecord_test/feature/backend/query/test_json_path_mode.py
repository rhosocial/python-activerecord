# tests/rhosocial/activerecord_test/feature/backend/query/test_json_path_mode.py
"""Tests for JSONPathMode dispatch behavior.

Covers:
- JSONPathMode.from_value() boundary cases
- JSONMixin.format_json_expression() dispatch decisions
- format_json_arrow_expression() error path on unsupported dialects
- format_json_function_expression() equivalence on supported dialects
- JSONExpression stores mode correctly
"""
from typing import TYPE_CHECKING, Any, Tuple

import pytest

from rhosocial.activerecord.backend.dialect import (
    JSONMixin,
    JSONSupport,
    SQLDialectBase,
    UnsupportedFeatureError,
)
from rhosocial.activerecord.backend.dialect.mixins.identifier import IdentifierMixin
from rhosocial.activerecord.backend.expression.advanced_functions import (
    JSONExpression,
    JSONPathMode,
)

if TYPE_CHECKING:  # pragma: no cover
    pass


# ----------------------------------------------------------------------------
# Test dialects
# ----------------------------------------------------------------------------


class _BaseTestDialect(SQLDialectBase, JSONMixin, JSONSupport, IdentifierMixin):
    """Common base for test dialects; provides identifier formatting."""

    name = "test"


class ArrowSupportedDialect(_BaseTestDialect):
    """Dialect that supports JSON arrow operators (-> and ->>)."""

    def supports_json_arrow_operators(self) -> bool:
        return True


class ArrowUnsupportedDialect(_BaseTestDialect):
    """Dialect that does NOT support JSON arrow operators."""

    def supports_json_arrow_operators(self) -> bool:
        return False


class FunctionOverrideDialect(ArrowSupportedDialect):
    """Dialect that overrides format_json_function_expression to verify dispatch."""

    def __init__(self, function_marker: str = "FN") -> None:
        super().__init__()
        self.function_marker = function_marker

    def format_json_function_expression(self, expr: "JSONExpression") -> Tuple[str, tuple]:
        return f"{self.function_marker}({expr.column}, {expr.path})", ()


# ----------------------------------------------------------------------------
# JSONPathMode.from_value() tests
# ----------------------------------------------------------------------------


class TestJSONPathModeFromValue:
    """Verify JSONPathMode.from_value boundary handling."""

    def test_none_returns_auto(self) -> None:
        assert JSONPathMode.from_value(None) is JSONPathMode.AUTO

    def test_pass_through_enum(self) -> None:
        assert JSONPathMode.from_value(JSONPathMode.ARROW) is JSONPathMode.ARROW

    @pytest.mark.parametrize(
        "value, expected",
        [
            ("auto", JSONPathMode.AUTO),
            ("arrow", JSONPathMode.ARROW),
            ("function", JSONPathMode.FUNCTION),
        ],
    )
    def test_string_to_enum(self, value: str, expected: "JSONPathMode") -> None:
        assert JSONPathMode.from_value(value) is expected

    def test_uppercase_string_raises(self) -> None:
        """Case-sensitive lookup: only the lowercase enum *value* is valid."""
        with pytest.raises(ValueError):
            JSONPathMode.from_value("AUTO")

    def test_mixed_case_string_raises(self) -> None:
        with pytest.raises(ValueError):
            JSONPathMode.from_value("Arrow")

    def test_invalid_string_raises(self) -> None:
        with pytest.raises(ValueError):
            JSONPathMode.from_value("bogus")

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(TypeError):
            JSONPathMode.from_value(123)


# ----------------------------------------------------------------------------
# JSONExpression stores mode as JSONPathMode enum
# ----------------------------------------------------------------------------


class TestJSONExpressionMode:
    """Verify JSONExpression coerces the mode argument."""

    @pytest.mark.parametrize(
        "value, expected",
        [
            (None, JSONPathMode.AUTO),
            ("auto", JSONPathMode.AUTO),
            (JSONPathMode.ARROW, JSONPathMode.ARROW),
            ("function", JSONPathMode.FUNCTION),
        ],
    )
    def test_mode_is_coerced_to_enum(self, value: Any, expected: "JSONPathMode") -> None:
        d = ArrowSupportedDialect()
        expr = JSONExpression(d, "data", "$.a", operation="->", mode=value)
        assert expr.mode is expected

    def test_default_mode_is_auto(self) -> None:
        """Default behavior unchanged: mode=None → JSONPathMode.AUTO."""
        d = ArrowSupportedDialect()
        expr = JSONExpression(d, "data", "$.a")
        assert expr.mode is JSONPathMode.AUTO


# ----------------------------------------------------------------------------
# Dispatch: format_json_expression goes to the right backend method
# ----------------------------------------------------------------------------


class TestDispatchBehavior:
    """Verify JSONMixin.format_json_expression dispatches by mode + capability."""

    def test_auto_on_arrow_supported_dialect_uses_arrow(self) -> None:
        d = ArrowSupportedDialect()
        expr = JSONExpression(d, "data", "$.a", operation="->>")
        sql, params = d.format_json_expression(expr)
        # Arrow formatting emits col->>'...'
        assert "->>" in sql
        assert params == ()

    def test_auto_on_arrow_unsupported_dialect_uses_function(self) -> None:
        d = ArrowUnsupportedDialect()
        expr = JSONExpression(d, "data", "$.a", operation="->>")
        sql, params = d.format_json_expression(expr)
        # Default function-based: JSON_UNQUOTE(JSON_EXTRACT(...))
        assert "JSON_UNQUOTE" in sql
        assert "JSON_EXTRACT" in sql

    def test_arrow_mode_on_unsupported_raises(self) -> None:
        d = ArrowUnsupportedDialect()
        expr = JSONExpression(
            d, "data", "$.a", operation="->>", mode=JSONPathMode.ARROW
        )
        with pytest.raises(UnsupportedFeatureError):
            d.format_json_expression(expr)

    def test_arrow_mode_on_supported_uses_arrow(self) -> None:
        d = ArrowSupportedDialect()
        expr = JSONExpression(
            d, "data", "$.a", operation="->>", mode=JSONPathMode.ARROW
        )
        sql, params = d.format_json_expression(expr)
        assert "->>" in sql
        assert params == ()

    def test_function_mode_on_supported_dialect_uses_function(self) -> None:
        """FUNCTION mode must ignore arrow capability and dispatch to function path."""
        d = FunctionOverrideDialect(function_marker="FN_MARKER")
        expr = JSONExpression(
            d, "data", "$.a", operation="->>", mode=JSONPathMode.FUNCTION
        )
        sql, params = d.format_json_expression(expr)
        assert "FN_MARKER" in sql
        assert params == ()

    def test_function_mode_on_unsupported_dialect_uses_function(self) -> None:
        """FUNCTION mode must work even when arrow is not supported."""
        d = ArrowUnsupportedDialect()
        expr = JSONExpression(
            d, "data", "$.a", operation="->", mode=JSONPathMode.FUNCTION
        )
        sql, params = d.format_json_expression(expr)
        # Default function-based
        assert "JSON_EXTRACT" in sql
        assert params == ()

    def test_string_mode_coerced_and_dispatched(self) -> None:
        """String mode values gets coerced to enum and dispatched correctly."""
        d = FunctionOverrideDialect(function_marker="STRING_MODE")
        expr = JSONExpression(
            d, "data", "$.a", operation="->>", mode="function"
        )
        sql, _ = d.format_json_expression(expr)
        assert "STRING_MODE" in sql


# ----------------------------------------------------------------------------
# Direct method tests
# ----------------------------------------------------------------------------


class TestDirectFormatMethods:
    """Verify format_json_arrow_expression / format_json_function_expression."""

    def test_arrow_direct_on_unsupported_raises(self) -> None:
        d = ArrowUnsupportedDialect()
        expr = JSONExpression(
            d, "data", "$.a", operation="->>", mode=JSONPathMode.ARROW
        )
        with pytest.raises(UnsupportedFeatureError):
            d.format_json_arrow_expression(expr)

    def test_function_direct_always_succeeds_on_supported(self) -> None:
        """Even on arrow-capable backends, function path is available."""
        d = ArrowSupportedDialect()
        expr = JSONExpression(
            d, "data", "$.a", operation="->>", mode=JSONPathMode.FUNCTION
        )
        sql, params = d.format_json_function_expression(expr)
        # Default implements JSON_UNQUOTE(JSON_EXTRACT(...))
        assert "JSON_UNQUOTE" in sql
        assert "JSON_EXTRACT" in sql

    def test_arrow_format_keeps_path_in_string_literal(self) -> None:
        """Arrow formatter escapes via SQL string literal, not parameter."""
        d = ArrowSupportedDialect()
        expr = JSONExpression(d, "users", "$.name", operation="->>")
        sql, params = d.format_json_arrow_expression(expr)
        # No parameter; path is embedded as SQL literal
        assert params == ()
        assert "->>" in sql
        assert "$.name" in sql

    def test_function_format_keeps_path_in_string_literal(self) -> None:
        """Function default uses SQL string literal but no parameter."""
        d = ArrowSupportedDialect()
        expr = JSONExpression(d, "users", "$.name", operation="->")
        sql, params = d.format_json_function_expression(expr)
        assert params == ()
        # Default function path embeds the path as SQL literal
        assert "'$.name'" in sql


# ----------------------------------------------------------------------------
# Path-escaping protections (sanity check: the formatters must escape single
# quotes inside the path so the path cannot break out of the SQL string
# literal).
# ----------------------------------------------------------------------------


class TestPathEscapeSafety:
    """Ensure path is escaped even when embedded in SQL literal."""

    @pytest.mark.parametrize("op", ["->", "->>"])
    def test_arrow_escapes_single_quote_in_path(self, op: str) -> None:
        d = ArrowSupportedDialect()
        # Path containing a single quote — if not escaped, this would break the
        # surrounding SQL string literal.
        path = "$.o'Brien"
        expr = JSONExpression(d, "data", path, operation=op)
        sql, _ = d.format_json_arrow_expression(expr)
        # The single quote in the path must appear doubled-up (escaped) so it
        # cannot terminate the SQL literal early.
        assert "''" in sql
        # The raw un-escaped form ("'B") must NOT appear in the SQL fragment.
        assert "'o'Brien'" not in sql

    @pytest.mark.parametrize("op", ["->", "->>"])
    def test_function_escapes_single_quote_in_path(self, op: str) -> None:
        d = ArrowSupportedDialect()
        path = "$.o'Brien"
        expr = JSONExpression(d, "data", path, operation=op)
        sql, _ = d.format_json_function_expression(expr)
        assert "''" in sql
        assert "'o'Brien'" not in sql
