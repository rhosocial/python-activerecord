# src/rhosocial/activerecord/backend/expression_registry/core_registry.py
"""Core's expression table: the kinds core owns, and nothing else.

``CORE_EXPRESSIONS`` is core's own data: a ``kind -> fully qualified class
name`` mapping collected from the expression package core ships. It knows no
backend and no dialect, so a backend composes its table by merging this
mapping with its own.

``CORE_EXPRESSION_REGISTRY`` is the frozen table built from that mapping. It is
assembled once, at import of this module, because the mapping is data: there is
no discovery left to defer, and a read only resolves a name to a class when an
artifact names it.
"""

from .registration import collect_expressions
from .registry import ExpressionRegistry

#: Core's kinds: ``kind`` -> fully qualified class name. No backend appears
#: here, and nothing outside core contributes to it.
CORE_EXPRESSIONS = collect_expressions("rhosocial.activerecord.backend.expression")

#: Core's frozen table, built from :data:`CORE_EXPRESSIONS`.
CORE_EXPRESSION_REGISTRY = ExpressionRegistry(CORE_EXPRESSIONS).freeze()
