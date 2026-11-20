# src/rhosocial/activerecord/backend/expression/statements/auto_increment_ddl.py
"""Build the DDL parts for an auto-increment key from a backend suggestion.

This is the single public entry point for hand-built expressions that need a
generated integer key (examples, tests, migration scripts). It asks the
dialect for its suggestion and returns the two pieces derivation uses: the
storage type (which may absorb the mechanism, as PostgreSQL's SERIAL) and the
attribute clauses that spell it (which may be empty).
"""
from typing import Any, List, Tuple, TYPE_CHECKING

from ..bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect.base import SQLDialectBase
    from ..types import DataType


def auto_increment_parts(
    dialect: "SQLDialectBase", data_type: "DataType"
) -> Tuple["DataType", List[Any]]:
    """Return ``(type, attributes)`` for a generated integer key.

    A dialect with no ``IntegerAutoIncrementColumnSuggestionSupport`` has no
    answer: the type is left alone and no attribute is added. That is the
    structural "no" -- no probing, no fallback string.
    """
    from ...dialect.protocols import IntegerAutoIncrementColumnSuggestionSupport

    if not isinstance(dialect, IntegerAutoIncrementColumnSuggestionSupport):
        return data_type, []
    suggestion = dialect.suggest_integer_auto_increment_column(data_type)
    attributes = (
        [suggestion.auto_increment]
        if isinstance(suggestion.auto_increment, BaseExpression)
        else []
    )
    return suggestion.type, attributes
