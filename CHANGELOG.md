## [1.0.0.dev12] - 2025-11-07

### Added

- Added asynchronous backend support alongside existing synchronous backends, enabling developers to use async/await patterns for database operations while maintaining full backward compatibility with synchronous code. ([#17](https://github.com/rhosocial/python-activerecord/issues/17))



### Changed

- Refactored the internal architecture of the backend storage abstraction using a compositional Mixin design, significantly enhancing modularity, code reuse, and extensibility. ([#17](https://github.com/rhosocial/python-activerecord/issues/17))
