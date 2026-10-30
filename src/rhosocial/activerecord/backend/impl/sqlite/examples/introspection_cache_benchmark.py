# src/rhosocial/activerecord/backend/impl/sqlite/examples/introspection_cache_benchmark.py
"""What the introspection cache buys, measured on SQLite.

Run::

    python -m rhosocial.activerecord.backend.impl.sqlite.examples.introspection_cache_benchmark

Three passes over the same schema are timed, and the number of questions
each pass actually puts to the database is counted:

* **no cache** -- the manager holds a cache whose TTL is 0, so every
  question is answered by asking;
* **warm** -- the default cache, on a manager that has walked this schema
  before, so every question is answered from memory.

The counts matter as much as the timings: SQLite answers a metadata
question inside this process, so a question costs microseconds and a
whole schema walk costs milliseconds. A server backend answers the same
questions over a socket, where each one costs a round trip.

The last section makes that difference explicit. It walks the schema
again with an artificial delay injected into the executor -- a stand-in
for a backend whose metadata lives on the other end of a connection --
and reports what the cache is worth there.
"""

import time
from typing import Any, Dict, List, Tuple

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.introspection import InMemoryIntrospectionCache
from rhosocial.activerecord.backend.introspection.executor import SyncIntrospectorExecutor

TABLES = 40
COLUMNS = 8
INDEXES = 2


# --------------------------------------------------------------------- #
# The schema, and the questions asked about it
# --------------------------------------------------------------------- #


def build_schema(backend: SQLiteBackend) -> None:
    """Create a schema with enough shape that the timings mean something."""
    # The low-level cursor, not the public execute(): this is setup, and
    # routing it through the whole execution path would add logging and
    # hooks to a measurement that is about introspection, not about DDL.
    cursor = backend._get_cursor()
    try:
        for t in range(TABLES):
            columns = ", ".join(
                f"col_{c} {'INTEGER' if c == 0 else 'TEXT'}" for c in range(COLUMNS)
            )
            cursor.execute(f"CREATE TABLE table_{t} (id INTEGER PRIMARY KEY, {columns})")
            for i in range(INDEXES):
                cursor.execute(
                    f"CREATE INDEX idx_{t}_{i} ON table_{t} (col_{1 + i}, col_{3 + i})"
                )
        # The connection runs in autocommit, so each DDL commits itself.
    finally:
        cursor.close()


def fresh_backend(path: str = ":memory:") -> SQLiteBackend:
    """A connected backend with a schema in it, ready to be asked about."""
    backend = SQLiteBackend(database=path)
    backend.connect()
    build_schema(backend)
    # Adapt the dialect before asking it anything: the introspector builds
    # SQL through the dialect, and an unadapted dialect has no version to
    # gate its statements on.
    backend.introspect_and_adapt()
    return backend


def walk_schema(backend: SQLiteBackend, counting: Any) -> int:
    """Ask the introspector everything it knows about this schema."""
    introspector = backend.introspector
    answers = 0
    for table in introspector.list_tables():
        answers += len(introspector.list_columns(table.name))
        answers += len(introspector.list_indexes(table.name))
        answers += 1 if introspector.get_primary_key(table.name) else 0
    return answers


# --------------------------------------------------------------------- #
# Counting and delaying what the executor is asked to do
# --------------------------------------------------------------------- #


class CountingExecutor(SyncIntrospectorExecutor):
    """An executor that also reports how much it was asked to do."""

    def __init__(self, backend: Any) -> None:
        super().__init__(backend)
        self.calls = 0

    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        self.calls += 1
        return super().execute(sql, params)


class LatentExecutor(CountingExecutor):
    """A counting executor that also spends time the way a socket would."""

    def __init__(self, backend: Any, delay: float) -> None:
        super().__init__(backend)
        self._delay = delay

    def execute(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        self.calls += 1
        time.sleep(self._delay)
        return super().execute(sql, params)


def uncached(backend: SQLiteBackend) -> Any:
    """Install a cache that keeps nothing, and a counting executor."""
    introspector = backend.introspector
    introspector._cache = InMemoryIntrospectionCache(ttl=0)
    executor = CountingExecutor(backend)
    introspector._executor = executor
    return executor


def cached(backend: SQLiteBackend, delay: float = 0.0) -> Any:
    """Install the default cache, and an executor that may be slow."""
    introspector = backend.introspector
    introspector._cache = InMemoryIntrospectionCache()
    executor = LatentExecutor(backend, delay)
    introspector._executor = executor
    return executor


def measure(backend: SQLiteBackend, repeats: int = 3) -> Tuple[float, int, int]:
    """Time one walk, and report what it cost in questions and answers."""
    executor = backend.introspector._executor
    before = executor.calls
    started = time.perf_counter()
    answers = walk_schema(backend, executor)
    elapsed = time.perf_counter() - started
    return elapsed, executor.calls - before, answers


# --------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------- #


def _ms(seconds: float) -> str:
    return f"{seconds * 1000:9.2f} ms"


def main() -> None:
    backend = fresh_backend()

    # No cache: every question is put to the database every time.
    uncached(backend)
    measure(backend)  # warm whatever the process caches on its own
    cold, questions, answers = measure(backend)

    # Default cache: the same questions, answered from memory.
    cached(backend)
    measure(backend)  # fill it
    warm, warm_questions, _ = measure(backend)

    print(f"SQLite introspection over {TABLES} tables, "
          f"{TABLES * COLUMNS} columns and {TABLES * INDEXES} indexes")
    print(f"  {answers} values answered, {questions} questions put to the database\n")
    print(f"  no cache                {_ms(cold)}   {questions} questions")
    print(f"  cached                  {_ms(warm)}   {warm_questions} questions")
    print(f"\n  cache saves             {_ms(cold - warm)} "
          f"({(cold - warm) / cold * 100:.0f}% of the uncached pass)")

    # The same walk, with each question paying a round trip. Two floors
    # bracketing what a local server backend costs per metadata query.
    # The achieved latency is measured rather than assumed, because
    # ``time.sleep`` only promises a lower bound and a benchmark that
    # reports a number it asked for instead of the number it got is not
    # a benchmark.
    for requested in (0.0005, 0.002):
        executor = cached(backend, requested)
        executor.calls = 0
        server_cold, _, _ = measure(backend)
        server_warm, warm_calls, _ = measure(backend)
        achieved = server_cold / questions if questions else 0.0
        local_cost = cold / questions if questions else 0.0
        print(f"\n  asked the executor to spend {requested * 1000:.1f} ms per question; "
              f"achieved {achieved * 1000:.2f} ms")
        print(f"    SQLite's own cost per question was {local_cost * 1e6:.0f} µs, "
              f"so this is {achieved / local_cost:.0f}× a round trip")
        print(f"    no cache              {_ms(server_cold)}   {questions} questions")
        print(f"    cached                {_ms(server_warm)}   {warm_calls} questions")
        print(f"    cache saves           {_ms(server_cold - server_warm)} "
              f"({(server_cold - server_warm) / server_cold * 100:.0f}% of cold)")

    backend.disconnect()


if __name__ == "__main__":
    main()
