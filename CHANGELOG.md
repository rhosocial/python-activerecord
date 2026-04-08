## [v1.0.0.dev22] - 2026-04-08

### Added

- Added connection pool management system with context awareness, graceful shutdown, and WorkerPool independent Pipe architecture for improved parallel processing capabilities. ([#63](https://github.com/rhosocial/python-activerecord/issues/63))
- Added transaction expression module with BeginTransactionExpression, CommitExpression, RollbackExpression, and SavepointExpression for building transaction SQL statements. ([#64](https://github.com/rhosocial/python-activerecord/issues/64))
- Added server status overview support for SQLite introspection system with sync/async parity, including PRAGMA-based configuration metrics, storage info, and CLI status subcommand. ([#65](https://github.com/rhosocial/python-activerecord/issues/65))


## [v1.0.0.dev21] - 2026-04-06


### Added

- Added `backend.explain(expression, options)` interface with typed, backend-specific result objects. SQLite backends return `SQLiteExplainResult` (bytecode) or `SQLiteExplainQueryPlanResult` (query plan), both with built-in index-usage analysis helpers (`analyze_index_usage()`, `is_full_scan`, `is_index_used`, `is_covering_index`). The interface follows the sync/async parity principle via `SyncExplainBackendMixin` and `AsyncExplainBackendMixin`. ([#56](https://github.com/rhosocial/python-activerecord/issues/56))
- Added connection status display to info command and comprehensive usage examples to introspect subcommand in SQLite CLI ([#57](https://github.com/rhosocial/python-activerecord/issues/57))
- Added intelligent data summarization for logging system with automatic sensitive field masking and configurable truncation. Supports summary, keys_only, and full logging modes. ([#58](https://github.com/rhosocial/python-activerecord/issues/58))
- Added WorkerPool module for multiprocessing task execution with resident worker processes, task queue dispatch, and graceful shutdown. Added FOR UPDATE row-level locking support for SELECT queries with `nowait` and `skip_locked` options. ([#59](https://github.com/rhosocial/python-activerecord/issues/59))
- Added lifecycle hooks for WorkerPool with `WORKER_START`, `WORKER_STOP`, `TASK_START`, `TASK_END` events, and `TaskContext` for task-level data sharing and resource monitoring. ([#60](https://github.com/rhosocial/python-activerecord/issues/60))



### Changed

- Refactored logging system to a separate `rhosocial.activerecord.logging` module with isolated loggers (`propagate=False` by default) to prevent root logger pollution. ([#55](https://github.com/rhosocial/python-activerecord/issues/55))


## [v1.0.0.dev20] - 2026-03-28


### Added

- Added comprehensive database introspection system with support for tables, columns, indexes, foreign keys, views, and triggers across SQLite and MySQL backends. ([#52](https://github.com/rhosocial/python-activerecord/issues/52))


## [v1.0.0.dev19] - 2026-03-22

### Added

- Added IS TRUE/FALSE boolean predicates to expression system for proper SQL boolean comparisons that handle three-valued logic (TRUE, FALSE, NULL). Added lazy loading for async SQLite components to allow installation without aiosqlite dependency. ([#48](https://github.com/rhosocial/python-activerecord/issues/48))
- Added batch execution interfaces `execute_batch_dml()` and `execute_batch_dql()` to the backend layer, supporting homogeneous DML expressions with RETURNING clause through expression-dialect system, and lazy pagination for DQL queries. ([#49](https://github.com/rhosocial/python-activerecord/issues/49))


## [v1.0.0.dev18] - 2026-03-20

### Added

- Added Python 3.10+ UnionType syntax support (X | Y) for model field type annotations, with environment-aware fixture selection for Python version-specific features. ([#43](https://github.com/rhosocial/python-activerecord/issues/43))



### Fixed

- Resolve SonarCloud code quality issues (S5807, S5754, S1192, S1172): fix missing `__all__` exports, improve exception handling, reduce string duplication, and address unused parameters. ([#44](https://github.com/rhosocial/python-activerecord/issues/44))
- Reduce cognitive complexity (S3776) for 4 high-complexity functions in SQLite dialect and relational query modules. ([#45](https://github.com/rhosocial/python-activerecord/issues/45))


## [v1.0.0.dev17] - 2026-03-16

### Added

- Enhance SQLite backend with FTS5, Pragma system, Generated Columns, and CLI improvements ([#39](https://github.com/rhosocial/python-activerecord/issues/39))



### Changed

- Changed `get_server_version()` to raise `OperationalError` on failure instead of returning a default version, ensuring database environment issues are detected early. Removed unused error classes (`ReturningNotSupportedError`, `VersionParseError`). ([#40](https://github.com/rhosocial/python-activerecord/issues/40))


## [v1.0.0.dev16] - 2026-03-12

### Added

- Added comprehensive DDL support including schema, index, sequence, trigger, function DDL expressions, materialized views, and SQL standard functions with full protocol-based backend abstraction. ([#36](https://github.com/rhosocial/python-activerecord/issues/36))


## [v1.0.0.dev15] - 2026-02-27


### Added

- Completed major refactoring: expression-dialect system with 100% coverage, AsyncBaseActiveRecord with full async CRUD support, ActiveQuery/CTEQuery/SetOperationQuery with async versions, relation system refactoring, and Protocol-based backend feature detection. ([#32](https://github.com/rhosocial/python-activerecord/issues/32))
- Added `introspect_and_adapt()` method to backends for self-adaptation to actual database server capabilities, achieving full sync/async symmetry. ([#33](https://github.com/rhosocial/python-activerecord/issues/33))


## [1.0.0.dev14] - 2025-12-11

### Added

- Added support for handling Union types in type adapters, resolving issues when converting optional (Union) types from the database. ([#26](https://github.com/rhosocial/python-activerecord/issues/26))
- Added support for custom column name mapping via the `UseColumn` annotation, allowing model fields to map to different database column names. ([#27](https://github.com/rhosocial/python-activerecord/issues/27))
- Introduce dummy backends for offline SQL generation and enhance .join() to support model-based relationship joins. ([#28](https://github.com/rhosocial/python-activerecord/issues/28))



### Changed

- Timestamp fields in `TimestampMixin` now use UTC instead of local time to ensure timezone consistency. ([#25](https://github.com/rhosocial/python-activerecord/issues/25))


## [1.0.0.dev13] - 2025-11-29

### Added

- Introduced a comprehensive overhaul of backend-driven type adaptation and refined query CTE handling. ([#20](https://github.com/rhosocial/python-activerecord/issues/20))
- Add backend CLI tool functionality for database operations ([#21](https://github.com/rhosocial/python-activerecord/issues/21))
- Added `CurrentExpression` class for SQL current date/time functions and SQLite-specific datetime tests. ([#22](https://github.com/rhosocial/python-activerecord/issues/22))


## [1.0.0.dev12] - 2025-11-07

### Added

- Added asynchronous backend support alongside existing synchronous backends, enabling developers to use async/await patterns for database operations while maintaining full backward compatibility with synchronous code. ([#17](https://github.com/rhosocial/python-activerecord/issues/17))



### Changed

- Refactored the internal architecture of the backend storage abstraction using a compositional Mixin design, significantly enhancing modularity, code reuse, and extensibility. ([#17](https://github.com/rhosocial/python-activerecord/issues/17))
