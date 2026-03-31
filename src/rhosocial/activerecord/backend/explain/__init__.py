# src/rhosocial/activerecord/backend/explain/__init__.py
"""
Backend EXPLAIN support — protocols, mixins, and result base class.

Quick start::

    from rhosocial.activerecord.backend.explain import (
        BaseExplainResult,
        SyncExplainBackendProtocol,
        AsyncExplainBackendProtocol,
        SyncExplainBackendMixin,
        AsyncExplainBackendMixin,
    )
"""

from .types import BaseExplainResult
from .protocols import SyncExplainBackendProtocol, AsyncExplainBackendProtocol
from .backend_mixin import (
    _ExplainMixinBase,
    SyncExplainBackendMixin,
    AsyncExplainBackendMixin,
)

__all__ = [
    # Result base class
    "BaseExplainResult",
    # Protocols (sync / async — strictly separated)
    "SyncExplainBackendProtocol",
    "AsyncExplainBackendProtocol",
    # Mixins (sync / async — strictly separated)
    "_ExplainMixinBase",
    "SyncExplainBackendMixin",
    "AsyncExplainBackendMixin",
]
