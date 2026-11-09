# tests/rhosocial/activerecord_test/logging_module/test_events.py
"""Structured ActiveRecord event logging."""

import io
import json
import logging

from rhosocial.activerecord.logging import (
    ActiveRecordEventFormatter,
    ActiveRecordJsonFormatter,
    LogEvent,
    log_event,
    render_event,
)


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def test_log_event_keeps_structured_payload():
    logger = _logger("test.activerecord.events.payload")
    handler = _ListHandler()
    logger.addHandler(handler)

    log_event(
        logger,
        LogEvent.DML_INSERT,
        model="User",
        object_name="users",
        object_type="TABLE",
        rows_affected=1,
        duration_ms=12.4,
    )

    record = handler.records[0]
    assert record.event == LogEvent.DML_INSERT
    assert record.activerecord["model"] == "User"
    assert record.activerecord["rows_affected"] == 1
    assert "dml.insert" in record.getMessage()
    assert "object_name=users" in record.getMessage()


def test_event_formatter_uses_custom_template():
    logger = _logger("test.activerecord.events.template")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(
        ActiveRecordEventFormatter("%(message)s", templates={LogEvent.DQL_SELECT: "select {model}"})
    )
    logger.addHandler(handler)

    log_event(logger, LogEvent.DQL_SELECT, model="User")

    assert stream.getvalue().strip() == "select User"


def test_json_formatter_includes_event_and_fields():
    logger = _logger("test.activerecord.events.json")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ActiveRecordJsonFormatter())
    logger.addHandler(handler)

    log_event(
        logger,
        LogEvent.DQL_SELECT,
        model="User",
        object_name="users",
        object_type="TABLE",
        rows_returned=3,
        duration_ms=12.4,
    )

    payload = json.loads(stream.getvalue())
    assert payload["event"] == "dql.select"
    assert payload["model"] == "User"
    assert payload["rows_returned"] == 3


def test_unknown_event_renders_event_name():
    logger = _logger("test.activerecord.events.unknown")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ActiveRecordEventFormatter("%(message)s"))
    logger.addHandler(handler)

    log_event(logger, "custom.event", model="User")

    assert stream.getvalue().strip() == "custom.event"


def test_render_event_tolerates_missing_fields():
    result = render_event(LogEvent.DQL_SELECT, {})
    assert result.startswith("dql.select")
