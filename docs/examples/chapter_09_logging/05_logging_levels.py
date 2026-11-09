"""
Logging Chapter: Example 5 - Default and explicit log levels

This example shows the quiet default and what appears when the application
raises the logger to INFO or DEBUG.  It does not touch the root logger.
"""

import logging
import sys

from rhosocial.activerecord.logging import (
    ActiveRecordEventFormatter,
    LogEvent,
    log_event,
)


def make_logger(name: str, level: int) -> logging.Logger:
    """Create an isolated logger writing event text to stdout."""
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ActiveRecordEventFormatter("%(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def emit_all(logger: logging.Logger, label: str) -> None:
    """Emit one event at each level so filtering is visible."""
    print(f"--- {label} (effective={logging.getLevelName(logger.getEffectiveLevel())}) ---")

    log_event(
        logger,
        LogEvent.DQL_SELECT,
        level=logging.DEBUG,
        model="User",
        object_name="users",
        object_type="table",
        rows_returned=3,
        duration_ms=12.4,
    )
    log_event(
        logger,
        LogEvent.DML_INSERT,
        level=logging.INFO,
        model="User",
        object_name="users",
        object_type="table",
        rows_affected=1,
        duration_ms=8.2,
    )
    log_event(
        logger,
        LogEvent.RELATION_BATCH_LOAD,
        level=logging.WARNING,
        relation="posts",
        rows_returned=5,
        cache_hit=False,
    )


def main() -> None:
    print("=" * 60)
    print("Example 5: Default and explicit log levels")
    print("=" * 60)

    root = logging.getLogger()
    original_root_level = root.level
    root.setLevel(logging.WARNING)
    try:
        # NOTSET inherits the root logger's WARNING: DEBUG and INFO stay silent.
        emit_all(make_logger("demo.logging.levels.default", logging.NOTSET), "default")

        # The application explicitly asks for INFO.
        emit_all(make_logger("demo.logging.levels.info", logging.INFO), "logger=INFO")

        # The application explicitly asks for DEBUG.
        emit_all(make_logger("demo.logging.levels.debug", logging.DEBUG), "logger=DEBUG")
    finally:
        root.setLevel(original_root_level)

    print("\nThe quiet default is inheritance, not a hard-coded WARNING on the library logger.")


if __name__ == "__main__":
    main()
