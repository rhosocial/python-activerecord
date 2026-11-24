# src/rhosocial/activerecord/backend/suggestion/definitions/general.py
"""Value definitions for the remaining single-value suggestion methods."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
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
class CreateTableLayoutSuggestion:
    """How a backend declares a partitioned/plain table at CREATE time.

    ``strategy`` is ``"single"`` when the backend can inline all definitions
    (indexes, comments) into one CREATE TABLE statement, or ``"split"`` when
    those must be emitted as separate statements (CreateIndex / CommentOn).
    ``inline_index`` / ``inline_comment`` report the individual capabilities.
    ``state`` is one of ``"actions"`` (use the flags), ``"unsupported"`` (this
    backend cannot render a table of this shape), ``"no-action"`` or
    ``"no-protocol"`` — kept distinct so a caller can report an unsupported
    layout instead of silently skipping it.
    """

    strategy: str = "split"
    inline_index: bool = False
    inline_comment: bool = False
    state: str = "actions"


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
    "CreateTableLayoutSuggestion",
    "IntrospectionScopeSuggestion",
    "JSONAccessOperatorSuggestion",
    "UpsertSyntaxSuggestion",
    "ConcatenationFunctionSuggestion",
]
