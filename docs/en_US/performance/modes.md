# Architecture Determines Performance

## Performance Through Simplicity

Our framework achieves excellent performance through architectural simplicity rather than complex optimization mechanisms:

- **Direct Architecture**: Only 2 steps from expression to SQL, avoiding multi-layer compilation that adds overhead
- **No Hidden Caching**: Unlike systems that require special query caching mechanisms, our approach is naturally efficient
- **Stateless Expressions**: No object state management overhead during query building
- **Predictable Performance**: Performance scales directly with expression count, without hidden factors

## Two Query Modes

### Strict Mode (Default)

Returns Pydantic-validated model instances:

```python
# Returns list of User instances, fully validated
users = User.query().all()

# Returns a single User instance
user = User.query().where(User.c.id == 1).one()
```

**Use Cases**: Business logic requiring model methods, validation, or relationship loading.

### Raw Mode (High Performance)

Returns raw dictionaries, bypassing Pydantic validation:

```python
# Use aggregate() to get list of raw dictionaries
users = User.query().select(User.c.id, User.c.name).aggregate()
# Returns: [{'id': 1, 'name': 'Alice'}, ...]

# Use aggregate() with aggregation functions
from rhosocial.activerecord.backend.expression import sum_, avg
stats = User.query().aggregate(
    total=sum_(User.c.score),
    avg_score=avg(User.c.score)
)
# Returns: {'total': 1000, 'avg_score': 85.5}
```

**Use Cases**:

- Read-only list display
- Big data export
- Intermediate layer data processing
- Statistical analysis

### Performance Comparison

| Operation | Strict Mode | Raw Mode | Improvement |
|-----------|-------------|----------|-------------|
| 10,000 records query | ~500ms | ~50ms | 10x |
| Validation overhead | Yes | No | - |
| Relationship loading | Supported | Not supported | - |
| Type adapters | Supported | Not supported | - |

> 💡 **AI Prompt Example**: "What's the difference between `aggregate()` and `all()`? When should I use each?"

## Important Notes

1. **Type adapters don't apply**: In `.aggregate()` mode, custom type adapters (`UseAdapter`) won't execute. You get raw data directly from the database driver.

2. **Relationship loading unavailable**: `.aggregate()` doesn't support `.with_()` eager loading because results aren't model instances.

3. **CTEQuery and SetOperationQuery**: These query types only support `.aggregate()`, not `.all()` or `.one()`.
