# src/rhosocial/activerecord/backend/base/execution_logging.py
"""Backend execution logging helpers.

SQL text and parameter values are logged here and nowhere else.  Query and
model layers attach a :class:`~rhosocial.activerecord.backend.options.LogContext`
so the backend can emit one ``DEBUG`` SQL record and one ``INFO`` summary.
"""

import logging
from typing import Any, Dict, List, Optional

from ...logging import LogDataKind, LogEvent, LogPayload, log_event
from ..options import ExecutionOptions, LogContext
from ..schema import StatementType


_dql_types = (StatementType.DQL, StatementType.SELECT)
_dml_types = (
    StatementType.DML,
    StatementType.INSERT,
    StatementType.UPDATE,
    StatementType.DELETE,
    StatementType.TRUNCATE,
    StatementType.MERGE,
)


def _category(stmt_type: StatementType) -> str:
    """Return the event-schema statement category for a statement type."""
    if stmt_type in _dql_types:
        return "DQL"
    if stmt_type in _dml_types:
        return "DML"
    if stmt_type is StatementType.DDL:
        return "DDL"
    if stmt_type is StatementType.TCL:
        return "TCL"
    return "OTHER"


def _model_name(context: Optional[LogContext]) -> Optional[str]:
    if context is None or context.model is None:
        return None
    return getattr(context.model, "__name__", str(context.model))


def _model_fqn(context: Optional[LogContext]) -> Optional[str]:
    if context is None or context.model is None:
        return None
    if context.model_fqn:
        return context.model_fqn
    module = getattr(context.model, "__module__", None)
    name = getattr(context.model, "__name__", None)
    if module and name and not module.startswith("builtins"):
        return f"{module}.{name}"
    return name


def _first_keyword(sql: str) -> str:
    text = sql.lstrip()
    if not text:
        return ""
    end = 0
    while end < len(text) and (text[end].isalpha() or text[end] == "_"):
        end += 1
    return text[:end].upper()


def _dml_event(sql: str) -> Optional[str]:
    keyword = _first_keyword(sql)
    if keyword in ("INSERT", "REPLACE"):
        return LogEvent.DML_INSERT
    if keyword == "UPDATE":
        return LogEvent.DML_UPDATE
    if keyword == "DELETE":
        return LogEvent.DML_DELETE
    return None


def _ddl_event(sql: str) -> Optional[str]:
    keyword = _first_keyword(sql)
    if keyword == "CREATE":
        return LogEvent.DDL_CREATE
    if keyword == "ALTER":
        return LogEvent.DDL_ALTER
    if keyword in ("DROP", "TRUNCATE"):
        return LogEvent.DDL_DROP
    return None


def resolve_event(
    stmt_type: StatementType,
    context: Optional[LogContext],
    sql: str,
) -> Optional[str]:
    """Resolve the structured event name for one executed statement."""
    category = _category(stmt_type)
    operation = (context.operation if context else None) or ""
    operation = operation.lower()
    source = (context.source if context else None) or ""
    source = source.lower()

    if category == "DQL":
        if source == "set_operation" or operation in (
            "union",
            "intersect",
            "except",
        ):
            return LogEvent.DQL_SET_OPERATION
        if source in ("cte", "cte_query"):
            return LogEvent.DQL_CTE
        if source == "aggregate" or operation in (
            "aggregate",
            "count",
            "sum",
            "avg",
            "min",
            "max",
        ):
            return LogEvent.DQL_AGGREGATE
        return LogEvent.DQL_SELECT

    if category == "DML":
        if "soft" in operation:
            return LogEvent.DML_SOFT_DELETE
        if operation in (
            "batch",
            "insert_many",
            "update_many",
            "bulk_insert",
            "bulk_update",
        ):
            return LogEvent.DML_BATCH
        if operation == "insert":
            return LogEvent.DML_INSERT
        if operation == "update":
            return LogEvent.DML_UPDATE
        if operation == "delete":
            return LogEvent.DML_DELETE
        return _dml_event(sql)

    if category == "DDL":
        return _ddl_event(sql)

    return None


def event_fields(
    stmt_type: StatementType,
    context: Optional[LogContext],
    *,
    param_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Build the structured fields shared by DEBUG and INFO records."""
    fields: Dict[str, Any] = {"statement_type": _category(stmt_type)}

    model = _model_name(context)
    if model:
        fields["model"] = model
    model_fqn = _model_fqn(context)
    if model_fqn:
        fields["model_fqn"] = model_fqn

    if context is not None:
        if context.operation:
            fields["operation"] = context.operation
        if context.object_name:
            fields["object_name"] = context.object_name
        if context.object_type:
            fields["object_type"] = context.object_type
        if context.schema:
            fields["schema"] = context.schema
        if context.database:
            fields["database"] = context.database

    if param_count is not None:
        fields["param_count"] = param_count

    return fields


def _redact_params(backend: Any, params: Any, context: Optional[LogContext]) -> Any:
    if params is None:
        return None
    config = backend._get_logging_config()
    logger_name = backend._get_logger_name()
    payload = LogPayload(
        params,
        LogDataKind.QUERY_PARAMS,
        param_meta=context.param_meta if context is not None else None,
    )
    return config.redact(payload, logger_name)


def log_execution_start(
    backend: Any,
    sql: str,
    params: Any,
    options: Optional[ExecutionOptions],
) -> None:
    """Log one DEBUG record with SQL text and redacted parameters."""
    if not backend.logger.isEnabledFor(logging.DEBUG):
        return

    context = options.log_context if options is not None else None
    try:
        param_count = len(params) if params is not None else None
    except TypeError:
        param_count = None
    redacted = _redact_params(backend, params, context)
    fields = event_fields(
        options.stmt_type if options is not None else StatementType.OTHER,
        context,
        param_count=param_count,
    )
    backend.log(
        logging.DEBUG,
        f"Executing SQL: {sql}, parameters: {redacted}",
        extra={"activerecord": fields},
    )


def log_batch_start(
    backend: Any,
    sql: str,
    params_list: List[Any],
    options: Optional[ExecutionOptions],
) -> None:
    """Log one DEBUG record for a batch without expanding all parameter sets."""
    if not backend.logger.isEnabledFor(logging.DEBUG):
        return

    context = options.log_context if options is not None else None
    fields = event_fields(
        options.stmt_type if options is not None else StatementType.DML,
        context,
        param_count=len(params_list),
    )
    fields["parameter_sets"] = len(params_list)
    backend.log(
        logging.DEBUG,
        f"Executing SQL: {sql}, parameter_sets: {len(params_list)}",
        extra={"activerecord": fields},
    )


def log_execution_summary(
    backend: Any,
    stmt_type: StatementType,
    sql: str,
    cursor: Any,
    data: Optional[List[Dict]],
    duration: float,
    options: Optional[ExecutionOptions],
) -> None:
    """Log one INFO summary for a completed DML, DQL or DDL execution."""
    context = options.log_context if options is not None else None
    event = resolve_event(stmt_type, context, sql)
    if event is None:
        return

    category = _category(stmt_type)
    fields = event_fields(stmt_type, context)
    fields["duration_ms"] = round(duration * 1000, 2)

    if category == "DML":
        fields["rows_affected"] = getattr(cursor, "rowcount", 0)
    elif category == "DQL":
        fields["rows_returned"] = len(data) if data is not None else 0

    log_event(backend.logger, event, level=logging.INFO, **fields)


def log_batch_summary(
    backend: Any,
    sql: str,
    params_list: List[Any],
    affected_rows: int,
    duration: float,
    options: Optional[ExecutionOptions],
) -> None:
    """Log one INFO summary for an ``execute_many`` batch."""
    context = options.log_context if options is not None else None
    fields = event_fields(
        options.stmt_type if options is not None else StatementType.DML,
        context,
    )
    fields["operation"] = context.operation if context and context.operation else "batch"
    fields["parameter_sets"] = len(params_list)
    fields["rows_affected"] = affected_rows
    fields["duration_ms"] = round(duration * 1000, 2)
    log_event(backend.logger, LogEvent.DML_BATCH, level=logging.INFO, **fields)


def log_execution_error(
    backend: Any,
    error: Exception,
    options: Optional[ExecutionOptions],
) -> None:
    """Log a DEBUG note before a failure is re-raised.

    The application sees the exception and normally records it; logging at
    ``ERROR`` here would duplicate that record for every database error.
    """
    if not backend.logger.isEnabledFor(logging.DEBUG):
        return
    context = options.log_context if options is not None else None
    fields = event_fields(
        options.stmt_type if options is not None else StatementType.OTHER,
        context,
    )
    fields["error_type"] = type(error).__name__
    fields["error_message"] = str(error)[:200]
    backend.log(logging.DEBUG, "Query failed, exception will be re-raised", extra={"activerecord": fields})
