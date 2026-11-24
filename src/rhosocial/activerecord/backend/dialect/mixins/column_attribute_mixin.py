# .../mixins/column_attribute_mixin.py
"""Mixin for ColumnAttributeSupport. Members/order/signature mirror the protocol."""
from ...expression.bases import BaseExpression

from typing import Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements.ddl_table import ColumnClause

class ColumnAttributeMixin:

    def format_column_attribute(self, expr: "ColumnClause") -> "Tuple[str, tuple]":
            """Render one expression-layer column clause as a definition fragment.

            The subject is a :class:`BaseExpression` node: :class:`CollationClause`,
            :class:`CharacterSetClause`, :class:`IdentityClause` or
            :class:`AutoIncrementClause`. Each names its own formatter through
            ``format_method``, so this method only has to dispatch.

            AR-layer ``ColumnAttribute`` objects are translated by the deriver
            (``base.derivation._translated_column_attributes``) before they reach
            ``ColumnDefinition.attributes``. The old render-time translation via
            ``translate_ar_attribute`` is deprecated and no longer invoked here.
            """
            from ..exceptions import UnsupportedFeatureError
            from ...expression.statements.ddl_table import (
                CharacterSetClause,
                CollationClause,
            )

            if not isinstance(expr, BaseExpression):
                raise UnsupportedFeatureError(
                    self.name,
                    f"COLUMN CLAUSE {type(expr).__name__}",
                    f"{self.name} cannot render this column clause; declare it "
                    f"only on backends that support it.",
                )
            if isinstance(expr, CollationClause):
                if not self.supports_column_collation():
                    raise UnsupportedFeatureError(self.name, "column-level COLLATE")
                return self.format_collation_clause(expr)
            if isinstance(expr, CharacterSetClause):
                if not self.supports_column_character_set():
                    raise UnsupportedFeatureError(self.name, "column-level CHARACTER SET")
                return self.format_character_set_clause(expr)
            formatter = getattr(self, expr.format_method, None)
            if formatter is None:
                raise UnsupportedFeatureError(
                    self.name,
                    f"{type(expr).__name__} formatter",
                    f"{self.name} has no formatter for the column clause "
                    f"{type(expr).__name__}; declare it only on backends that "
                    f"support it.",
                )
            return formatter(expr)

    def translate_ar_attribute(self, attr: Any) -> Any:
            """DEPRECATED — AR-layer attribute translation now lives in the deriver.

            Core no longer calls this. ``base.derivation._translated_column_attributes``
            turns model declarations into expression-layer clauses before they reach
            ``ColumnDefinition.attributes``. Kept only for external callers that may
            still reach here; it will be removed in a future release.
            """
            import warnings

            warnings.warn(
                "translate_ar_attribute is deprecated; AR-layer column attributes "
                "are translated in base.derivation before reaching the dialect.",
                DeprecationWarning,
                stacklevel=2,
            )
            from ....base.ddl import (
                CharacterSetAttribute,
                CollationAttribute,
                IdentityAttribute,
            )
            from ...expression.statements.ddl_table import (
                CharacterSetClause,
                CollationClause,
                IdentityClause,
            )

            if isinstance(attr, IdentityAttribute):
                # The AR-layer IdentityAttribute keeps its tri-state until the AR
                # layer's exposure of the split is decided (out of scope for this
                # round); translate it to the expression layer's two parameters.
                return IdentityClause(
                    self,
                    attr.generation,
                    start=attr.start,
                    increment=attr.increment,
                    minvalue=attr.minvalue,
                    maxvalue=attr.maxvalue,
                    cycle=attr.cycle is True,
                    no_cycle=attr.cycle is False,
                )
            if isinstance(attr, CollationAttribute):
                return CollationClause(self, attr.name)
            if isinstance(attr, CharacterSetAttribute):
                return CharacterSetClause(self, attr.name)
            return None
