# src/rhosocial/activerecord/backend/introspection/backend_mixin.py
"""
Mixin that adds the .introspector property to a backend class.

Usage
-----
class MySyncBackend(IntrospectorBackendMixin, StorageBackend):
    def _create_introspector(self):
        from .introspection import SyncMyDBIntrospector
        from rhosocial.activerecord.backend.introspection.executor import (
            SyncIntrospectorExecutor,
        )
        return SyncMyDBIntrospector(self, SyncIntrospectorExecutor(self))

class MyAsyncBackend(IntrospectorBackendMixin, AsyncStorageBackend):
    def _create_introspector(self):
        from .introspection import AsyncMyDBIntrospector
        from rhosocial.activerecord.backend.introspection.executor import (
            AsyncIntrospectorExecutor,
        )
        return AsyncMyDBIntrospector(self, AsyncIntrospectorExecutor(self))
"""

from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .base import SyncAbstractIntrospector, AsyncAbstractIntrospector


class IntrospectorBackendMixin:
    """Mixin that provides the `introspector` property to a backend.

    The introspector is created lazily on first access via
    `_create_introspector()`, which concrete backends must implement.

    For sync backends, _create_introspector() should return a
    SyncAbstractIntrospector subclass.
    For async backends, it should return an AsyncAbstractIntrospector subclass.

    Example::

        class MyBackend(IntrospectorBackendMixin, StorageBackend):
            def _create_introspector(self):
                from .introspection import SyncMyDBIntrospector
                from rhosocial.activerecord.backend.introspection.executor import (
                    SyncIntrospectorExecutor,
                )
                return SyncMyDBIntrospector(self, SyncIntrospectorExecutor(self))
    """

    _introspector_instance: Optional[Union["SyncAbstractIntrospector", "AsyncAbstractIntrospector"]] = None

    def _create_introspector(self) -> Union["SyncAbstractIntrospector", "AsyncAbstractIntrospector"]:
        """Create the introspector instance.

        Subclasses must implement this method to return the appropriate
        introspector type (sync or async) based on whether the backend
        is synchronous or asynchronous.

        Returns:
            A SyncAbstractIntrospector for sync backends,
            or an AsyncAbstractIntrospector for async backends.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _create_introspector()"
        )

    @property
    def introspector(self) -> Union["SyncAbstractIntrospector", "AsyncAbstractIntrospector"]:
        """Get the introspector instance (created lazily)."""
        if self._introspector_instance is None:
            self._introspector_instance = self._create_introspector()
        return self._introspector_instance

    def set_introspector(
        self,
        introspector: Union["SyncAbstractIntrospector", "AsyncAbstractIntrospector"]
    ) -> None:
        """Inject a custom introspector (useful for testing or extension).

        Args:
            introspector: The introspector instance to use from now on.
        """
        self._introspector_instance = introspector

    def reset_introspector(self) -> None:
        """Reset to the default introspector (created on next access)."""
        self._introspector_instance = None
