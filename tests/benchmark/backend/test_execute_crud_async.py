"""Asynchronous SQLite direct backend CRUD benchmarks."""

import pytest

from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.data import make_user_payload

from .workloads import (
    DQL_OPTIONS,
    execute_delete_one_async,
    execute_find_one_async,
    execute_insert_one_async,
    execute_update_one_async,
)


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_async
@pytest.mark.benchmark_write
def test_sqlite_backend_execute_insert_one_async(benchmark, sqlite_backend_async_context):
    context, run = sqlite_backend_async_context
    counter = {"value": 0}

    async def insert_row():
        counter["value"] += 1
        payload = make_user_payload(len(context.payloads) + counter["value"])
        return await execute_insert_one_async(context, payload)

    inserted_id = benchmark(lambda: run(insert_row()))
    row = run(execute_find_one_async(context, inserted_id))
    assert row["username"] == f"bench_user_{len(context.payloads) + counter['value']}"


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_async
@pytest.mark.benchmark_read
def test_sqlite_backend_execute_find_one_async(benchmark, sqlite_backend_async_context):
    context, run = sqlite_backend_async_context
    record_id = context.record_ids[len(context.record_ids) // 2]
    row = benchmark(lambda: run(execute_find_one_async(context, record_id)))
    assert row["id"] == record_id


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_async
@pytest.mark.benchmark_write
def test_sqlite_backend_execute_update_one_async(benchmark, sqlite_backend_async_context):
    context, run = sqlite_backend_async_context
    counter = {"value": 0}

    async def update_row():
        counter["value"] += 1
        payload = make_user_payload(len(context.payloads) + counter["value"])
        record_id = await execute_insert_one_async(context, payload)
        username = f"backend_updated_{counter['value']}"
        await execute_update_one_async(context, record_id, username)
        return record_id, username

    record_id, username = benchmark(lambda: run(update_row()))
    row = run(execute_find_one_async(context, record_id))
    assert row["username"] == username


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_async
@pytest.mark.benchmark_write
def test_sqlite_backend_execute_delete_one_async(benchmark, sqlite_backend_async_context):
    context, run = sqlite_backend_async_context
    counter = {"value": 0}

    async def delete_row():
        counter["value"] += 1
        payload = make_user_payload(len(context.payloads) + counter["value"])
        record_id = await execute_insert_one_async(context, payload)
        await execute_delete_one_async(context, record_id)
        return record_id

    record_id = benchmark(lambda: run(delete_row()))
    result = run(
        context.backend.execute(
            context.sql["find_one"],
            (record_id,),
            options=DQL_OPTIONS,
        )
    )
    assert not result.data
