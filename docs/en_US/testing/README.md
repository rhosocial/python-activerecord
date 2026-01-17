# Chapter 9: Testing

rhosocial-activerecord advocates for the "Zero-IO" testing philosophy. With the built-in `DummyBackend`, you can quickly verify model logic and SQL generation without relying on a real database environment.

## Contents

*   [Using DummyBackend](dummy.md): Learn how to use the dummy backend for high-performance unit testing.

## Testing Strategy Recommendations

1.  **Unit Testing**: Use `DummyBackend` to test business logic and query construction.
2.  **Integration Testing**: Use `SQLiteBackend` (in-memory mode) to test actual database interactions.
3.  **End-to-End Testing**: Perform comprehensive tests in a real database environment (like PostgreSQL).
