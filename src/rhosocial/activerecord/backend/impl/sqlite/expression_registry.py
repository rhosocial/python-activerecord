# src/rhosocial/activerecord/backend/impl/sqlite/expression_registry.py
"""SQLite's expression table: core's kinds merged with SQLite's own.

``SQLITE_EXPRESSIONS`` is the mapping this backend's expression package
declares. The published table is the merge of core's mapping and that one --
never a sibling backend's, and no dialect takes part.

Both mappings are data (``kind -> fully qualified class name``); resolution
imports a class only when an artifact names its kind.
"""

from rhosocial.activerecord.backend.expression_registry import (
    CORE_EXPRESSIONS,
    ExpressionRegistry,
    collect_expressions,
    merge_expressions,
)

#: The kinds SQLite's own expression package declares.
SQLITE_EXPRESSIONS = collect_expressions(
    "rhosocial.activerecord.backend.impl.sqlite.expression"
)

#: SQLite's table: core's kinds plus SQLite's own, frozen.
SQLITE_EXPRESSION_REGISTRY = ExpressionRegistry(
    merge_expressions(CORE_EXPRESSIONS, SQLITE_EXPRESSIONS)
).freeze()

__all__ = [
    "SQLITE_EXPRESSIONS",
    "SQLITE_EXPRESSION_REGISTRY",
]
