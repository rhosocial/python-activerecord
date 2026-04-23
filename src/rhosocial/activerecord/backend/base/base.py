# src/rhosocial/activerecord/backend/base/base.py
import logging
from abc import ABC, abstractmethod
from typing import Optional

from ..config import ConnectionConfig
from ..dialect import SQLDialectBase
from ..type_adapter import (
    DateTimeAdapter,
    JSONAdapter,
    UUIDAdapter,
    EnumAdapter,
    BooleanAdapter,
    DecimalAdapter,
)
from ..type_registry import TypeRegistry


class StorageBackendBase(ABC):
    """Minimal base for configuration and connection state only.

    This base class provides:
    - Configuration management
    - Connection state tracking
    - Logger initialization
    - Type adapter registry
    """

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
        self._logger: Optional[logging.Logger] = kwargs.get("logger", logging.getLogger("storage"))

        # Initialize backend state
        self._capabilities = None  # Legacy attribute, kept for compatibility

        # Type Adaptation (for TypeAdaptionMixin)
        # Architectural Note: This registry is completely independent of the dialect.
        # It maps (Python Type, DBAPI Type) to a SQLTypeAdapter.
        self.adapter_registry = TypeRegistry()
        self._register_default_adapters()
        self.logger.info("Initialized TypeAdaptionMixin with SQLTypeAdapter registry.")

    def _register_default_adapters(self) -> None:
        """Register default type adapters."""
        adapters = [
            DateTimeAdapter(),
            JSONAdapter(),
            UUIDAdapter(),
            EnumAdapter(),
            BooleanAdapter(),
            DecimalAdapter(),
        ]
        for adapter in adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type)
        self.logger.debug("Registered all standard type adapters.")

    @property
    @abstractmethod
    def dialect(self) -> SQLDialectBase:
        """Get SQL dialect."""
        pass

    @property
    def threadsafety(self) -> int:
        """Return driver threadsafety level.

        Returns:
            0 = not thread-safe
            1 = safe when used only from the same thread (connections cannot be shared)
            2 = safe when used from multiple threads (connections can be shared)

        Backends should override this property to return the appropriate value
        based on their database driver's threadsafety.

        Note:
            This is not the DBAPI threadsafety level but the actual driver level.
            Some drivers (like psycopg) report threadsafety=1 in DBAPI but are
            actually thread-safe at the connection level.
        """
        return 1  # Conservative default: connections cannot be shared across threads
