"""Asynchronous SQLite direct backend batch benchmarks."""

import pytest

from rhosocial.activerecord.testsuite.benchmark.crud.fixtures.data import make_user_payload

from .workloads import execute_many_insert_async


@pytest.mark.benchmark
@pytest.mark.benchmark_backend
@pytest.mark.benchmark_async
@pytest.mark.benchmark_write
def test_sqlite_backend_execute_many_insert_async(benchmark, sqlite_backend_async_context):
    context, run = sqlite_backend_async_context
    start = len(context.payloads) + 1
    payloads = [make_user_payload(start + index) for index in range(100)]
    affected_rows = benchmark(lambda: run(execute_many_insert_async(context, payloads)))
    assert affected_rows == len(payloads)
