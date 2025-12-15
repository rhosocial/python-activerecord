# src/rhosocial/activerecord/backend/base/capability.py
from abc import abstractmethod
from ..capabilities import DatabaseCapabilities

class CapabilityMixin:
    """Mixin for database capability management."""
    @property
    def capabilities(self) -> DatabaseCapabilities:
        if self._capabilities is None:
            self._capabilities = self._initialize_capabilities()
        return self._capabilities
    @abstractmethod
    def _initialize_capabilities(self) -> DatabaseCapabilities:
        pass