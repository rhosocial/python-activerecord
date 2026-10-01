# src/rhosocial/activerecord/logging/defaults.py
"""Default logging configuration for framework-level loggers."""

import logging
import dataclasses
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
    """Put the default config back to its factory state, in place.

    Assigning a fresh object was the alternative, and it needs a `global` --
    which is the only reason to prefer it is that the old one may be held
    elsewhere.  Nothing is: ``get_default_logging_config`` is the only reader,
    so replacing the value in place is invisible to callers and needs no
    rebinding.  A config that a caller captured by other means should not be
    resurrected by a test fixture anyway.
    """
    config = _default_logging_config
    fresh = LoggingConfig()
    # Enumerated rather than written out field by field.  The hand-written
    # version silently missed `auto_setup`, and a reset that restores five of
    # six fields is worse than one that does nothing: it looks like it worked.
    for f in dataclasses.fields(LoggingConfig):
        setattr(config, f.name, getattr(fresh, f.name))


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
