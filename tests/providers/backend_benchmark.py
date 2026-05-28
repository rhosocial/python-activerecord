"""SQLite provider for backend direct benchmark tests."""

import os
import tempfile
import uuid

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.testsuite.benchmark.backend.interfaces import (
    BackendBenchmarkContext,
)
from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.data import (
    make_user_payloads,
    payload_count_for_size,
)

from .scenarios import get_enabled_scenarios, get_scenario


class BackendBenchmarkProvider:
    def __init__(self):
        self._scenario_db_files = {}
        self._active_backends = []
        self._active_async_backends = []

    def get_benchmark_scenarios(self):
        return list(get_enabled_scenarios().keys())

    def setup_benchmark_sync(self, scenario: str, size: str):
        from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

        _, original_config = get_scenario(scenario)
        config = self._make_config(scenario, original_config)
        backend = SQLiteBackend(connection_config=config)
        self._initialize_schema(backend)
        payloads = make_user_payloads(payload_count_for_size(size))
        record_ids = self._seed_sync(backend, payloads)
        self._active_backends.append(backend)
        return BackendBenchmarkContext(
            scenario=scenario,
            size=size,
            backend=backend,
            payloads=payloads,
            record_ids=record_ids,
            sql=self._sql_templates(),
            params_factory=self._params_factory,
            backend_namespace="rhosocial.activerecord.backend.impl.sqlite",
            backend_name="sqlite",
        )

    def teardown_benchmark_sync(self, scenario: str, context: BackendBenchmarkContext) -> None:
        self._cleanup_sync(scenario)

    async def setup_benchmark_async(self, scenario: str, size: str):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

        _, original_config = get_scenario(scenario)
        config = self._make_config(scenario, original_config)
        backend = AsyncSQLiteBackend(connection_config=config)
        await self._initialize_schema_async(backend)
        payloads = make_user_payloads(payload_count_for_size(size))
        record_ids = await self._seed_async(backend, payloads)
        self._active_async_backends.append(backend)
        return BackendBenchmarkContext(
            scenario=scenario,
            size=size,
            backend=backend,
            payloads=payloads,
            record_ids=record_ids,
            sql=self._sql_templates(),
            params_factory=self._params_factory,
            backend_namespace="rhosocial.activerecord.backend.impl.sqlite",
            backend_name="sqlite",
        )

    async def teardown_benchmark_async(self, scenario: str, context: BackendBenchmarkContext) -> None:
        await self._cleanup_async(scenario)

    def _make_config(self, scenario, original_config):
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

        unique_filename = os.path.join(
            tempfile.gettempdir(),
            f"benchmark_backend_{scenario}_{uuid.uuid4().hex}.sqlite",
        )
        self._scenario_db_files[scenario] = unique_filename
        return SQLiteConnectionConfig(
            database=unique_filename,
            delete_on_close=original_config.delete_on_close,
            pragmas=original_config.pragmas,
        )

    def _initialize_schema(self, backend):
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        backend.execute("DROP TABLE IF EXISTS benchmark_users", options=options)
        backend.execute(self._schema_sql(), options=options)

    async def _initialize_schema_async(self, backend):
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("DROP TABLE IF EXISTS benchmark_users", options=options)
        await backend.execute(self._schema_sql(), options=options)

    def _seed_sync(self, backend, payloads):
        record_ids = []
        options = ExecutionOptions(stmt_type=StatementType.DML, process_result_set=False)
        for payload in payloads:
            result = backend.execute(
                self._sql_templates()["insert"],
                self._params_factory("insert", payload),
                options=options,
            )
            if result.affected_rows != 1 or result.last_insert_id is None:
                raise AssertionError("failed to seed sync backend benchmark row")
            record_ids.append(result.last_insert_id)
        return record_ids

    async def _seed_async(self, backend, payloads):
        record_ids = []
        options = ExecutionOptions(stmt_type=StatementType.DML, process_result_set=False)
        for payload in payloads:
            result = await backend.execute(
                self._sql_templates()["insert"],
                self._params_factory("insert", payload),
                options=options,
            )
            if result.affected_rows != 1 or result.last_insert_id is None:
                raise AssertionError("failed to seed async backend benchmark row")
            record_ids.append(result.last_insert_id)
        return record_ids

    def _sql_templates(self):
        return {
            "insert": """
INSERT INTO benchmark_users (
    username, email, age, balance, notes, is_active, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
""",
            "find_one": "SELECT * FROM benchmark_users WHERE id = ?",
            "update": "UPDATE benchmark_users SET username = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            "delete": "DELETE FROM benchmark_users WHERE id = ?",
        }

    def _params_factory(self, operation, payload):
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

    def _schema_sql(self):
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

    def _cleanup_sync(self, scenario):
        for backend in self._active_backends:
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()
        self._remove_db_file(scenario)

    async def _cleanup_async(self, scenario):
        for backend in self._active_async_backends:
            try:
                await backend.disconnect()
            except Exception:
                pass
        self._active_async_backends.clear()
        self._remove_db_file(scenario)

    def _remove_db_file(self, scenario):
        db_file = self._scenario_db_files.pop(scenario, None)
        if db_file and os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass
