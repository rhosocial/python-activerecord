# src/rhosocial/activerecord/backend/suggestion/definitions/general.py
"""Value definitions for the remaining single-value suggestion methods."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.bases import BaseExpression
    from ...introspection.types import IntrospectionScope


@dataclass(frozen=True)
class IndexTypeSuggestion:
    """Index type names this backend offers."""

    types: List[str]


@dataclass(frozen=True)
class IndexStatementSuggestion:
    """Preferred CREATE/DROP INDEX statement form (None = generic)."""

    statement: Optional[Any]


@dataclass(frozen=True)
class TableStatementSuggestion:
    """Preferred CREATE/DROP TABLE statement form (None = generic)."""

    statement: Optional[Any]


@dataclass(frozen=True)
class IntrospectionScopeSuggestion:
    """The introspection scopes this backend offers."""

    scopes: List["IntrospectionScope"]


@dataclass(frozen=True)
class JSONAccessOperatorSuggestion:
    """The JSON access operator this backend uses."""

    operator: str


@dataclass(frozen=True)
class UpsertSyntaxSuggestion:
    """The UPSERT syntax form this backend uses."""

    syntax: str


@dataclass(frozen=True)
class ConcatenationFunctionSuggestion:
    """Function name for concatenation (None = the ``||`` operator)."""

    function: Optional[str]


__all__ = [
    "IndexTypeSuggestion",
    "IndexStatementSuggestion",
    "TableStatementSuggestion",
    "IntrospectionScopeSuggestion",
    "JSONAccessOperatorSuggestion",
    "UpsertSyntaxSuggestion",
    "ConcatenationFunctionSuggestion",
]
