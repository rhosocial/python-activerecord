# tests/support/logging.py
"""Restore framework logging state after an in-process CLI invocation."""

import logging
from contextlib import contextmanager

from rhosocial.activerecord.logging.defaults import get_default_logging_config

PREFIX = "rhosocial.activerecord"


def framework_loggers():
    return [
        logger
        for name, logger in logging.Logger.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
        and (name == PREFIX or name.startswith(PREFIX + "."))
    ]


@contextmanager
def preserve_logging():
    """Restore default logging config and framework logger levels afterwards."""
    config = get_default_logging_config()
    saved = (config.default_level, config.propagate, config.auto_setup)
    levels = [(logger, logger.level) for logger in framework_loggers()]
    try:
        yield
    finally:
        config.default_level, config.propagate, config.auto_setup = saved
        for logger, level in levels:
            logger.setLevel(level)
