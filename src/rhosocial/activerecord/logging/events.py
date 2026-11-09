# src/rhosocial/activerecord/logging/events.py
"""Structured event names and helpers for ActiveRecord logging.

Library log records carry a stable ``event`` name and a structured
``activerecord`` payload.  Human-readable text and JSON formatters can render
the same record without changing the event schema.
"""

from typing import Any, Dict, Mapping, Optional

import logging


class LogEvent:
    """Stable event names used by ActiveRecord log records."""

    DML_INSERT = "dml.insert"
    DML_UPDATE = "dml.update"
    DML_DELETE = "dml.delete"
    DML_SOFT_DELETE = "dml.soft_delete"
    DML_BATCH = "dml.batch"

    DQL_SELECT = "dql.select"
    DQL_AGGREGATE = "dql.aggregate"
    DQL_CTE = "dql.cte"
    DQL_SET_OPERATION = "dql.set_operation"

    DDL_CREATE = "ddl.create"
    DDL_ALTER = "ddl.alter"
    DDL_DROP = "ddl.drop"

    TRANSACTION_BEGIN = "transaction.begin"
    TRANSACTION_COMMIT = "transaction.commit"
    TRANSACTION_ROLLBACK = "transaction.rollback"
    TRANSACTION_SAVEPOINT = "transaction.savepoint"

    MODEL_FIND_ONE = "model.find_one"
    MODEL_FIND_ONE_OR_CREATE = "model.find_one_or_create"

    RELATION_BATCH_LOAD = "relation.batch_load"

    WORKER_EXIT = "worker.exit"


#: Default event templates.  Every field is optional in the template because
#: ``log_event`` may be called from code that does not know all context.
DEFAULT_EVENT_TEMPLATES: Dict[str, str] = {
    LogEvent.DML_INSERT: (
        "dml.insert model={model} object_name={object_name} "
        "object_type={object_type} rows_affected={rows_affected} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.DML_UPDATE: (
        "dml.update model={model} object_name={object_name} "
        "object_type={object_type} rows_affected={rows_affected} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.DML_DELETE: (
        "dml.delete model={model} object_name={object_name} "
        "object_type={object_type} rows_affected={rows_affected} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.DML_SOFT_DELETE: (
        "dml.soft_delete model={model} object_name={object_name} "
        "object_type={object_type} rows_affected={rows_affected} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.DML_BATCH: (
        "dml.batch model={model} operation={operation} "
        "parameter_sets={parameter_sets} rows_affected={rows_affected} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.DQL_SELECT: (
        "dql.select model={model} object_name={object_name} "
        "object_type={object_type} rows_returned={rows_returned} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.DQL_AGGREGATE: (
        "dql.aggregate model={model} operation={operation} "
        "rows_returned={rows_returned} duration_ms={duration_ms}"
    ),
    LogEvent.DQL_CTE: (
        "dql.cte model={model} object_name={object_name} "
        "rows_returned={rows_returned} duration_ms={duration_ms}"
    ),
    LogEvent.DQL_SET_OPERATION: (
        "dql.set_operation operation={operation} "
        "rows_returned={rows_returned} duration_ms={duration_ms}"
    ),
    LogEvent.DDL_CREATE: (
        "ddl.create object_name={object_name} object_type={object_type} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.DDL_ALTER: (
        "ddl.alter object_name={object_name} object_type={object_type} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.DDL_DROP: (
        "ddl.drop object_name={object_name} object_type={object_type} "
        "duration_ms={duration_ms}"
    ),
    LogEvent.TRANSACTION_BEGIN: "transaction.begin isolation={isolation}",
    LogEvent.TRANSACTION_COMMIT: "transaction.commit duration_ms={duration_ms}",
    LogEvent.TRANSACTION_ROLLBACK: (
        "transaction.rollback reason={reason} duration_ms={duration_ms}"
    ),
    LogEvent.TRANSACTION_SAVEPOINT: (
        "transaction.savepoint operation={operation} name={savepoint}"
    ),
    LogEvent.MODEL_FIND_ONE: "model.find_one model={model} found={found}",
    LogEvent.MODEL_FIND_ONE_OR_CREATE: (
        "model.find_one_or_create model={model} created={created}"
    ),
    LogEvent.RELATION_BATCH_LOAD: (
        "relation.batch_load relation={relation} count={rows_returned} "
        "cache_hit={cache_hit}"
    ),
    LogEvent.WORKER_EXIT: "worker.exit worker={worker} reason={reason}",
}


class _SafeFormatDict(dict):
    """Format mapping that leaves missing fields empty instead of raising."""

    def __missing__(self, key: str) -> str:
        return ""


def render_event(
    event: str,
    fields: Mapping[str, Any],
    templates: Optional[Mapping[str, str]] = None,
) -> str:
    """Render an event using its template, or return the event name."""
    template = (templates or DEFAULT_EVENT_TEMPLATES).get(event)
    if template is None:
        return event

    values: Dict[str, Any] = dict(fields)
    values.setdefault("event", event)
    try:
        return template.format_map(_SafeFormatDict(values))
    except Exception:
        # A malformed user template must not break the application log call.
        return event


def log_event(
    logger: logging.Logger,
    event: str,
    *,
    level: int = logging.INFO,
    message: Optional[str] = None,
    templates: Optional[Mapping[str, str]] = None,
    **fields: Any,
) -> None:
    """Log one structured ActiveRecord event.

    Args:
        logger: Logger to write to.
        event: Stable event name, usually one of :class:`LogEvent`.
        level: Log level, defaults to INFO.
        message: Optional pre-rendered message; when omitted the event template
            renders one.
        templates: Optional template mapping overriding the defaults.
        **fields: Structured event fields.  They are stored in the record's
            ``activerecord`` payload and are never formatted as SQL parameters.
    """
    if not logger.isEnabledFor(level):
        return

    payload = dict(fields)
    if message is None:
        message = render_event(event, payload, templates)

    logger.log(level, message, extra={"event": event, "activerecord": payload})
