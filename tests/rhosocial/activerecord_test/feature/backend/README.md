# feature/backend — Backend Test Subjects

Common test subjects shared across backends (ddl/dml/introspection/views/schema/transactions/cli/query/adapters/backend/concurrency/named_connection/protocol/functions/dialect), plus vendor-specific subtrees (`sqlite/`).

Layout follows `.claude/plan/2026-09-03/cross-backend-test-taxonomy.md`:
- Common subjects: files/case names mirror the same paths in the backend repos.
- Sync/Async parity: `test_x.py` paired with `test_x_async.py`, co-located.
- `conftest.py` provides shared SQLite fixtures, `requires_*` marker hooks and mock dialect/backend fixtures for the whole subtree.
- `dummy/` + `dummy2/`: DummyDialect offline suites for expression/statement contracts.
- `sqlite/`: SQLite vendor-specific features (`extensions/`, `examples/`).
