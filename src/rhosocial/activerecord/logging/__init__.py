# src/rhosocial/activerecord/logging/__init__.py
"""Logging utilities for ActiveRecord.

This module provides a unified logging system for ActiveRecord that:

- Does NOT modify the root logger and does NOT install handlers
- Emits nothing on import: only logger objects are created
- Propagates to the application's root logger by default
- Provides framework-level logging helpers through configure_logging()
- Supports custom formatters and log levels
- Supports explicit LoggingConfig objects for models and backends

Key Principle:
    The application owns logging.  ActiveRecord loggers default to
    ``WARNING``, have no handlers of their own, and propagate to their
    parents.  Silencing or enabling the library is therefore an application
    decision: set a level on the logger or configure the root logger.

Basic Usage:
    Configure ActiveRecord models::

        import logging
        from rhosocial.activerecord.logging import LoggingConfig
        from rhosocial.activerecord.model import ActiveRecord

        ActiveRecord.__logging_config__ = LoggingConfig(default_level=logging.INFO)

    Let the application's root configuration decide::

        import logging

        logging.basicConfig(level=logging.DEBUG)
        # Library loggers already propagate; no handler is installed by us.

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

from .formatter import (
    ModuleFormatter,
    ActiveRecordFormatter,
    ActiveRecordEventFormatter,
    ActiveRecordJsonFormatter,
)
from .events import LogEvent, DEFAULT_EVENT_TEMPLATES, log_event, render_event
from .redaction import (
    LogDataKind,
    LogPayload,
    ParamMeta,
    MASKERS,
    SensitiveValue,
    default_mask,
    get_masker,
    register_masker,
    unwrap_sensitive,
)
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
    "ActiveRecordEventFormatter",
    "ActiveRecordJsonFormatter",
    # Structured events
    "LogEvent",
    "DEFAULT_EVENT_TEMPLATES",
    "log_event",
    "render_event",
    # Redaction
    "LogDataKind",
    "LogPayload",
    "ParamMeta",
    "MASKERS",
    "SensitiveValue",
    "default_mask",
    "get_masker",
    "register_masker",
    "unwrap_sensitive",
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
