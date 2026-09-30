# src/rhosocial/activerecord/backend/dialect/mixins/uuid.py
"""Generic dialect mixin for UUID value expressions.

Backends spell UUID generation, constants and casting differently, so this
mixin implements the three ``format_uuid_*`` methods in terms of a
``UUID_FUNCTION`` table that each dialect fills in. A dialect with no native
way to perform an operation leaves its entry out and reports the capability
as unsupported, which turns a render into an
:class:`~...dialect.exceptions.UnsupportedFeatureError` carrying a usable
suggestion rather than another backend's SQL.
"""

from typing import Any, Dict, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.uuid import (
        UUIDCastExpression,
        UUIDConstantExpression,
        UUIDGenerationExpression,
    )


class UUIDMixin:
    """UUID value support: generation, constants and casting.

    A dialect opts in per operation. The default is honest absence: nothing is
    claimed, and rendering raises with a suggestion pointing at the field
    mixin, which generates UUIDs in Python and needs no database function.
    """

    #: SQL text for each operation. ``generation`` and ``cast`` map to a
    #: format string (``{inner}`` is the operand for a cast); ``constant``
    #: maps to a per-constant mapping, e.g.
    #: ``{"constant": {"nil": "...", "max": "..."}}``. An operation absent
    #: from this mapping is unsupported. Subclasses override the attribute
    #: rather than the methods.
    UUID_SQL: Dict[str, Any] = {}

    #: How to phrase the failure for each operation.
    UUID_SUGGESTIONS: Dict[str, str] = {
        "generation": (
            "Generate the value in Python instead — `field/uuid.py` "
            "(`UUIDMixin`) already does this with `uuid.uuid4()` and needs no "
            "database function."
        ),
        "constant": (
            "Compare against a literal instead — the nil UUID is "
            "'00000000-0000-0000-0000-000000000000' and the max UUID is "
            "'ffffffff-ffff-ffff-ffff-ffffffffffff'."
        ),
        "cast": (
            "Cast in Python instead — `uuid.UUID(value)` validates the "
            "text and raises ValueError on malformed input."
        ),
    }

    # ------------------------------------------------------------------
    # Capability probes
    # ------------------------------------------------------------------

    def supports_uuid_generation(self) -> bool:
        """Whether the database can produce a UUID on its own."""
        return "generation" in self.UUID_SQL

    def supports_uuid_constant(self) -> bool:
        """Whether the nil / max UUID constants are available as SQL."""
        return "constant" in self.UUID_SQL

    def supports_uuid_cast(self) -> bool:
        """Whether text can be converted to a UUID in SQL."""
        return "cast" in self.UUID_SQL

    def _require_uuid(self, operation: str, feature: str) -> Any:
        """Return the SQL declaration for *operation*, or raise.

        The declaration is a format string for ``generation`` and ``cast``, and
        a per-constant mapping for ``constant``.
        """
        sql = self.UUID_SQL.get(operation)
        if sql is None:
            raise UnsupportedFeatureError(
                self.name,
                feature,
                self.UUID_SUGGESTIONS.get(operation, ""),
            )
        return sql

    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------

    def format_uuid_generation(
        self, expr: "UUIDGenerationExpression"
    ) -> Tuple[str, Tuple]:
        """Render a fresh-UUID expression.

        Args:
            expr: The UUIDGenerationExpression node.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        sql = self._require_uuid("generation", "UUID generation")
        if getattr(expr, "alias", None):
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_uuid_constant(self, expr: "UUIDConstantExpression") -> Tuple[str, Tuple]:
        """Render the nil or max UUID constant.

        Args:
            expr: The UUIDConstantExpression node.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        constants = self._require_uuid("constant", "UUID constants")
        sql = constants.get(expr.which) if isinstance(constants, dict) else None
        if sql is None:
            raise UnsupportedFeatureError(
                self.name,
                f"UUID {expr.which} constant",
                self.UUID_SUGGESTIONS.get("constant", ""),
            )
        if getattr(expr, "alias", None):
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, ()

    def format_uuid_cast(self, expr: "UUIDCastExpression") -> Tuple[str, Tuple]:
        """Render a text-to-UUID conversion.

        Args:
            expr: The UUIDCastExpression node.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        template = self._require_uuid("cast", "UUID cast")
        inner_sql, inner_params = expr.expression.to_sql()
        sql = template.format(inner=inner_sql)
        if getattr(expr, "alias", None):
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"
        return sql, inner_params


__all__ = ["UUIDMixin"]
