# tests/rhosocial/activerecord_test/feature/cli/logging_isolation.py
"""Restore framework logging state after an in-process CLI invocation.

``cli.main()`` is a process entry point: it configures framework loggers for
the command that is about to run and never restores them, because the process
is expected to exit. In the test suite many CLI runs share one pytest process,
so an unguarded call leaks a WARNING level into later tests, including the
execution-logging contract tests. This context manager snapshots and restores
the global default config and every existing framework logger level.
"""

import logging
from contextlib import contextmanager

from rhosocial.activerecord.logging.defaults import get_default_logging_config

_PREFIX = "rhosocial.activerecord"


def _framework_loggers():
    return [
        (name, logger)
        for name, logger in logging.Logger.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
        and (name == _PREFIX or name.startswith(_PREFIX + "."))
    ]


@contextmanager
def preserve_logging():
    """Restore default logging config and framework logger levels afterwards."""
    config = get_default_logging_config()
    saved = (config.default_level, config.propagate, config.auto_setup)
    levels = [(logger, logger.level) for _, logger in _framework_loggers()]
    try:
        yield
    finally:
        config.default_level, config.propagate, config.auto_setup = saved
        for logger, level in levels:
            logger.setLevel(level)
