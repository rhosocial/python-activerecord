# Execution Modes (Strict vs Raw)

## Strict Mode (Default)

By default, all query results undergo Pydantic validation and instantiation. This guarantees data absolutely conforms to the model definition but incurs CPU overhead.

```python
# Returns a list of User instances, fully validated
users = User.find_all()
```

## Raw/Aggregate Mode

When you need to process massive amounts of data (e.g., report export, ETL) and are confident in the database data validity, you can use `.aggregate()` mode (or `find_all(raw=True)`, depending on specific API) to return Python dictionaries or tuples directly.

```python
# Bypass Pydantic, return list of dictionaries directly
# Speed improvement is typically 5x - 10x
users_data = User.query().aggregate()
```

**Use Cases**:
*   Read-only list display
*   Big data export
*   Intermediate layer data processing
