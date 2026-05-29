"""SQLite provider for FastAPI benchmark tests."""

import os
import sys
import tempfile
import uuid
from contextlib import asynccontextmanager
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
)
from rhosocial.activerecord.testsuite.benchmark.fastapi.interfaces import (
    FASTAPI_CONNECTION_STRATEGIES,
    FASTAPI_CONTEXT_STRATEGY,
    FASTAPI_RUNTIME_CONFIGS,
    FastAPIBenchmarkContext,
)
from rhosocial.activerecord.testsuite.utils import select_fixture

from .scenarios import get_enabled_scenarios, get_scenario

AsyncBenchmarkUser310 = None
AsyncBenchmarkUser311 = None
AsyncBenchmarkUser312 = None

if sys.version_info >= (3, 10):
    from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.models_py310 import (
        AsyncBenchmarkUser as AsyncBenchmarkUser310,
    )

if sys.version_info >= (3, 11):
    from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.models_py311 import (
        AsyncBenchmarkUser as AsyncBenchmarkUser311,
    )

if sys.version_info >= (3, 12):
    from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.models_py312 import (
        AsyncBenchmarkUser as AsyncBenchmarkUser312,
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


class FastAPIBenchmarkProvider:
    def __init__(self):
        self._scenario_db_files = {}
        self._active_async_backends = []
        self._active_async_pools = []
        self._active_clients = []

    def get_benchmark_scenarios(self):
        return list(get_enabled_scenarios().keys())

    def get_connection_strategies(self):
        return FASTAPI_CONNECTION_STRATEGIES

    async def setup_benchmark_async(
        self,
        scenario: str,
        size: str,
        connection_strategy: str = "context",
    ):
        import httpx
        from rhosocial.activerecord.testsuite.benchmark.fastapi.app import (
            create_fastapi_benchmark_app,
        )

        model_class, config = await self._setup_async_model(AsyncBenchmarkUser, scenario)
        payloads = make_user_payloads(payload_count_for_size(size))
        record_ids = []
        async with model_class.__backend__.context():
            for payload in payloads:
                instance = model_class(**payload)
                rows = await instance.save()
                if rows != 1 or instance.id is None:
                    raise AssertionError("failed to seed async FastAPI benchmark row")
                record_ids.append(instance.id)

        runtime_config = self._fastapi_runtime_config(connection_strategy)
        pool = None
        pool_config = None
        backend_context_factory = self._create_async_context_factory(config)
        if connection_strategy != FASTAPI_CONTEXT_STRATEGY:
            pool, pool_config = await self._create_async_pool(config, runtime_config)
            backend_context_factory = pool.connection

        app = create_fastapi_benchmark_app(
            model_class=model_class,
            backend_context_factory=backend_context_factory,
            backend_name="sqlite",
            scenario=scenario,
        )
        transport = httpx.ASGITransport(app=app)
        client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        self._active_clients.append(client)

        return FastAPIBenchmarkContext(
            scenario=scenario,
            size=size,
            app=app,
            client=client,
            model_class=model_class,
            payloads=payloads,
            record_ids=record_ids,
            backend_namespace="rhosocial.activerecord.backend.impl.sqlite",
            backend_name="sqlite",
            connection_strategy=connection_strategy,
            concurrency=runtime_config["concurrency"],
            repeat=runtime_config["repeat"],
            pool_config={
                "min_size": pool_config.min_size,
                "max_size": pool_config.max_size,
                "connection_mode": pool_config.connection_mode,
            }
            if pool_config
            else None,
            pool_connection_mode=pool.connection_mode if pool else None,
            pool_stats=pool.get_stats if pool else None,
        )

    async def teardown_benchmark_async(
        self,
        scenario: str,
        context: FastAPIBenchmarkContext,
    ) -> None:
        await self._cleanup_async(scenario)

    async def _setup_async_model(
        self, model_class: Type[ActiveRecord], scenario: str
    ) -> Type[ActiveRecord]:
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

        _, original_config = get_scenario(scenario)
        config = self._make_config(scenario, original_config)
        await model_class.configure(config, AsyncSQLiteBackend)
        await self._initialize_schema_async(model_class)
        if model_class.__backend__ not in self._active_async_backends:
            self._active_async_backends.append(model_class.__backend__)
        return model_class, config

    def _make_config(self, scenario, original_config):
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

        unique_filename = os.path.join(
            tempfile.gettempdir(),
            f"benchmark_fastapi_activerecord_{scenario}_{uuid.uuid4().hex}.sqlite",
        )
        self._scenario_db_files[scenario] = unique_filename
        return SQLiteConnectionConfig(
            database=unique_filename,
            delete_on_close=False,
            pragmas=original_config.pragmas,
        )

    async def _initialize_schema_async(self, model_class):
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await model_class.__backend__.execute(
            "DROP TABLE IF EXISTS benchmark_users",
            options=options,
        )
        await model_class.__backend__.execute(self._schema_sql(), options=options)

    def _create_async_context_factory(self, config):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

        @asynccontextmanager
        async def context_factory():
            backend = AsyncSQLiteBackend(connection_config=config)
            async with backend.context():
                yield backend

        return context_factory

    def _fastapi_runtime_config(self, connection_strategy):
        try:
            return FASTAPI_RUNTIME_CONFIGS[connection_strategy]
        except KeyError as exc:
            raise ValueError(
                f"unsupported FastAPI benchmark connection strategy: {connection_strategy}"
            ) from exc

    async def _create_async_pool(self, config, runtime_config):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        from rhosocial.activerecord.connection.pool import AsyncBackendPool, PoolConfig

        pool_config = PoolConfig(
            min_size=runtime_config["pool_min_size"],
            max_size=runtime_config["pool_max_size"],
            connection_mode="auto",
            backend_factory=lambda: AsyncSQLiteBackend(connection_config=config),
        )
        pool = await AsyncBackendPool.create(pool_config)
        self._active_async_pools.append(pool)
        return pool, pool_config

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

    async def _cleanup_async(self, scenario):
        for client in self._active_clients:
            try:
                await client.aclose()
            except Exception:
                pass
        self._active_clients.clear()

        for pool in self._active_async_pools:
            try:
                await pool.close(force=True)
            except Exception:
                pass
        self._active_async_pools.clear()

        for backend in self._active_async_backends:
            try:
                options = ExecutionOptions(stmt_type=StatementType.DDL)
                await backend.execute("DROP TABLE IF EXISTS benchmark_users", options=options)
            except Exception:
                pass
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
