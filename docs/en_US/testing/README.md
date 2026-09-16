# Testing

rhosocial-activerecord advocates for the "Zero-IO" testing philosophy. With the built-in `DummyBackend`, you can quickly verify model logic and SQL generation without relying on a real database environment.

## Contents

*   [Inspecting SQL with DummyBackend](dummy.md): Learn how to use the dummy backend to verify SQL generation logic.
*   [Testing Strategies](strategies.md): Adopt targeted testing strategies based on component characteristics.
*   [Environment-Aware Fixture Selection](fixtures.md): Automatically select the most appropriate model class based on runtime Python version.
*   [Backend Testing Guide](backend_testing.md): Three-tier testing configuration for backend implementations.
*   [Testsuite Provider Guide](provider_guide.md): Provider interface implementation for the testsuite.

## Testing Strategy Recommendations

1.  **Unit Testing**: Use `DummyBackend` to test business logic and query construction.
2.  **Integration Testing**: Use `SQLiteBackend` (in-memory mode) to test actual database interactions.
3.  **End-to-End Testing**: Perform comprehensive tests in a real database environment (like PostgreSQL).

See [Backend Testing Guide](backend_testing.md) for detailed backend testing configuration.

## Backend Provider Responsibilities

When implementing a backend that uses the testsuite, the provider must handle environment preparation, cleanup, and connection management. See [Testsuite Provider Guide](provider_guide.md) for detailed implementation guidelines.
