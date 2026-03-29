# src/rhosocial/activerecord/logging/mixin.py
"""Logging mixin for ActiveRecord models and backends.

This module provides mixin classes that add logging functionality
to ActiveRecord models and backend implementations.
"""

import inspect
import logging
from typing import Optional, ClassVar

from .formatter import ActiveRecordFormatter
from .manager import get_logging_manager


class LoggingMixin:
    """Mixin providing logging functionality for ActiveRecord model classes.

    This mixin provides a unified logging interface for model classes.
    It supports:
    - Class-level logger configuration via __logger__ attribute
    - Automatic stack level calculation for correct source attribution
    - Optional formatter auto-setup (does NOT modify root logger)

    The mixin is designed to be inherited by model base classes.

    Class Attributes:
        __logger__: Optional class-level logger instance. If None, uses
            the global configuration's default logger.

    Usage:
        class MyModel(LoggingMixin, BaseModel):
            __table_name__ = "my_table"

            def save(self):
                self.log(logging.INFO, "Saving record")
    """

    # Class-level logger (can be overridden by subclasses)
    __logger__: ClassVar[Optional[logging.Logger]] = None

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Get the logger for this class.

        Returns the class-level __logger__ if set, otherwise creates
        a logger using the global configuration.

        Returns:
            logging.Logger: The logger instance for this class.
        """
        if hasattr(cls, '__logger__') and cls.__logger__ is not None:
            return cls.__logger__

        # Get default logger from manager
        logger_name = cls._get_logger_name()
        return get_logging_manager().get_logger(logger_name)

    @classmethod
    def _get_logger_name(cls) -> str:
        """Determine the appropriate logger name for this class.

        Subclasses can override this to customize logger naming.

        Returns:
            str: The logger name (default: 'activerecord').
        """
        # Default to 'activerecord' for models
        return get_logging_manager().LOGGER_MODEL

    @classmethod
    def set_logger(cls, logger: logging.Logger) -> None:
        """Set the class-level logger.

        Args:
            logger: A logging.Logger instance, or None to use default.

        Raises:
            ValueError: If logger is not a logging.Logger instance.

        Example:
            >>> import logging
            >>> custom_logger = logging.getLogger('myapp.user')
            >>> User.set_logger(custom_logger)
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        cls.__logger__ = logger

    @classmethod
    def setup_logger(cls, formatter: Optional[logging.Formatter] = None) -> None:
        """Setup the logger with a formatter.

        This method configures the formatter for the class logger.
        IMPORTANT: It does NOT modify the root logger.

        Args:
            formatter: Optional custom formatter. If None, uses default
                ActiveRecordFormatter.

        Note:
            This method only affects the current logger's handlers.
            It will not modify the root logger or any other logger.
        """
        logger = cls.get_logger()
        if logger is None:
            return

        if formatter is None:
            formatter = ActiveRecordFormatter()

        # Only modify this logger's handlers, NOT root logger
        if logger.handlers:
            for handler in logger.handlers:
                handler.setFormatter(formatter)
        # If no handlers, the manager will add one with the correct formatter
        # when the first log is written (if auto_setup is enabled)

    @classmethod
    def log(cls, level: int, msg: str, *args, **kwargs) -> None:
        """Log a message at the specified level.

        This method calculates the correct stack level so that log messages
        show the actual source location (caller's file and line number).

        Args:
            level: Log level (e.g., logging.DEBUG, logging.INFO).
            msg: Log message format string.
            *args: Additional arguments for message formatting.
            **kwargs: Additional keyword arguments for logging.

        Note:
            The 'offset' keyword argument can be used to adjust stack level
            for deeply nested calls.
        """
        logger = cls.get_logger()
        if logger is None:
            return

        # Calculate stack level for correct source attribution
        current_frame = inspect.currentframe()
        if current_frame is not None:
            current_frame = current_frame.f_back

        stack_level = 1
        while current_frame:
            frame_name = current_frame.f_globals.get("__name__", "")
            # Skip internal frames (ActiveRecord modules)
            if not frame_name.startswith("rhosocial.activerecord"):
                break
            current_frame = current_frame.f_back
            stack_level += 1

        if current_frame:
            stack_level += 1

        # Allow custom offset for edge cases
        if "offset" in kwargs:
            stack_level += kwargs.pop("offset")

        # Auto-setup formatter if needed (only for this logger, not root)
        manager = get_logging_manager()
        if manager.config.auto_setup:
            if not logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(manager.config.formatter)
                logger.addHandler(handler)

        # Use the appropriate log method
        level_name = logging.getLevelName(level).lower()
        method = getattr(logger, level_name, None)
        if method is not None:
            method(msg, *args, stacklevel=stack_level, **kwargs)
        else:
            logger.log(level, msg, *args, **kwargs)


class BackendLoggingMixin:
    """Logging mixin specifically for Backend classes.

    This mixin is designed for storage backend implementations.
    It uses 'storage' as the default logger name.

    Instance Attributes:
        _logger: Instance-level logger storage.

    Usage:
        class MyBackend(BackendLoggingMixin, StorageBackend):
            def execute(self, query):
                self.log(logging.DEBUG, f"Executing: {query}")
    """

    _logger: Optional[logging.Logger] = None

    @property
    def logger(self) -> logging.Logger:
        """Get the backend logger.

        Returns:
            logging.Logger: The logger instance for this backend.
        """
        if self._logger is None:
            self._logger = get_logging_manager().get_storage_logger()
        return self._logger

    @logger.setter
    def logger(self, value: Optional[logging.Logger]) -> None:
        """Set the backend logger.

        Args:
            value: A logging.Logger instance, or None to use default.

        Raises:
            ValueError: If value is not a logging.Logger instance.
        """
        if value is not None and not isinstance(value, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        self._logger = value

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log a message at the specified level.

        Args:
            level: Log level (e.g., logging.DEBUG, logging.INFO).
            msg: Log message format string.
            *args: Additional arguments for message formatting.
            **kwargs: Additional keyword arguments for logging.
        """
        current_frame = inspect.currentframe()
        if current_frame is not None:
            current_frame = current_frame.f_back

        stack_level = 1
        while current_frame:
            frame_name = current_frame.f_globals.get("__name__", "")
            if not frame_name.startswith("rhosocial.activerecord"):
                break
            current_frame = current_frame.f_back
            stack_level += 1

        if current_frame:
            stack_level += 1

        self.logger.log(level, msg, *args, stacklevel=stack_level, **kwargs)
