"""SQLite provider for CRUD benchmark tests."""

import os
import sys
import tempfile
import uuid
from typing import Type

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.data import (
    make_user_payloads,
    payload_count_for_size,
)
from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.models import (
    AsyncBenchmarkUser as AsyncBenchmarkUserBase,
    BenchmarkUser as BenchmarkUserBase,
)
from rhosocial.activerecord.testsuite.benchmark.crud.interfaces import CrudBenchmarkContext
from rhosocial.activerecord.testsuite.utils import select_fixture

from .scenarios import get_enabled_scenarios, get_scenario

BenchmarkUser310 = AsyncBenchmarkUser310 = None
BenchmarkUser311 = AsyncBenchmarkUser311 = None
BenchmarkUser312 = AsyncBenchmarkUser312 = None

if sys.version_info >= (3, 10):
    from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.models_py310 import (
        AsyncBenchmarkUser as AsyncBenchmarkUser310,
        BenchmarkUser as BenchmarkUser310,
    )

if sys.version_info >= (3, 11):
    from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.models_py311 import (
        AsyncBenchmarkUser as AsyncBenchmarkUser311,
        BenchmarkUser as BenchmarkUser311,
    )

if sys.version_info >= (3, 12):
    from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.models_py312 import (
        AsyncBenchmarkUser as AsyncBenchmarkUser312,
        BenchmarkUser as BenchmarkUser312,
    )


BenchmarkUser = select_fixture(
    *[candidate for candidate in (BenchmarkUser312, BenchmarkUser311, BenchmarkUser310, BenchmarkUserBase) if candidate]
)
AsyncBenchmarkUser = select_fixture(
    *[
        candidate
        for candidate in (
            AsyncBenchmarkUser312,
            AsyncBenchmarkUser311,
            AsyncBenchmarkUser310,
            AsyncBenchmarkUserBase,
        )
        if candidate
    ]
)


class CrudBenchmarkProvider:
    def __init__(self):
        self._scenario_db_files = {}
        self._active_backends = []
        self._active_async_backends = []

    def get_benchmark_scenarios(self):
        return list(get_enabled_scenarios().keys())

    def setup_benchmark_sync(self, scenario: str, size: str):
        model_class = self._setup_model(BenchmarkUser, scenario)
        payloads = make_user_payloads(payload_count_for_size(size))
        record_ids = []
        for payload in payloads:
            instance = model_class(**payload)
            rows = instance.save()
            if rows != 1 or instance.id is None:
                raise AssertionError("failed to seed sync CRUD benchmark row")
            record_ids.append(instance.id)
        return CrudBenchmarkContext(
            scenario=scenario,
            size=size,
            model_class=model_class,
            payloads=payloads,
            record_ids=record_ids,
            backend_namespace="rhosocial.activerecord.backend.impl.sqlite",
            backend_name="sqlite",
        )

    def teardown_benchmark_sync(self, scenario: str, context: CrudBenchmarkContext) -> None:
        self._cleanup_sync(scenario)

    async def setup_benchmark_async(self, scenario: str, size: str):
        model_class = await self._setup_async_model(AsyncBenchmarkUser, scenario)
        payloads = make_user_payloads(payload_count_for_size(size))
        record_ids = []
        for payload in payloads:
            instance = model_class(**payload)
            rows = await instance.save()
            if rows != 1 or instance.id is None:
                raise AssertionError("failed to seed async CRUD benchmark row")
            record_ids.append(instance.id)
        return CrudBenchmarkContext(
            scenario=scenario,
            size=size,
            model_class=model_class,
            payloads=payloads,
            record_ids=record_ids,
            backend_namespace="rhosocial.activerecord.backend.impl.sqlite",
            backend_name="sqlite",
        )

    async def teardown_benchmark_async(self, scenario: str, context: CrudBenchmarkContext) -> None:
        await self._cleanup_async(scenario)

    def _setup_model(self, model_class: Type[ActiveRecord], scenario: str) -> Type[ActiveRecord]:
        backend_class, original_config = get_scenario(scenario)
        config = self._make_config(scenario, original_config)
        model_class.configure(config, backend_class)
        self._initialize_schema(model_class)
        if model_class.__backend__ not in self._active_backends:
            self._active_backends.append(model_class.__backend__)
        return model_class

    async def _setup_async_model(self, model_class: Type[ActiveRecord], scenario: str) -> Type[ActiveRecord]:
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

        _, original_config = get_scenario(scenario)
        config = self._make_config(scenario, original_config)
        await model_class.configure(config, AsyncSQLiteBackend)
        await self._initialize_schema_async(model_class)
        if model_class.__backend__ not in self._active_async_backends:
            self._active_async_backends.append(model_class.__backend__)
        return model_class

    def _make_config(self, scenario, original_config):
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
        from providers.pooling import resolve_database_file, should_keep_database

        unique_filename = resolve_database_file(scenario, suffix=".bench.sqlite")
        self._scenario_db_files[scenario] = unique_filename
        return SQLiteConnectionConfig(
            database=unique_filename,
            delete_on_close=original_config.delete_on_close and not should_keep_database(scenario),
            pragmas=original_config.pragmas,
        )

    def _initialize_schema(self, model_class):
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        model_class.__backend__.execute("DROP TABLE IF EXISTS benchmark_users", options=options)
        model_class.__backend__.execute(self._schema_sql(), options=options)

    async def _initialize_schema_async(self, model_class):
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await model_class.__backend__.execute(
            "DROP TABLE IF EXISTS benchmark_users",
            options=options,
        )
        await model_class.__backend__.execute(self._schema_sql(), options=options)

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
