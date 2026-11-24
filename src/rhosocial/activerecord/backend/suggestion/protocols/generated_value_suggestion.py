# src/rhosocial/activerecord/backend/suggestion/protocols/generated_value_suggestion.py
"""GeneratedValueSuggestionSupport protocol.

A **backend suggestion** capability: the dialect answers how a
database-generated column value is declared on its server. It answers only the
"how" — that the field is a generated key is a separate model declaration, so
"generated value but not a primary key" is expressible.
"""
from typing import Protocol, runtime_checkable, TYPE_CHECKING

from ..definitions import GeneratedValueSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.types import DataType


@runtime_checkable
class GeneratedValueSuggestionSupport(Protocol):
    """A dialect's suggested DDL for a database-generated column value."""

    def suggest_generated_value(
        self, default_type: "DataType"
    ) -> GeneratedValueSuggestion:
        """Suggest the storage type + mechanism for a generated value.

        ``default_type`` carries the declared precision (e.g. IntegerType vs
        BigIntType); a backend picks the matching storage type from it. Return
        a :class:`GeneratedValueSuggestion` whose ``state`` reports whether to
        append a clause, use an embedded type, is unsupported, or needs no
        action.
        """
        ...  # pragma: no cover
