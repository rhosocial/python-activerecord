# 自定义后端 (Custom Backend)

要支持新的数据库（如 PostgreSQL, MySQL），你需要：

1.  **继承 `SQLDialectBase`**: 定义该数据库特定的 SQL 语法（引号风格、类型映射）。
2.  **继承 `StorageBackend`**: 实现 `connect`, `execute`, `fetch` 等底层 I/O 操作。

目前 `sqlite` 实现是一个完美的参考范例。请查阅 `src/rhosocial/activerecord/backend/impl/sqlite` 源码。
