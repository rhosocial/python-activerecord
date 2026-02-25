# Feature Points for Commit Message Scopes

This document defines the standard "feature points" or scopes that should be used in commit messages, following the Conventional Commits specification (`<type>(scope): <description>`). Using these standardized scopes helps to categorize changes and automatically generate more informative changelogs.

A scope can be subdivided with a hyphen for greater specificity (e.g., `query-cte`). If a commit touches multiple scopes, they should be listed separated by commas (e.g., `feat(query,backend): ...`).

## Core Package Scopes (`rhosocial-activerecord`)

These scopes apply to changes within the main `rhosocial-activerecord` package.

-   **`query`**: Changes related to the query builder, `ActiveQuery`, or query execution logic.
    -   **`query-simple`**: Changes to basic query operations (e.g., `where`, `find`).
    -   **`query-aggregate`**: Changes related to aggregate queries (e.g., `count`, `sum`, `avg`).
    -   **`query-cte`**: Changes related to Common Table Expressions (CTEs).
    -   *Example*: `feat(query-cte): add recursive CTE support`
-   **`backend`**: Changes to the backend abstraction layer.
    -   **`backend-cli`**: Changes specific to backend command-line tools.
    -   **`backend-adapters`**: Changes specific to backend type adapters.
    -   *Example*: `refactor(backend-adapters): simplify the type adapter loading mechanism`
-   **`field`**: Changes related to field types, custom fields, validation, or serialization.
    -   *Example*: `fix(field): correct default value handling for `JsonField`
-   **`relation`**: Changes affecting model relationships (`has_many`, `belongs_to`, etc.).
    -   *Example*: `perf(relation): optimize preloading of nested relationships`
-   **`event`**: Changes to the event hooks system (`before_save`, `after_delete`, etc.).
    -   *Example*: `feat(event): add `before_validation` and `after_validation` hooks`
-   **`mixin`**: Changes related to model mixins like `TimestampMixin`, `SoftDeleteMixin`, etc.
    -   *Example*: `docs(mixin): clarify usage of OptimisticLockingMixin`

## Backend Package Scopes (`rhosocial-activerecord-*`)

These scopes are used for changes within specific backend implementation packages. A sub-scope should be used to specify the feature area.

-   **`<backend_name>`**: Use the name of the backend (e.g., `mysql`, `postgres`, `sqlite`).
    -   **`<backend_name>-cli`**: Changes to the backend's command-line interface.
    -   **`<backend_name>-adapters`**: Changes to the backend's type adapters.
    -   *Example*: `fix(mysql-adapters): handle connection errors during `ping`
-   **`dialect`**: Changes related to a backend's specific SQL dialect.
    -   *Example*: `feat(dialect): implement RETURNING emulation for MySQL`
-   **`driver`**: Changes related to the native database driver integration.
    -   *Example*: `fix(driver): correctly handle `psycopg2.OperationalError`

## Test Suite Package Scopes (`rhosocial-activerecord-testsuite`)

These scopes are for changes within the `rhosocial-activerecord-testsuite` package. The main scopes can be subdivided based on the directory structure.

-   **`feature`**: Changes to standardized feature tests.
    -   **`feature-basic`**: Basic CRUD and model feature tests.
    -   **`feature-events`**: Tests for the event system.
    -   **`feature-mixins`**: Tests for model mixins.
    -   **`feature-query`**: Tests for query functionality.
    -   **`feature-relation`**: Tests for model relationships.
    -   **`feature-backend`**: Tests for backend-specific features.
    -   **`feature-examples`**: Example-based tests.
    -   **`feature-interface`**: Tests for public interfaces.
    -   *Example*: `test(feature-query): add new tests for JSON operations`
-   **`realworld`**: Changes to complex, real-world scenario tests.
    -   *Example*: `test(realworld): add e-commerce scenario`
-   **`benchmark`**: Changes to performance benchmark tests.
    -   *Example*: `test(benchmark): add benchmark for bulk insert performance`
-   **`provider`**: Changes related to the test provider interface (`IProvider`).
    -   *Example*: `refactor(provider): simplify schema setup`