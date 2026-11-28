# src/rhosocial/activerecord/backend/impl/dummy/expression_registry.py
"""Dummy's expression table: core's kinds merged with the dummy nodes.

``DUMMY_EXPRESSIONS`` is the mapping the dummy backend's expression module
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

#: The kinds the dummy expression module declares.
DUMMY_EXPRESSIONS = collect_expressions(
    "rhosocial.activerecord.backend.impl.dummy.expression"
)

#: Dummy's table: core's kinds plus the dummy nodes, frozen.
DUMMY_EXPRESSION_REGISTRY = ExpressionRegistry(
    merge_expressions(CORE_EXPRESSIONS, DUMMY_EXPRESSIONS)
).freeze()

__all__ = [
    "DUMMY_EXPRESSIONS",
    "DUMMY_EXPRESSION_REGISTRY",
]
