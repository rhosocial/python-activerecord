"""
Logging Chapter: Example 6 - Structured events and formatters

This example shows the same structured event rendered as human-readable text
and as one JSON object per line.  The event schema is shared by both.
"""

import logging
import sys

from rhosocial.activerecord.logging import (
    ActiveRecordEventFormatter,
    ActiveRecordJsonFormatter,
    LogEvent,
    log_event,
)


def make_logger(name: str, formatter: logging.Formatter) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def emit_events(logger: logging.Logger) -> None:
    log_event(
        logger,
        LogEvent.DML_INSERT,
        model="User",
        model_fqn="app.models.User",
        operation="insert",
        object_name="users",
        object_type="table",
        schema="public",
        database="app",
        rows_affected=1,
        parameter_sets=1,
        param_count=3,
        duration_ms=12.4,
    )
    log_event(
        logger,
        LogEvent.DQL_SELECT,
        model="User",
        model_fqn="app.models.User",
        operation="select",
        object_name="users",
        object_type="table",
        schema="public",
        database="app",
        rows_returned=3,
        param_count=2,
        duration_ms=8.2,
    )
    log_event(
        logger,
        LogEvent.DML_BATCH,
        model="OrderItem",
        operation="insert_many",
        object_name="order_items",
        object_type="table",
        parameter_sets=100,
        rows_affected=100,
        duration_ms=120.5,
    )
    log_event(
        logger,
        LogEvent.TRANSACTION_COMMIT,
        isolation="read_committed",
        duration_ms=2.1,
    )
    log_event(
        logger,
        LogEvent.RELATION_BATCH_LOAD,
        relation="posts",
        rows_returned=5,
        cache_hit=False,
    )


def main() -> None:
    print("=" * 60)
    print("Example 6: Structured events and formatters")
    print("=" * 60)

    print("\n--- ActiveRecordEventFormatter (text) ---")
    emit_events(make_logger("demo.events.text", ActiveRecordEventFormatter()))

    print("\n--- ActiveRecordJsonFormatter (one JSON object per line) ---")
    emit_events(make_logger("demo.events.json", ActiveRecordJsonFormatter()))

    print("\nEvents carry record.event and record.activerecord; formatters only render them.")


if __name__ == "__main__":
    main()
