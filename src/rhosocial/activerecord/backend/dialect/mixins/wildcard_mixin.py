# .../mixins/wildcard_mixin.py
"""Per-feature mixin for WildcardSupport. Members/order/signature mirror the protocol."""

from typing import Any, List, Optional, Tuple, TYPE_CHECKING
from ...expression import bases
from ...expression.core import (
    CastExpression,
    QualifiedIdentifier,
    Subquery,
    AllColumnsWildcard,
)
from ...expression.literals import Identifier
from ...expression.mixins import AliasableMixin
from ...expression.operators import (
    ArithmeticOperation,
    BinaryExpression,
    RawSQL,
    SQLOperation,
    ConcatenationOperation,
    UnaryExpression,
)
from .function import FunctionCallMixin

class WildcardMixin:
    def format_all_columns_wildcard(self, expr: "AllColumnsWildcard") -> "Tuple[str, tuple]":
            """Format a :class:`~...expression.core.AllColumnsWildcard`.

            A bare ``*`` when no relation is set -- the surrounding clause's
            formatter decides what the expansion spans. With a relation, the
            qualifier is the spelling the query itself uses: the alias when the
            reference carries one, the relation's own qualified name otherwise.

            Args:
                expr: The all-columns wildcard being rendered.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is empty.

            Raises:
                TypeError: ``relation`` is set but is not a ``NamedRelationRef``.
            """
            relation = expr.relation
            if relation is None:
                return "*", ()
            from ...expression.sources import NamedRelationRef

            if not isinstance(relation, NamedRelationRef):
                raise TypeError(
                    f"AllColumnsWildcard.relation must be a NamedRelationRef, "
                    f"got {type(relation).__name__}"
                )
            if relation.alias:
                qualifier = self.format_identifier(relation.alias, relation.alias_need_quote)
            else:
                qualifier, _ = relation.relation.to_sql()
            return f"{qualifier}.*", ()

    def format_row_count_wildcard(self, expr: "RowCountWildcard") -> "Tuple[str, tuple]":
            """Format a :class:`~...expression.core.RowCountWildcard`.

            The bare asterisk, and nothing else: the row-count wildcard carries
            no relation by contract.

            Args:
                expr: The row-count wildcard being rendered.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is empty.
            """
            return "*", ()
