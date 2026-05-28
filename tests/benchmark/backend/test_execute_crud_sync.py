"""Synchronous SQLite direct backend CRUD benchmarks."""

import pytest

from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.data import make_user_payload

from .workloads import (
    DQL_OPTIONS,
    execute_delete_one,
    execute_find_one,
    execute_insert_one,
    execute_update_one,
)


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_sync
@pytest.mark.benchmark_write
def test_sqlite_backend_execute_insert_one_sync(benchmark, sqlite_backend_sync_context):
    counter = {"value": 0}

    def insert_row():
        counter["value"] += 1
        payload = make_user_payload(len(sqlite_backend_sync_context.payloads) + counter["value"])
        return execute_insert_one(sqlite_backend_sync_context, payload)

    inserted_id = benchmark(insert_row)
    row = execute_find_one(sqlite_backend_sync_context, inserted_id)
    assert row["username"] == f"bench_user_{len(sqlite_backend_sync_context.payloads) + counter['value']}"


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_sync
@pytest.mark.benchmark_read
def test_sqlite_backend_execute_find_one_sync(benchmark, sqlite_backend_sync_context):
    record_id = sqlite_backend_sync_context.record_ids[len(sqlite_backend_sync_context.record_ids) // 2]
    row = benchmark(execute_find_one, sqlite_backend_sync_context, record_id)
    assert row["id"] == record_id


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_sync
@pytest.mark.benchmark_write
def test_sqlite_backend_execute_update_one_sync(benchmark, sqlite_backend_sync_context):
    counter = {"value": 0}

    def update_row():
        counter["value"] += 1
        payload = make_user_payload(len(sqlite_backend_sync_context.payloads) + counter["value"])
        record_id = execute_insert_one(sqlite_backend_sync_context, payload)
        username = f"backend_updated_{counter['value']}"
        execute_update_one(sqlite_backend_sync_context, record_id, username)
        return record_id, username

    record_id, username = benchmark(update_row)
    row = execute_find_one(sqlite_backend_sync_context, record_id)
    assert row["username"] == username


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_sync
@pytest.mark.benchmark_write
def test_sqlite_backend_execute_delete_one_sync(benchmark, sqlite_backend_sync_context):
    counter = {"value": 0}

    def delete_row():
        counter["value"] += 1
        payload = make_user_payload(len(sqlite_backend_sync_context.payloads) + counter["value"])
        record_id = execute_insert_one(sqlite_backend_sync_context, payload)
        execute_delete_one(sqlite_backend_sync_context, record_id)
        return record_id

    record_id = benchmark(delete_row)
    result = sqlite_backend_sync_context.backend.execute(
        sqlite_backend_sync_context.sql["find_one"],
        (record_id,),
        options=DQL_OPTIONS,
    )
    assert not result.data
