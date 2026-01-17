# Custom Backend

To support a new database (e.g., PostgreSQL, MySQL), you need to:

1.  **Inherit `SQLDialectBase`**: Define the SQL syntax specific to that database (quote style, type mapping).
2.  **Inherit `StorageBackend`**: Implement low-level I/O operations such as `connect`, `execute`, `fetch`.

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

## Testing and Protocol Support

The Rhosocial ActiveRecord test suite is designed to be protocol-aware. This means it automatically adapts to the capabilities of your backend:

*   **Automatic Test Selection**: The test runner checks your dialect's feature flags (e.g., `supports_window_functions()`).
*   **Skipping Unsupported Features**: If your dialect returns `False` for a specific feature, the corresponding tests are automatically skipped.
*   **Validation**: If your dialect returns `True` but fails to generate valid SQL for that feature, the tests will fail.

Therefore, it is crucial to accurately implement the `supports_*` methods in your dialect. Do not return `True` for features you haven't fully implemented or verified.
