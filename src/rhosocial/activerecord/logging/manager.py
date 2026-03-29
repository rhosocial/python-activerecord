# src/rhosocial/activerecord/logging/manager.py
"""Global logging manager for ActiveRecord.

This module provides a centralized logging management system for ActiveRecord.
It allows users to configure logging behavior globally without modifying
the root logger.
"""

import logging
from typing import Optional, Type

from .config import LoggingConfig, LoggerConfig
from .formatter import ActiveRecordFormatter, ModuleFormatter


class LoggingManager:
    """Global manager for ActiveRecord logging configuration.

    This class provides a single entry point for configuring logging
    across all ActiveRecord components. It does NOT modify the root logger.

    The manager is implemented as a singleton to ensure consistent
    logging configuration across the entire application.

    Predefined Logger Names:
        - LOGGER_MODEL ('activerecord'): For model operations
        - LOGGER_STORAGE ('storage'): For backend/storage operations
        - LOGGER_TRANSACTION ('transaction'): For transaction operations

    Usage:
        Basic configuration::

            from rhosocial.activerecord.logging import configure_logging
            configure_logging(level=logging.INFO)

        Advanced configuration::

            from rhosocial.activerecord.logging import get_logging_manager
            manager = get_logging_manager()
            manager.configure(
                default_level=logging.DEBUG,
                formatter=MyCustomFormatter(),
                propagate=False
            )

        Get a specific logger::

            logger = manager.get_logger('activerecord')
    """

    _instance: Optional['LoggingManager'] = None
    _config: LoggingConfig

    # Predefined logger names
    LOGGER_MODEL = 'activerecord'      # For model operations
    LOGGER_STORAGE = 'storage'         # For backend/storage operations
    LOGGER_TRANSACTION = 'transaction' # For transaction operations

    def __new__(cls) -> 'LoggingManager':
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = LoggingConfig()
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'LoggingManager':
        """Get the singleton instance.

        Returns:
            The singleton LoggingManager instance.
        """
        return cls()

    def configure(
        self,
        level: Optional[int] = None,
        formatter: Optional[logging.Formatter] = None,
        propagate: Optional[bool] = None,
        auto_setup: Optional[bool] = None,
    ) -> None:
        """Configure global logging settings.

        This method allows users to customize the logging behavior
        for all ActiveRecord components.

        Args:
            level: Default log level for all ActiveRecord loggers.
                Common values: logging.DEBUG, logging.INFO, logging.WARNING.
            formatter: Default formatter instance for log messages.
                Can be a custom formatter or ActiveRecordFormatter.
            propagate: Whether to propagate logs to parent loggers.
                Default is False to avoid polluting user's root logger.
            auto_setup: Whether to auto-create handlers on first use.
                Default is True for convenience.

        Example:
            >>> manager.configure(
            ...     level=logging.INFO,
            ...     propagate=False
            ... )
        """
        if level is not None:
            self._config.default_level = level
        if formatter is not None:
            self._config.formatter = formatter
        if propagate is not None:
            self._config.propagate = propagate
        if auto_setup is not None:
            self._config.auto_setup = auto_setup

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the current configuration.

        Args:
            name: The name of the logger to get/create.

        Returns:
            Configured logging.Logger instance.
        """
        return self._config.get_logger(name)

    def get_model_logger(self) -> logging.Logger:
        """Get the default logger for model operations.

        Returns:
            Logger named 'activerecord'.
        """
        return self.get_logger(self.LOGGER_MODEL)

    def get_storage_logger(self) -> logging.Logger:
        """Get the default logger for storage operations.

        Returns:
            Logger named 'storage'.
        """
        return self.get_logger(self.LOGGER_STORAGE)

    def get_transaction_logger(self) -> logging.Logger:
        """Get the default logger for transaction operations.

        Returns:
            Logger named 'transaction'.
        """
        return self.get_logger(self.LOGGER_TRANSACTION)

    @property
    def config(self) -> LoggingConfig:
        """Get the current configuration.

        Returns:
            The current LoggingConfig instance.
        """
        return self._config

    def reset(self) -> None:
        """Reset the configuration to defaults.

        This is mainly useful for testing purposes.
        """
        self._config = LoggingConfig()


# Module-level convenience functions

def get_logging_manager() -> LoggingManager:
    """Get the global logging manager instance.

    Returns:
        The singleton LoggingManager instance.

    Example:
        >>> manager = get_logging_manager()
        >>> manager.configure(level=logging.INFO)
    """
    return LoggingManager.get_instance()


def configure_logging(
    level: Optional[int] = None,
    formatter: Optional[logging.Formatter] = None,
    propagate: Optional[bool] = None,
    auto_setup: Optional[bool] = None,
) -> None:
    """Configure ActiveRecord logging globally.

    This is the recommended entry point for users to customize logging.
    It provides a simple interface for common logging configurations.

    Args:
        level: Default log level (e.g., logging.INFO, logging.DEBUG).
            If None, uses default (DEBUG).
        formatter: Custom formatter instance.
            If None, uses ActiveRecordFormatter with default format.
        propagate: Whether to propagate logs to parent loggers.
            Default is False to avoid polluting root logger.
        auto_setup: Whether to auto-create handlers on first use.
            Default is True.

    Example:
        Simple configuration::

            import logging
            from rhosocial.activerecord.logging import configure_logging

            configure_logging(level=logging.INFO)

        With custom formatter::

            from rhosocial.activerecord.logging import (
                configure_logging,
                ActiveRecordFormatter
            )

            configure_logging(
                level=logging.DEBUG,
                formatter=ActiveRecordFormatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                )
            )
    """
    manager = get_logging_manager()
    manager.configure(
        level=level,
        formatter=formatter,
        propagate=propagate,
        auto_setup=auto_setup
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger configured with ActiveRecord settings.

    Args:
        name: The name of the logger to get.

    Returns:
        Configured logging.Logger instance.

    Example:
        >>> logger = get_logger('myapp.custom')
        >>> logger.info("Custom log message")
    """
    return get_logging_manager().get_logger(name)
