# Custom Backend

To support a new database (e.g., PostgreSQL, MySQL), you need to:

1.  **Inherit `SQLDialectBase`**: Define the SQL syntax specific to that database (quote style, type mapping).
2.  **Inherit `StorageBackend`**: Implement low-level I/O operations such as `connect`, `execute`, `fetch`.

The current `sqlite` implementation is a perfect reference example. Please refer to the source code at `src/rhosocial/activerecord/backend/impl/sqlite`.
