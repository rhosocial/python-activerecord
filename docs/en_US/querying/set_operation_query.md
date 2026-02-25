# SetOperationQuery (Set Operation Query)

`SetOperationQuery` is the object returned after calling set operation methods (like `union`) on `ActiveQuery` or `CTEQuery`. It represents the set operation of two or more query results.

## Supported Operations

*   `union(other)`: Union (UNION). Automatically removes duplicates.
*   `intersect(other)`: Intersection (INTERSECT).
*   `except_(other)`: Difference (EXCEPT / MINUS).

## Operator Overloading

In addition to method calls, `SetOperationQuery` supports using Python operators for set operations, making the code more concise.

*   `|` (Bitwise OR) corresponds to `union()`
*   `&` (Bitwise AND) corresponds to `intersect()`
*   `-` (Subtraction) corresponds to `except_()`

**Examples:**

```python
# Use | operator for UNION
union_query = q1 | q2

# Use & operator for INTERSECT
intersect_query = q1 & q2

# Use - operator for EXCEPT
except_query = q1 - q2
```

## Methods

### `aggregate() -> List[Dict[str, Any]]`

Executes the set query and returns all results (list of dictionaries).

> **Why no `one()` and `all()` methods?**
> 
> Unlike `ActiveQuery`, `SetOperationQuery` does not support `one()` and `all()` methods. This is because set operations (UNION, INTERSECT, EXCEPT) return raw data dictionaries rather than model instances. The `one()` and `all()` methods are specifically designed to return model instances, but the results of set operations cannot guarantee mapping back to a single model type, especially when combining columns from different tables.

**Sync-Async Parity**: `SetOperationQuery` also has an asynchronous counterpart `AsyncSetOperationQuery` with equivalent functionality and consistent APIs. The only difference is that the asynchronous version requires using the `await` keyword to call the `aggregate()` method.

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

results = union_query.aggregate() # Returns list of dictionaries
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
5.  **Exploring Class Members**: If you want to know what methods are available in the `SetOperationQuery` class, you can use JetBrains PyCharm or other IDEs with code intelligence. Alternatively, you can write a simple script to check class members:
    ```python
    from rhosocial.activerecord.query.set_operation import SetOperationQuery
    methods = [method for method in dir(SetOperationQuery) if not method.startswith('_')]
    print("SetOperationQuery methods:", sorted(methods))
    ```
