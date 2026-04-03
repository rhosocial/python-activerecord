# 11. Testing

rhosocial-activerecord advocates for the "Zero-IO" testing philosophy. With the built-in `DummyBackend`, you can quickly verify model logic and SQL generation without relying on a real database environment.

## Contents

*   [Inspecting SQL with DummyBackend](dummy.md): Learn how to use the dummy backend to verify SQL generation logic.
*   [Testing Strategies](strategies.md): Adopt targeted testing strategies based on component characteristics.
*   [Environment-Aware Fixture Selection](fixtures.md): Automatically select the most appropriate model class based on runtime Python version.

## Testing Strategy Recommendations

1.  **Unit Testing**: Use `DummyBackend` to test business logic and query construction.
2.  **Integration Testing**: Use `SQLiteBackend` (in-memory mode) to test actual database interactions.
3.  **End-to-End Testing**: Perform comprehensive tests in a real database environment (like PostgreSQL).

## Backend Provider Responsibilities

When implementing a backend that uses the testsuite, the provider must handle:

1. **Environment Preparation**:
   - Create database schemas
   - Establish connections
   - Configure test models

2. **Environment Cleanup** (Critical Order):
   ```
   Correct: DROP TABLE → Close Cursors → Disconnect
   Wrong:   Disconnect → DROP TABLE (connection already closed!)
   ```

3. **Common Issues**:
   - Table conflicts (not dropping tables)
   - Data contamination (not cleaning up)
   - Connection leaks (not disconnecting properly)
   - Backend-specific issues (e.g., MySQL async WeakSet iteration)

See `python-activerecord-testsuite/docs/en_US/README.md` for detailed provider implementation guidelines.
