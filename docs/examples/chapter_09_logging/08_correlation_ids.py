"""
Logging Chapter: Example 8 - Correlation IDs in JSON logs

This example shows how an application-owned contextvars filter adds
request_id/trace_id/span_id to every record, including library events.
"""

import contextvars
import logging
import sys

from rhosocial.activerecord.logging import (
    ActiveRecordJsonFormatter,
    LogEvent,
    log_event,
)

request_id_var = contextvars.ContextVar("request_id", default=None)
trace_id_var = contextvars.ContextVar("trace_id", default=None)
span_id_var = contextvars.ContextVar("span_id", default=None)


class CorrelationFilter(logging.Filter):
    """Copy application correlation values onto each LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.trace_id = trace_id_var.get()
        record.span_id = span_id_var.get()
        return True


def make_logger() -> logging.Logger:
    logger = logging.getLogger("demo.correlation")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ActiveRecordJsonFormatter())
    handler.addFilter(CorrelationFilter())
    logger.addHandler(handler)
    return logger


def emit_for_request(
    logger: logging.Logger,
    request_id: str,
    trace_id: str,
    span_id: str,
) -> None:
    tokens = (
        request_id_var.set(request_id),
        trace_id_var.set(trace_id),
        span_id_var.set(span_id),
    )
    try:
        log_event(
            logger,
            LogEvent.DQL_SELECT,
            model="User",
            object_name="users",
            object_type="table",
            rows_returned=3,
            duration_ms=12.4,
        )
        log_event(
            logger,
            LogEvent.DML_UPDATE,
            model="User",
            object_name="users",
            object_type="table",
            rows_affected=1,
            duration_ms=8.2,
        )
    finally:
        for var, token in zip((request_id_var, trace_id_var, span_id_var), tokens):
            var.reset(token)


def main() -> None:
    print("=" * 60)
    print("Example 8: Correlation IDs in JSON logs")
    print("=" * 60)

    logger = make_logger()

    emit_for_request(logger, "req-alpha", "trace-alpha", "span-alpha-1")
    emit_for_request(logger, "req-beta", "trace-beta", "span-beta-1")

    print("\nELK/Kibana can group both events with request_id: \"req-alpha\" or trace_id: \"trace-alpha\".")


if __name__ == "__main__":
    main()
