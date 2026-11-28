# src/rhosocial/activerecord/backend/suggestion/definitions/generated_value.py
"""Value definition for the database-generated-value suggestion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.bases.bases import BaseExpression
    from ...expression.types import DataType


@dataclass(frozen=True)
class GeneratedValueSuggestion:
    """A backend's answer for a database-generated column value.

    ``state`` is one of:
      * ``"generate"`` — append ``clause`` (e.g. IDENTITY / AUTO_INCREMENT) to
        the column; ``storage_type`` is normally the unchanged declared type.
      * ``"embedded-in-type"`` — ``storage_type`` absorbs the semantics (e.g.
        PostgreSQL SERIAL); there is no clause to append.
      * ``"unsupported"`` — this backend has no mechanism for a generated key;
        the caller must report an error (user should drop the auto-increment
        marker or declare the mechanism explicitly).
      * ``"no-action"`` — the field is not a generated-value key; plain column.

    Precision travels in the ``default_type`` argument of the suggest method;
    a backend picks the right storage type (e.g. SERIAL vs BIGSERIAL) from it.
    """

    state: str
    storage_type: Optional["DataType"] = None
    clause: Optional["BaseExpression"] = None


__all__ = ["GeneratedValueSuggestion"]
