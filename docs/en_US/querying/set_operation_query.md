# SetOperationQuery (Set Operation Query)

`SetOperationQuery` is the object returned after calling set operation methods (like `union`) on `ActiveQuery` or `CTEQuery`. It represents the set operation of two or more query results.

## Supported Operations

*   `union(other)`: Union (UNION). Automatically removes duplicates.
*   `intersect(other)`: Intersection (INTERSECT).
*   `except_(other)`: Difference (EXCEPT / MINUS).

## Methods

### `all() -> List[Dict[str, Any]]`

Executes the set query and returns all results (list of dictionaries).

### `one() -> Optional[Dict[str, Any]]`

Executes the set query and returns the first result (dictionary).

## Usage Examples

### Combining Two Query Results (UNION)

```python
# Query active users
q1 = User.query().where(User.c.is_active == True)

# Query admin users
q2 = User.query().where(User.c.role == 'admin')

# Combine results (automatically removes duplicates)
# SQL: SELECT * FROM users WHERE is_active = 1 UNION SELECT * FROM users WHERE role = 'admin'
union_query = q1.union(q2)

results = union_query.all() # Returns list of dictionaries
```

## Important Limitations and Notes

1.  **Return Type**: `SetOperationQuery` always returns a **list of dictionaries**, even if the source queries are Model-based. This is because set operations may combine columns from different tables, making it impossible to guarantee mapping back to a single Model.

2.  **Immutability**: `SetOperationQuery` **does not support** query building methods like `where`, `select`, `join`, `order_by`, `limit`.
    *   **Incorrect**: `q1.union(q2).where(...)`
    *   **Correct**: `q1.where(...).union(q2.where(...))`
    
    If you need to filter or sort the results after UNION, you must wrap it as part of a subquery or CTE.

3.  **Column Matching**: All queries participating in set operations must have the **same number of columns** and **compatible data types** for corresponding columns.
    *   It is recommended to explicitly use `.select()` to specify columns to ensure order and quantity consistency.
    
    ```python
    # Recommended
    q1 = User.query().select(User.c.name, User.c.email)
    q2 = Admin.query().select(Admin.c.name, Admin.c.email)
    q1.union(q2)
    ```

4.  **Sorting**: `SetOperationQuery` itself does not support `order_by`. If you need to sort the final result, you typically need to wrap it in another query.
