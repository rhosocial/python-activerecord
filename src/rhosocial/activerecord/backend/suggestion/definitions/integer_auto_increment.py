# src/rhosocial/activerecord/backend/suggestion/definitions/integer_auto_increment.py
"""Value definition for the integer auto-increment column suggestion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

from ...expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.types import DataType


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


__all__ = ["IntegerAutoIncrementColumnSuggestion"]
