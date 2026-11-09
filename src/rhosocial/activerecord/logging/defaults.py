# src/rhosocial/activerecord/logging/defaults.py
"""Default logging configuration for framework-level loggers."""

import logging
from typing import Optional

from .config import LoggingConfig

_ROOT_LOGGER = "rhosocial.activerecord"
_LOGGER_QUERY = "rhosocial.activerecord.query"
_LOGGER_TRANSACTION = "rhosocial.activerecord.transaction"
_LOGGER_CONNECTION = "rhosocial.activerecord.connection"

_default_logging_config = LoggingConfig()


def get_default_logging_config() -> LoggingConfig:
    return _default_logging_config


def reset_default_logging_config() -> None:
    global _default_logging_config
    _default_logging_config = LoggingConfig()


def configure_logging(
    level: Optional[int] = None,
    formatter: Optional[logging.Formatter] = None,
    propagate: Optional[bool] = None,
    auto_setup: Optional[bool] = None,
) -> None:
    """Adjust the framework-level logging defaults.

    Called with no arguments this is a no-op: the defaults are ``WARNING``,
    ``propagate=True`` and ``auto_setup=False``.  That means ActiveRecord
    never installs a handler and never writes to stderr on import; an
    application that wants detail raises the level or configures the root
    logger itself.

    Args:
        level: New default level for framework-level loggers.
        formatter: Formatter used when ``auto_setup`` installs a handler.
        propagate: Whether loggers propagate to their parent loggers.
        auto_setup: Whether ``get_logger`` installs a stream handler.
    """
    config = get_default_logging_config()
    if level is not None:
        config.default_level = level
    if formatter is not None:
        config.formatter = formatter
    if propagate is not None:
        config.propagate = propagate
    if auto_setup is not None:
        config.auto_setup = auto_setup


def get_logger(name: str) -> logging.Logger:
    return get_default_logging_config().get_logger(name)
