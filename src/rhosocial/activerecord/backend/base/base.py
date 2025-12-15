# src/rhosocial/activerecord/backend/base/base.py
import logging
from abc import ABC, abstractmethod

from ..config import ConnectionConfig
from ..dialect import SQLDialectBase
from ..type_registry import TypeRegistry
from ..type_adapter import (
    SQLTypeAdapter,
    DateTimeAdapter,
    JSONAdapter,
    UUIDAdapter,
    EnumAdapter,
    BooleanAdapter,
    DecimalAdapter,
)


class StorageBackendBase(ABC):
    """Minimal base for configuration and connection state only."""

    def _register_default_adapters(self) -> None:
        adapters = [
            DateTimeAdapter(), JSONAdapter(), UUIDAdapter(), EnumAdapter(),
            BooleanAdapter(), DecimalAdapter(),
        ]
        for adapter in adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type)
        self.logger.debug("Registered all standard type adapters.")

    def __init__(self, **kwargs) -> None:
        """Initialize storage backend with all required attributes."""
        # Configuration
        if "connection_config" not in kwargs or kwargs["connection_config"] is None:
            self.config = ConnectionConfig(**kwargs)
        else:
            self.config = kwargs["connection_config"]

        # Connection state
        self._connection = None
        self._transaction_level = 0
        self._transaction_manager = None
        self._cursor = None
        self._server_version_cache = None

        # Logger (for LoggingMixin)
        self._logger: Optional[logging.Logger] = kwargs.get('logger', logging.getLogger('storage'))

        # Capabilities (for CapabilityMixin)
        self._capabilities = None

        # Type Adaptation (for TypeAdaptionMixin)
        # Architectural Note: This registry is completely independent of the dialect.
        # It maps (Python Type, DBAPI Type) to a SQLTypeAdapter.
        self.adapter_registry = TypeRegistry()
        self._register_default_adapters()
        self.logger.info("Initialized TypeAdaptionMixin with SQLTypeAdapter registry.")

    @property
    @abstractmethod
    def dialect(self) -> SQLDialectBase:
        """Get SQL dialect."""
        pass
