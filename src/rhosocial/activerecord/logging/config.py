# src/rhosocial/activerecord/logging/config.py
"""Logging configuration for ActiveRecord.

This module provides configuration classes for managing logging
settings across ActiveRecord components.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import logging

from .formatter import ActiveRecordFormatter


@dataclass
class LoggerConfig:
    """Configuration for a single logger.

    This class defines the settings for an individual logger instance.

    Attributes:
        name: The name of the logger (e.g., 'activerecord', 'storage').
        level: The logging level (default: DEBUG).
        propagate: Whether to propagate logs to parent loggers (default: False).
        handlers: List of handlers to attach to the logger.
    """

    name: str
    level: int = logging.DEBUG
    propagate: bool = False
    handlers: List[logging.Handler] = field(default_factory=list)

    def create_logger(self) -> logging.Logger:
        """Create and configure a logger instance.

        Returns:
            Configured logging.Logger instance.
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        logger.propagate = self.propagate

        for handler in self.handlers:
            if handler not in logger.handlers:
                logger.addHandler(handler)

        return logger


@dataclass
class LoggingConfig:
    """Global logging configuration for ActiveRecord.

    This configuration controls how ActiveRecord creates and manages loggers.
    Users can customize logging behavior through this class.

    Key principle: This configuration does NOT modify the root logger.
    All loggers created through this config have propagate=False by default,
    preventing logs from bubbling up to the root logger.

    Attributes:
        default_level: Default log level for all ActiveRecord loggers.
        propagate: Whether to propagate logs to parent loggers (default: False).
        formatter: Default formatter for handlers.
        loggers: Logger configurations by category.
        auto_setup: Whether to auto-setup handlers when first log is written.

    Example:
        >>> config = LoggingConfig(
        ...     default_level=logging.INFO,
        ...     propagate=False,
        ...     auto_setup=True
        ... )
        >>> logger = config.get_logger('activerecord')
    """

    # Default log level for all ActiveRecord loggers
    default_level: int = logging.DEBUG

    # Whether to propagate logs to parent loggers (including root)
    # Default False to avoid polluting user's root logger
    propagate: bool = False

    # Default formatter class or instance
    formatter: logging.Formatter = field(default_factory=ActiveRecordFormatter)

    # Logger configurations by category
    loggers: Dict[str, LoggerConfig] = field(default_factory=dict)

    # Whether to auto-setup handlers when first log is written
    auto_setup: bool = True

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the configured settings.

        This method creates a logger that is isolated from the root logger
        by default (propagate=False), preventing ActiveRecord logs from
        appearing in user's root logger handlers unless explicitly configured.

        Args:
            name: The name of the logger to create/get.

        Returns:
            Configured logging.Logger instance.
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.default_level)
        logger.propagate = self.propagate

        # Check if there's a specific config for this logger
        if name in self.loggers:
            config = self.loggers[name]
            logger.setLevel(config.level)
            logger.propagate = config.propagate
            for handler in config.handlers:
                if handler not in logger.handlers:
                    logger.addHandler(handler)

        # Auto-setup handler if enabled and no handlers exist
        if self.auto_setup and not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(self.formatter)
            logger.addHandler(handler)

        return logger

    def add_logger_config(self, config: LoggerConfig) -> None:
        """Add a specific logger configuration.

        Args:
            config: LoggerConfig instance to add.
        """
        self.loggers[config.name] = config
