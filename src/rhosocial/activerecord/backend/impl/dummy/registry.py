# src/rhosocial/activerecord/backend/impl/dummy/registry.py
"""The dummy backend's expression registry.

The dummy backend owns the kinds its own expression module declares. It does
not own core's kinds and it does not list any other backend's: the overlap with
core is expressed by composition — ``base=core_registry()`` — and there is no
cross-backend merge anywhere.

The registry is built on first use, cached, and frozen. Freezing is what lets
the dialect hand the same table to every reader without one caller's
registration changing what another caller resolves.
"""

from rhosocial.activerecord.backend.expression.registry import ExpressionRegistry
from rhosocial.activerecord.backend.expression.serialization import (
    core_registry,
    registry_for_packages,
)

#: The dummy backend exposes its expressions from a single module, not a package.
_DUMMY_EXPRESSION_MODULE = "rhosocial.activerecord.backend.impl.dummy.expression"

_backend_registry = None


def backend_registry() -> ExpressionRegistry:
    """The dummy backend's registry: core's kinds plus its own, frozen and cached.

    Returns:
        The frozen registry ``DummyDialect.artifact_registry()`` exposes.
    """
    global _backend_registry
    if _backend_registry is None:
        # Build into a local and publish only on success: a half-populated
        # instance cached under the module global would make every later call
        # fail with a confusing "no such kind" instead of the real cause.
        _backend_registry = registry_for_packages(
            _DUMMY_EXPRESSION_MODULE,
            base=core_registry(),
        )
    return _backend_registry
