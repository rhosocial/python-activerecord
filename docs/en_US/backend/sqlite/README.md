# SQLite Backend Documentation

> **AI Learning Assistant**: Key concepts in this documentation are marked with AI Prompt. When you encounter concepts you don't understand, you can ask the AI assistant directly.
>
> **Example:** "How does the SQLite backend handle transactions?"

## Table of Contents

1. **[Introduction](introduction/README.md)**
    *   **[SQLite Backend Overview](introduction/README.md)**: Architecture, sync/async parity, and quick example
    *   **[Supported Versions](introduction/README.md#version-requirements)**: SQLite version matrix

2. **[Installation & Configuration](installation_and_configuration/README.md)**
    *   **[Installation](installation_and_configuration/README.md#installation)**: pip installation and async driver setup
    *   **[Connection Configuration](installation_and_configuration/README.md#connection-configuration)**: Database path, in-memory databases, and options

3. **[SQLite Specific Features](backend_specific_features/README.md)**
    *   **[Pragma System](backend_specific_features/pragma.md)**: SQLite PRAGMA configuration and queries
    *   **[Extension Framework](backend_specific_features/extension.md)**: Extension detection and management
    *   **[Full-Text Search (FTS5)](backend_specific_features/fts5.md)**: FTS5 full-text search functionality
    *   **[Version Feature Support](backend_specific_features/README.md#version-feature-support-matrix)**: Feature availability by version
    *   **[Known Limitations](backend_specific_features/README.md#known-limitations)**: SQLite-specific constraints

4. **[DDL Operations](ddl/README.md)**
    *   **[DDL Overview](ddl/README.md)**: Schema management and SQLite DDL limitations

5. **[Transaction Support](transaction_support/README.md)**
    *   **[Transaction Overview](transaction_support/README.md)**: Transaction manager API
    *   **[Savepoints](transaction_support/README.md#savepoints)**: Nested transactions
    *   **[Isolation Level](transaction_support/README.md#isolation-level)**: SQLite isolation semantics

6. **[Type Adapters](type_adapters/README.md)**
    *   **[Type Mapping](type_adapters/README.md#type-mapping)**: SQLite to Python type conversion
    *   **[Special Types](type_adapters/README.md#special-types)**: datetime, UUID, Decimal, JSON support

7. **[Testing](testing/README.md)**
    *   **[Testing Principles](testing/README.md)**: Sync/async parity, expression tests, testsuite usage

8. **[Troubleshooting](troubleshooting/README.md)**
    *   **[Common Issues](troubleshooting/README.md)**: Database locked, WAL mode, and other SQLite pitfalls

9. **[Scenarios](scenarios/README.md)**
    *   **[Concurrency Characteristics](scenarios/README.md)**: File locking, network storage, and deployment patterns

10. **[Customization](customization/README.md)**
    *   **[Custom Expressions](customization/README.md#custom-expressions)**: SQLite-specific SQL syntax
    *   **[Custom Types](customization/README.md#custom-data-types)**: Extending the type system
    *   **[Custom Adapters](customization/README.md#custom-type-adapters)**: Registering type converters

11. **[Command-Line Interface](cli/README.md)**
    *   **[CLI Overview](cli/README.md)**: Query, introspect, and manage SQLite databases

## Additional Resources

- **[Custom SQLite Build](custom-sqlite-build.md)**: Building custom SQLite with extensions
- **[Core Library Documentation](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US)**: Complete ActiveRecord framework docs

> **Core Library Documentation**: For the complete ActiveRecord framework documentation (modeling, querying, relationships, performance, worker pools), refer to [rhosocial-activerecord documentation](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US).

💡 *AI Prompt:* "How does the SQLite backend differ from MySQL or PostgreSQL backends?"
