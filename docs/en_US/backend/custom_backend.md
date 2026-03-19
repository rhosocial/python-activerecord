# Custom Backend

To support a new database (e.g., PostgreSQL, MySQL), you need to:

1.  **Inherit `SQLDialectBase`**: Define the SQL syntax specific to that database (quote style, type mapping).
2.  **Inherit `StorageBackend`**: Implement low-level I/O operations such as `connect`, `execute`, `fetch`, `introspect_and_adapt`.

## Backend Self-Adaptation (introspect_and_adapt)

The `introspect_and_adapt()` method is key to achieving sync/async symmetry in backend implementations. It's called automatically during model configuration to ensure the backend adapts to the actual database server version:

1. **Connect to the database** (if not already connected)
2. **Query the actual server version**
3. **Re-initialize dialect and type adapters** to match the actual version

For example, MySQL 5.6 doesn't support JSON type, while MySQL 8.0 does. With `introspect_and_adapt()`, the backend can query the actual version and adjust its feature support accordingly.

For backends that don't need version-specific adaptation (e.g., SQLite, Dummy), this can be implemented as a no-op.

### Version Detection Behavior

The `get_server_version()` method is responsible for retrieving the database server version. **Important Change**: When version detection fails, this method raises an `OperationalError` exception instead of returning a default value.

```python
from rhosocial.activerecord.backend.errors import OperationalError

try:
    version = backend.get_server_version()
except OperationalError as e:
    # Version detection failed, handle the error
    print(f"Unable to get database version: {e}")
```

This design ensures that issues are detected early rather than being masked. Returning a default version number could lead to:
- Subsequent operations on unsupported database versions
- Hard-to-track subtle errors
- Poor user experience

When implementing a custom backend, please ensure:
1. Version detection logic is robust enough
2. Meaningful error messages are provided
3. Consider the impact of connection state on version detection

## Reference Implementations

We recommend referring to the existing implementations in `src/rhosocial/activerecord/backend/impl/`:

*   **`dummy`**: A full-featured backend for testing SQL generation without a real database. It demonstrates how to implement **all** supported protocols using standard mixins.
*   **`sqlite`**: A real-world implementation that handles version-specific feature support (e.g., checking SQLite version for CTE support).

## Protocol-Based Dialect System

The dialect system relies heavily on **Protocols** defined in `src/rhosocial/activerecord/backend/dialect/protocols.py`. These protocols (e.g., `WindowFunctionSupport`, `CTESupport`) define the capabilities of a database.

### The Dummy Dialect: A Complete Example

The `DummyDialect` (`src/rhosocial/activerecord/backend/impl/dummy/dialect.py`) is a great learning resource because it supports **everything**.

Notice how it simply mixes in standard implementations:

```python
class DummyDialect(
    SQLDialectBase,
    # Standard implementations via Mixins
    WindowFunctionMixin, CTEMixin, AdvancedGroupingMixin, ...
    # Protocol definitions for type checking
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ...
):
    # Feature flags
    def supports_window_functions(self) -> bool: return True
    # ...
```

### Implementation Strategy

When implementing a custom dialect (e.g., for MySQL or PostgreSQL), follow this strategy:

1.  **Check the Base Protocol**: Look at `src/rhosocial/activerecord/backend/dialect/protocols.py` to see what methods a feature requires.
2.  **Evaluate Default Implementation**: Check `src/rhosocial/activerecord/backend/dialect/mixins.py` (or the base class). The base implementation is often sufficient for standard SQL.
3.  **Mixin if Compatible**: If the standard SQL behavior works for your database, just inherit the corresponding `Mixin` (e.g., `WindowFunctionMixin`) and set the feature flag to `True`.
4.  **Custom Implementation Only When Necessary**: If your database uses non-standard syntax, ONLY THEN should you implement the protocol methods manually.

### Pay Attention to Formatting Functions

After mixing in a protocol, verify the corresponding formatting methods. For example, if you mix in `WindowFunctionMixin`, check `format_window_function_call` in the mixin/base class.

*   If your database follows standard SQL (e.g., `OVER (...)`), the default implementation works.
*   If it differs, override that specific method.

## RETURNING Clause Support (Important)

When saving new records (INSERT), the framework needs to retrieve the database-generated primary key value. This is achieved through two methods:

### Primary Key Retrieval Strategy

| Priority | Method | Requirement |
|----------|--------|-------------|
| 1 | RETURNING clause | Backend implements `supports_returning_clause()` returning `True` |
| 2 | last_insert_id | Backend provides integer primary key via `cursor.lastrowid` |

### Backend Implementation Requirements

**If the database supports RETURNING clause** (e.g., PostgreSQL, SQLite 3.35+, MySQL 8.0+):

```python
from rhosocial.activerecord.backend.dialect.mixins import ReturningMixin
from rhosocial.activerecord.backend.dialect.protocols import ReturningSupport

class MyDialect(ReturningMixin, ReturningSupport):
    def supports_returning_clause(self) -> bool:
        """Determine RETURNING support based on database version"""
        return self.version >= (x, y, z)  # Replace with actual version
```

**If the database doesn't support RETURNING clause**:

- Must ensure `cursor.lastrowid` is available (most Python database drivers support this)
- Only supports integer auto-increment primary keys (`IntegerPKMixin`)
- Backends without RETURNING support will fail when saving new records with non-integer primary keys (e.g., UUID)

### Compatibility Matrix

| Database | RETURNING Support | Minimum Version |
|----------|-------------------|-----------------|
| SQLite | ✅ | 3.35.0 |
| PostgreSQL | ✅ | All versions |
| MySQL | ❌ | - (uses last_insert_id) |
| MariaDB | ❌ | - (uses last_insert_id) |

> 💡 **AI Prompt Example**: "How do I implement RETURNING clause support in a custom backend? What are the limitations if RETURNING is not supported?"

## Testing and Protocol Support

The Rhosocial ActiveRecord test suite is designed to be protocol-aware. This means it automatically adapts to the capabilities of your backend:

*   **Automatic Test Selection**: The test runner checks your dialect's feature flags (e.g., `supports_window_functions()`).
*   **Skipping Unsupported Features**: If your dialect returns `False` for a specific feature, the corresponding tests are automatically skipped.
*   **Validation**: If your dialect returns `True` but fails to generate valid SQL for that feature, the tests will fail.

Therefore, it is crucial to accurately implement the `supports_*` methods in your dialect. Do not return `True` for features you haven't fully implemented or verified.

## Backend CLI Support

Backends can also serve as command-line tools by implementing a `__main__.py` module. This is useful for debugging, quick database access, or testing your implementation.

For example, the **SQLite** backend (`src/rhosocial/activerecord/backend/impl/sqlite/__main__.py`) can be executed directly:

```bash
# Run a SQL query against a database file
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my.db "SELECT * FROM users"

# Execute a SQL script file
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my.db -f schema.sql --executescript
```

This is achieved by standard Python module execution. When building your own backend, considering adding a CLI interface can greatly enhance the developer experience.
