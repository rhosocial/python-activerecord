# src/rhosocial/activerecord/backend/suggestion/integer_auto_increment.py
"""Integer auto-increment suggestion: value + renderer.

One suggestion target per file. The value is a pure frozen dataclass; the
renderer turns it into ``(type, attributes)`` expressions. Suggestions live in
`backend.suggestion`, never in `backend.expression` (reserved for BaseExpression
derivatives).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Tuple, Union

from ..expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect.base import SQLDialectBase
    from ..expression.types import DataType


@dataclass(frozen=True)
class IntegerAutoIncrementColumnSuggestion:
    """A backend's suggested DDL for an integer auto-increment column.

    Attributes:
        type: The storage type expression (``IntegerType``, a backend's own
            integer subclass, or a pseudo-type such as PostgreSQL's SERIAL).
        auto_increment: ``BaseExpression`` naming the mechanism, ``False``
            (type absorbs it; no clause may be added), or ``None`` (plain type).
    """

    type: "DataType"
    auto_increment: Union["BaseExpression", bool, None] = None


class IntegerAutoIncrementSuggestionRenderer:
    """Render an integer auto-increment suggestion into ``(type, attributes)``."""

    def parts(self, dialect: "SQLDialectBase", data_type: "DataType") -> Tuple["DataType", List]:
        """Return ``(type, attributes)``; structural "no" leaves type alone."""
        from ..suggestion.protocols import IntegerAutoIncrementColumnSuggestionSupport

        if not isinstance(dialect, IntegerAutoIncrementColumnSuggestionSupport):
            return data_type, []
        suggestion: "IntegerAutoIncrementColumnSuggestion" = (
            dialect.suggest_integer_auto_increment_column(data_type)
        )
        attributes = (
            [suggestion.auto_increment]
            if isinstance(suggestion.auto_increment, BaseExpression)
            else []
        )
        return suggestion.type, attributes
