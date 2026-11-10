# tests/rhosocial/activerecord_test/logging_module/test_execution_logging.py
"""Backend execution logging: one DEBUG SQL point and one INFO summary.

The tests pin the contract from the logging chapter:

* SQL text is logged once, at DEBUG, by the backend;
* INFO carries a DML/DQL/DDL summary without SQL or parameter values;
* the query layer no longer logs SQL or parameters;
* positional parameters stay opaque unless metadata says they are safe;
* ``SensitiveValue`` is unwrapped before the database receives the value;
* a failure that will be re-raised is not logged at ERROR by the library.
"""

import logging
from typing import Optional

import pytest

from rhosocial.activerecord.backend.errors import QueryError
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions, LogContext
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.logging import LogEvent, SensitiveValue
from rhosocial.activerecord.model import ActiveRecord


CREATE_TABLE = (
    'CREATE TABLE "log_users" ('
    '"id" INTEGER PRIMARY KEY AUTOINCREMENT, '
    '"name" TEXT NOT NULL, '
    '"secret" TEXT'
    ')'
)


def _records(caplog, event=None):
    if event is None:
        return list(caplog.records)
    return [record for record in caplog.records if getattr(record, "event", None) == event]


def _sql_debug_records(caplog):
    return [
        record
        for record in caplog.records
        if record.levelno == logging.DEBUG
        and record.getMessage().startswith("Executing SQL")
    ]


@pytest.fixture
def log_model(tmp_path):
    """Configure an isolated SQLite model with a fresh table."""

    class LogUser(ActiveRecord):
        __table_name__ = "log_users"
        id: Optional[int] = None
        name: str = ""
        secret: str = ""

    LogUser.configure(
        SQLiteConnectionConfig(database=str(tmp_path / "execution.db")),
        SQLiteBackend,
    )
    backend = LogUser.backend()
    backend.connect()
    backend.execute(
        CREATE_TABLE,
        options=ExecutionOptions(
            stmt_type=StatementType.DDL,
            log_context=LogContext(operation="create", object_name="log_users"),
        ),
    )
    yield LogUser, backend
    backend.disconnect()


def test_debug_logs_sql_once_and_hides_positional_values(log_model, caplog):
    LogUser, _backend = log_model
    user = LogUser(name="alice", secret="top-secret")

    with caplog.at_level(logging.DEBUG):
        user.save()

    sql_records = _sql_debug_records(caplog)
    assert len(sql_records) == 1
    message = sql_records[0].getMessage()
    assert "INSERT INTO" in message
    assert "top-secret" not in message
    assert "alice" not in message
    assert "<2 params: str, str>" in message

    fields = sql_records[0].activerecord
    assert fields["statement_type"] == "DML"
    assert fields["model"] == "LogUser"
    assert fields["operation"] == "insert"
    assert fields["object_name"] == "log_users"


def test_info_insert_summary_has_no_sql_or_values(log_model, caplog):
    LogUser, _backend = log_model
    user = LogUser(name="alice", secret="top-secret")

    with caplog.at_level(logging.INFO):
        user.save()

    inserts = _records(caplog, LogEvent.DML_INSERT)
    assert len(inserts) == 1
    record = inserts[0]
    assert "INSERT" not in record.getMessage()
    assert "alice" not in record.getMessage()
    assert "top-secret" not in record.getMessage()
    assert record.activerecord["rows_affected"] == 1
    assert record.activerecord["object_name"] == "log_users"
    assert "duration_ms" in record.activerecord


def test_info_select_summary_reports_rows(log_model, caplog):
    LogUser, _backend = log_model
    LogUser(name="alice", secret="a").save()
    LogUser(name="bob", secret="b").save()

    with caplog.at_level(logging.INFO):
        records = LogUser.query().all()

    assert len(records) == 2
    selects = _records(caplog, LogEvent.DQL_SELECT)
    assert len(selects) == 1
    assert selects[0].activerecord["rows_returned"] == 2
    assert selects[0].activerecord["model"] == "LogUser"


def test_query_layer_no_longer_logs_sql(log_model, caplog):
    LogUser, _backend = log_model
    LogUser(name="alice", secret="a").save()

    with caplog.at_level(logging.DEBUG):
        LogUser.query().all()

    messages = [record.getMessage() for record in caplog.records]
    assert not any("Executing query:" in message for message in messages)
    assert not any("Executing async query:" in message for message in messages)


def test_sensitive_value_is_unwrapped_before_execution(log_model, caplog):
    LogUser, backend = log_model

    with caplog.at_level(logging.DEBUG):
        backend.execute(
            'INSERT INTO "log_users" ("name", "secret") VALUES (?, ?)',
            (SensitiveValue("bob"), SensitiveValue("top-secret")),
            options=ExecutionOptions(
                stmt_type=StatementType.DML,
                log_context=LogContext(
                    model=LogUser,
                    operation="insert",
                    object_name="log_users",
                ),
            ),
        )

    sql_records = _sql_debug_records(caplog)
    assert len(sql_records) == 1
    assert "top-secret" not in sql_records[0].getMessage()

    rows = backend.fetch_all(
        'SELECT "name", "secret" FROM "log_users"',
        log_context=LogContext(model=LogUser, operation="select", object_name="log_users"),
    )
    assert rows == [{"name": "bob", "secret": "top-secret"}]


def test_high_level_insert_fills_table_context(log_model, caplog):
    LogUser, backend = log_model
    from rhosocial.activerecord.backend.options import InsertOptions

    with caplog.at_level(logging.INFO):
        backend.insert(
            InsertOptions(
                table="log_users",
                data={"name": "carol", "secret": "c"},
            )
        )

    inserts = _records(caplog, LogEvent.DML_INSERT)
    assert len(inserts) == 1
    assert inserts[0].activerecord["object_name"] == "log_users"
    assert inserts[0].activerecord["operation"] == "insert"


def test_batch_execution_summary_counts_parameter_sets(log_model, caplog):
    LogUser, backend = log_model

    with caplog.at_level(logging.INFO):
        backend.execute_many(
            'INSERT INTO "log_users" ("name", "secret") VALUES (?, ?)',
            [("alice", "a"), ("bob", "b")],
            options=ExecutionOptions(
                stmt_type=StatementType.DML,
                log_context=LogContext(
                    model=LogUser,
                    operation="insert_many",
                    object_name="log_users",
                ),
            ),
        )

    batches = _records(caplog, LogEvent.DML_BATCH)
    assert len(batches) == 1
    assert batches[0].activerecord["parameter_sets"] == 2
    assert batches[0].activerecord["rows_affected"] == 2


def test_transaction_events_are_structured(log_model, caplog):
    LogUser, backend = log_model

    with caplog.at_level(logging.INFO):
        with backend.transaction():
            pass

    events = {record.event for record in caplog.records if getattr(record, "event", None)}
    assert LogEvent.TRANSACTION_BEGIN in events
    assert LogEvent.TRANSACTION_COMMIT in events


def test_failure_is_not_logged_at_error_before_reraise(log_model, caplog):
    LogUser, backend = log_model

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(QueryError):
            backend.fetch_all(
                'SELECT * FROM "missing_table"',
                log_context=LogContext(model=LogUser, operation="select"),
            )

    errors = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert errors == []
    assert any(
        "exception will be re-raised" in record.getMessage()
        for record in caplog.records
    )


def test_param_meta_masks_declared_sensitive_positions(caplog):
    from rhosocial.activerecord.logging import (
        LogDataKind,
        LogPayload,
        ParamMeta,
        SummarizerConfig,
        LoggingConfig,
    )

    config = LoggingConfig(
        summarizer_config=SummarizerConfig(sensitive_fields={"password"})
    )
    payload = LogPayload(
        ("alice", "top-secret"),
        LogDataKind.QUERY_PARAMS,
        param_meta=(
            ParamMeta(index=0, field="name"),
            ParamMeta(index=1, field="password", sensitive=True),
        ),
    )

    redacted = config.redact(payload, "test")

    assert "alice" in str(redacted)
    assert "top-secret" not in str(redacted)
    assert "***MASKED***" in str(redacted)


@pytest.mark.asyncio
async def test_async_execution_logs_same_events(tmp_path, caplog):
    from rhosocial.activerecord.backend.impl.sqlite.backend import (
        AsyncSQLiteBackend,
    )

    backend = AsyncSQLiteBackend(
        SQLiteConnectionConfig(database=str(tmp_path / "async_execution.db"))
    )
    await backend.connect()
    try:
        await backend.execute(
            CREATE_TABLE,
            options=ExecutionOptions(
                stmt_type=StatementType.DDL,
                log_context=LogContext(operation="create", object_name="log_users"),
            ),
        )
        with caplog.at_level(logging.INFO):
            await backend.execute(
                'INSERT INTO "log_users" ("name", "secret") VALUES (?, ?)',
                ("alice", "top-secret"),
                options=ExecutionOptions(
                    stmt_type=StatementType.DML,
                    log_context=LogContext(
                        model=LogUserRef,
                        operation="insert",
                        object_name="log_users",
                    ),
                ),
            )
            await backend.fetch_all(
                'SELECT "name" FROM "log_users"',
                log_context=LogContext(
                    model=LogUserRef,
                    operation="select",
                    object_name="log_users",
                ),
            )
    finally:
        await backend.disconnect()

    inserts = _records(caplog, LogEvent.DML_INSERT)
    selects = _records(caplog, LogEvent.DQL_SELECT)
    assert len(inserts) == 1
    assert inserts[0].activerecord["rows_affected"] == 1
    assert len(selects) == 1
    assert selects[0].activerecord["rows_returned"] == 1
    assert "alice" not in inserts[0].getMessage()
    assert "top-secret" not in inserts[0].getMessage()


class LogUserRef:
    """Stand-in model used where only the class name matters."""

    __table_name__ = "log_users"


def test_sync_and_async_backend_share_logger_name():
    from rhosocial.activerecord.backend.impl.sqlite.backend import (
        AsyncSQLiteBackend,
        SQLiteBackend,
    )

    sync_backend = SQLiteBackend(database=":memory:")
    async_backend = AsyncSQLiteBackend(database=":memory:")

    assert sync_backend._get_logger_name() == "rhosocial.activerecord.backend.sqlite"
    assert async_backend._get_logger_name() == "rhosocial.activerecord.backend.sqlite"


def test_resolve_event_uses_sources():
    from rhosocial.activerecord.backend.base.execution_logging import (
        resolve_event,
    )

    cte = LogContext(model=LogUserRef, operation="cte", source="cte_query")
    set_op = LogContext(
        model=LogUserRef,
        operation="union_all",
        source="set_operation",
    )
    aggregate = LogContext(
        model=LogUserRef,
        operation="aggregate",
        source="aggregate",
    )

    assert resolve_event(StatementType.DQL, cte, "SELECT 1") == LogEvent.DQL_CTE
    assert (
        resolve_event(StatementType.DQL, set_op, "SELECT 1 UNION SELECT 2")
        == LogEvent.DQL_SET_OPERATION
    )
    assert (
        resolve_event(StatementType.DQL, aggregate, "SELECT COUNT(*) FROM t")
        == LogEvent.DQL_AGGREGATE
    )
    assert (
        resolve_event(StatementType.DQL, None, "SELECT 1")
        == LogEvent.DQL_SELECT
    )
