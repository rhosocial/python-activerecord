"""SQLite direct backend benchmark fixtures."""

import asyncio
import os
import tempfile
import uuid
from dataclasses import dataclass
from typing import Any, Callable, List

import pytest

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.data import (
    make_user_payloads,
    payload_count_for_size,
)

from providers.scenarios import get_enabled_scenarios, get_scenario


@dataclass
class BackendBenchmarkContext:
    scenario: str
    size: str
    backend: Any
    payloads: List[dict]
    record_ids: List[Any]
    sql: dict
    params_factory: Callable[..., Any]
    backend_namespace: str
    backend_name: str
    database_path: str


DQL_OPTIONS = ExecutionOptions(stmt_type=StatementType.DQL, process_result_set=True)
DML_OPTIONS = ExecutionOptions(stmt_type=StatementType.DML, process_result_set=False)
DDL_OPTIONS = ExecutionOptions(stmt_type=StatementType.DDL)

SCENARIO_PARAMS = list(get_enabled_scenarios().keys()) or [
    pytest.param(
        "default",
        marks=pytest.mark.skip(reason="No SQLite benchmark scenarios found"),
    )
]


def pytest_addoption(parser):
    try:
        parser.addoption(
            "--benchmark-size",
            action="store",
            default="small",
            choices=("small", "medium", "large"),
            help="Data size for SQLite backend benchmark scenarios.",
        )
    except ValueError:
        pass


@pytest.fixture(scope="function")
def benchmark_size(request):
    return request.config.getoption("--benchmark-size")


def pytest_configure(config):
    config.addinivalue_line("markers", "benchmark: Mark tests as performance benchmarks")
    config.addinivalue_line("markers", "benchmark_sync: Mark synchronous benchmark tests")
    config.addinivalue_line("markers", "benchmark_async: Mark asynchronous benchmark tests")
    config.addinivalue_line("markers", "benchmark_read: Mark read-oriented benchmark tests")
    config.addinivalue_line("markers", "benchmark_write: Mark write-oriented benchmark tests")
    config.addinivalue_line("markers", "benchmark_backend: Mark backend direct benchmark tests")


@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def sqlite_backend_sync_context(request, benchmark_size):
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

    scenario = request.param
    _, original_config = get_scenario(scenario)
    config, database_path = _make_config(scenario, original_config)
    backend = SQLiteBackend(connection_config=config)
    _initialize_schema(backend)
    payloads = make_user_payloads(payload_count_for_size(benchmark_size))
    record_ids = _seed_sync(backend, payloads)
    try:
        yield BackendBenchmarkContext(
            scenario=scenario,
            size=benchmark_size,
            backend=backend,
            payloads=payloads,
            record_ids=record_ids,
            sql=_sql_templates(),
            params_factory=_params_factory,
            backend_namespace="rhosocial.activerecord.backend.impl.sqlite",
            backend_name="sqlite",
            database_path=database_path,
        )
    finally:
        backend.disconnect()
        _remove_db_file(database_path)


@pytest.fixture(scope="function", params=SCENARIO_PARAMS)
def sqlite_backend_async_context(request, benchmark_size):
    from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

    scenario = request.param
    _, original_config = get_scenario(scenario)
    config, database_path = _make_config(scenario, original_config)
    loop = asyncio.new_event_loop()
    backend = AsyncSQLiteBackend(connection_config=config)
    try:
        loop.run_until_complete(_initialize_schema_async(backend))
        payloads = make_user_payloads(payload_count_for_size(benchmark_size))
        record_ids = loop.run_until_complete(_seed_async(backend, payloads))
        yield (
            BackendBenchmarkContext(
                scenario=scenario,
                size=benchmark_size,
                backend=backend,
                payloads=payloads,
                record_ids=record_ids,
                sql=_sql_templates(),
                params_factory=_params_factory,
                backend_namespace="rhosocial.activerecord.backend.impl.sqlite",
                backend_name="sqlite",
                database_path=database_path,
            ),
            loop.run_until_complete,
        )
    finally:
        loop.run_until_complete(backend.disconnect())
        loop.close()
        _remove_db_file(database_path)


def _make_config(scenario, original_config):
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

    database_path = os.path.join(
        tempfile.gettempdir(),
        f"benchmark_backend_{scenario}_{uuid.uuid4().hex}.sqlite",
    )
    return (
        SQLiteConnectionConfig(
            database=database_path,
            delete_on_close=original_config.delete_on_close,
            pragmas=original_config.pragmas,
        ),
        database_path,
    )


def _initialize_schema(backend):
    backend.execute("DROP TABLE IF EXISTS benchmark_users", options=DDL_OPTIONS)
    backend.execute(_schema_sql(), options=DDL_OPTIONS)


async def _initialize_schema_async(backend):
    await backend.execute("DROP TABLE IF EXISTS benchmark_users", options=DDL_OPTIONS)
    await backend.execute(_schema_sql(), options=DDL_OPTIONS)


def _seed_sync(backend, payloads):
    record_ids = []
    for payload in payloads:
        result = backend.execute(
            _sql_templates()["insert"],
            _params_factory("insert", payload),
            options=DML_OPTIONS,
        )
        if result.affected_rows != 1 or result.last_insert_id is None:
            raise AssertionError("failed to seed sync SQLite backend benchmark row")
        record_ids.append(result.last_insert_id)
    return record_ids


async def _seed_async(backend, payloads):
    record_ids = []
    for payload in payloads:
        result = await backend.execute(
            _sql_templates()["insert"],
            _params_factory("insert", payload),
            options=DML_OPTIONS,
        )
        if result.affected_rows != 1 or result.last_insert_id is None:
            raise AssertionError("failed to seed async SQLite backend benchmark row")
        record_ids.append(result.last_insert_id)
    return record_ids


def _sql_templates():
    return {
        "insert": """
INSERT INTO benchmark_users (
    username, email, age, balance, notes, is_active, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
""",
        "find_one": "SELECT * FROM benchmark_users WHERE id = ?",
        "update": (
            "UPDATE benchmark_users "
            "SET username = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?"
        ),
        "delete": "DELETE FROM benchmark_users WHERE id = ?",
    }


def _params_factory(operation, payload):
    if operation != "insert":
        raise ValueError(f"unsupported backend benchmark operation: {operation}")
    return (
        payload["username"],
        payload["email"],
        payload["age"],
        payload["balance"],
        payload["notes"],
        payload["is_active"],
    )


def _schema_sql():
    return """
CREATE TABLE benchmark_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER,
    balance REAL NOT NULL DEFAULT 0.0,
    notes TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
)
"""


def _remove_db_file(database_path):
    if database_path and os.path.exists(database_path):
        try:
            os.remove(database_path)
        except OSError:
            pass
