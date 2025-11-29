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
