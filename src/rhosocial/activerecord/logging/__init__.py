# src/rhosocial/activerecord/logging/__init__.py
"""Logging utilities for ActiveRecord.

This module provides a unified logging system for ActiveRecord that:

- Does NOT modify the root logger
- Provides framework-level logging helpers through configure_logging()
- Supports custom formatters and log levels
- Supports explicit LoggingConfig objects for models and backends

Key Principle:
    ActiveRecord logging is isolated from user's logging configuration.
    By default, logs do not propagate to the root logger.

Basic Usage:
    Configure ActiveRecord models::

        import logging
        from rhosocial.activerecord.logging import LoggingConfig
        from rhosocial.activerecord.model import ActiveRecord

        ActiveRecord.__logging_config__ = LoggingConfig(default_level=logging.INFO)

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

    Framework-level logger::

        from rhosocial.activerecord.logging import get_logger

        logger = get_logger('my_custom_logger')

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
from .config import LoggerConfig, LoggingConfig, LogDataMode
from .summarizer import SummarizerConfig, DataSummarizer
from .defaults import (
    configure_logging,
    get_logger,
    get_default_logging_config,
    reset_default_logging_config,
)
from .mixin import LoggingMixin, BackendLoggingMixin

__all__ = [
    # Formatters
    "ModuleFormatter",
    "ActiveRecordFormatter",
    # Configuration
    "LoggerConfig",
    "LoggingConfig",
    "LogDataMode",
    # Summarizer
    "SummarizerConfig",
    "DataSummarizer",
    # Framework-level defaults
    "configure_logging",
    "get_logger",
    "get_default_logging_config",
    "reset_default_logging_config",
    # Mixins
    "LoggingMixin",
    "BackendLoggingMixin",
]
