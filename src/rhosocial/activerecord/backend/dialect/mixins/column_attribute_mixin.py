# .../mixins/column_attribute_mixin.py
"""Mixin for ColumnAttributeSupport. Members/order/signature mirror the protocol."""
from ...expression.bases import BaseExpression

from typing import Any, Tuple

class ColumnAttributeMixin:

    def format_column_attribute(self, expr: "ColumnClause") -> "Tuple[str, tuple]":
            """Render one selected column clause as a definition fragment.

            The subject is an expression-layer node: :class:`CollationClause`,
            :class:`CharacterSetClause`, :class:`IdentityClause` or
            :class:`AutoIncrementClause`. Each names its own formatter through
            ``format_method``, so this method only has to dispatch.

            An AR-layer ``ColumnAttribute`` is accepted at the entrance and
            translated before dispatch, because no deriver turns a model's
            declarations into clauses yet -- that layer does not exist, so this is
            currently the only route from ``UseColumnAttributes`` to SQL. The
            translation lives in its own method so it can be deleted whole when a
            deriver lands. It has to be here rather than in
            :meth:`format_column_attributes` because backend
            ``format_column_definition`` overrides call this method directly.
            """
            from ..exceptions import UnsupportedFeatureError
            from ...expression.statements.ddl_table import (
                CharacterSetClause,
                CollationClause,
            )

            if not isinstance(expr, BaseExpression):
                # An AR-layer ColumnAttribute, not an expression. The test is the
                # type, not `hasattr(expr, "format_method")`: that probed a field
                # every expression declares, and it also answered False for an
                # expression whose base property raises -- which is a different
                # question than "is this one of ours". §11.2: asserting to a known
                # base is the way to ask what an argument is.
                original = expr
                expr = self.translate_ar_attribute(original)
                if expr is None:
                    raise UnsupportedFeatureError(
                        self.name,
                        f"COLUMN CLAUSE {type(original).__name__}",
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
            """Turn an AR-layer ``ColumnAttribute`` into an expression-layer clause.

            Transitional, and the reason is a missing layer rather than a
            preference: nothing in the library turns a model's ``UseColumnAttributes``
            declaration into column clauses, so the AR-layer objects reach
            ``ColumnDefinition.attributes`` directly and the dialect has to accept
            them. Once that translation layer exists it belongs there, and this
            method goes with it. Public because backend ``format_column_definition``
            overrides call it: a protocol member that outside callers need is
            public even when its implementation is transitional.
            """
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
