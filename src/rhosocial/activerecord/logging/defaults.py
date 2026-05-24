# src/rhosocial/activerecord/logging/defaults.py
"""Default logging configuration for framework-level loggers."""

import logging
from typing import Optional

from .config import LoggingConfig

_ROOT_LOGGER = "rhosocial.activerecord"
_LOGGER_MODEL = "rhosocial.activerecord.model"
_LOGGER_BACKEND = "rhosocial.activerecord.backend"
_LOGGER_QUERY = "rhosocial.activerecord.query"
_LOGGER_TRANSACTION = "rhosocial.activerecord.transaction"
_LOGGER_WORKER = "rhosocial.activerecord.worker"
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
