# src/rhosocial/activerecord/logging/__init__.py
"""Logging utilities for ActiveRecord.

This module provides a unified logging system for ActiveRecord that:

- Does NOT modify the root logger
- Allows global configuration through configure_logging()
- Supports custom formatters and log levels
- Provides consistent logging across Model and Backend classes

Key Principle:
    ActiveRecord logging is isolated from user's logging configuration.
    By default, logs do not propagate to the root logger.

Basic Usage:
    Simple configuration::

        import logging
        from rhosocial.activerecord.logging import configure_logging

        # Configure logging for ActiveRecord
        configure_logging(level=logging.INFO)

        # Now ActiveRecord will log at INFO level

Advanced Usage:
    Custom formatter::

        from rhosocial.activerecord.logging import (
            configure_logging,
            ActiveRecordFormatter,
        )

        formatter = ActiveRecordFormatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
        )
        configure_logging(level=logging.DEBUG, formatter=formatter)

    Access logging manager::

        from rhosocial.activerecord.logging import get_logging_manager

        manager = get_logging_manager()
        logger = manager.get_logger('my_custom_logger')

Custom Logger for a Model:
    Set a custom logger for a specific model::

        import logging
        from myapp.models import User

        # Set a custom logger for a specific model
        custom_logger = logging.getLogger('myapp.user_model')
        User.set_logger(custom_logger)

    Disable logging for a model::

        User.set_logger(None)
"""

from .formatter import ModuleFormatter, ActiveRecordFormatter
from .config import LoggerConfig, LoggingConfig
from .summarizer import (
    SummarizerConfig,
    DataSummarizer,
    get_default_summarizer,
    set_default_summarizer,
    summarize_data,
)
from .manager import (
    LoggingManager,
    get_logging_manager,
    configure_logging,
    get_logger,
)
from .mixin import LoggingMixin, BackendLoggingMixin

__all__ = [
    # Formatters
    "ModuleFormatter",
    "ActiveRecordFormatter",
    # Configuration
    "LoggerConfig",
    "LoggingConfig",
    # Summarizer
    "SummarizerConfig",
    "DataSummarizer",
    "get_default_summarizer",
    "set_default_summarizer",
    "summarize_data",
    # Manager
    "LoggingManager",
    "get_logging_manager",
    "configure_logging",
    "get_logger",
    # Mixins
    "LoggingMixin",
    "BackendLoggingMixin",
]
