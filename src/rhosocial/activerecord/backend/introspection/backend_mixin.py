# src/rhosocial/activerecord/backend/introspection/backend_mixin.py
"""
Mixin that adds the .introspector property to a backend class.

Usage
-----
class MyBackend(IntrospectorBackendMixin, StorageBackend):
    def _create_introspector(self):
        from .introspection import MyIntrospector
        from rhosocial.activerecord.backend.introspection.executor import (
            SyncIntrospectorExecutor,
        )
        return MyIntrospector(self, SyncIntrospectorExecutor(self))
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .base import AbstractIntrospector


class IntrospectorBackendMixin:
    """Mixin that provides the `introspector` property to a backend.

    The introspector is created lazily on first access via
    `_create_introspector()`, which concrete backends must implement.
    Users may also inject a custom introspector via `set_introspector()`.
    """

    _introspector_instance: Optional["AbstractIntrospector"] = None

    def _create_introspector(self) -> "AbstractIntrospector":
        """Create and return the introspector for this backend.

        Concrete backends must override this method.

        Example::

            def _create_introspector(self):
                from .introspection import MyDBIntrospector
                from rhosocial.activerecord.backend.introspection.executor import (
                    SyncIntrospectorExecutor,
                )
                return MyDBIntrospector(self, SyncIntrospectorExecutor(self))
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _create_introspector()"
        )

    @property
    def introspector(self) -> "AbstractIntrospector":
        """Return the introspector for this backend (lazily created)."""
        if self._introspector_instance is None:
            self._introspector_instance = self._create_introspector()
        return self._introspector_instance

    def set_introspector(self, introspector: "AbstractIntrospector") -> None:
        """Inject a custom introspector (useful for testing or extension).

        Args:
            introspector: The introspector instance to use from now on.
        """
        self._introspector_instance = introspector

    def reset_introspector(self) -> None:
        """Reset to the default introspector (created on next access)."""
        self._introspector_instance = None
