# Architecture Determines Performance

## Performance Through Simplicity

Our framework achieves excellent performance through architectural simplicity rather than complex optimization mechanisms:

- **Direct Architecture**: Only 2 steps from expression to SQL, avoiding multi-layer compilation that adds overhead
- **No Hidden Caching**: Unlike systems that require special query caching mechanisms, our approach is naturally efficient
- **Stateless Expressions**: No object state management overhead during query building
- **Predictable Performance**: Performance scales directly with expression count, without hidden factors

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
