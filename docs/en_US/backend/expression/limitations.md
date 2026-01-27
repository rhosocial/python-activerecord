# Expression System Limitations & Considerations

## Important Note: Scope of the Expression System

The rhosocial-activerecord expression system is a powerful and flexible tool for building SQL queries. However, it's important to understand its scope and limitations:

### 1. Expression System Does Not Perform Semantic Validation

The expression system faithfully builds SQL according to user intent, but **does not validate** whether the generated SQL complies with SQL standards or can be successfully executed in the target database.

#### Example: Type Consistency in Set Operations

According to SQL standards, when performing set operations like UNION, INTERSECT, or EXCEPT, all participating queries must have the same number of columns, and corresponding columns must have compatible data types.

```python
# The following code is valid in the expression system but may fail during database execution
from rhosocial.activerecord.backend.expression import (
    Column, Literal, QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.query_sources import SetOperationExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

dialect = DummyDialect()

# First query returns integer ID and text name
query1 = QueryExpression(
    dialect,
    select=[Column(dialect, "id"), Column(dialect, "name")],
    from_=TableExpression(dialect, "users")
)

# Second query returns text email and integer age
query2 = QueryExpression(
    dialect,
    select=[Column(dialect, "email"), Column(dialect, "age")],
    from_=TableExpression(dialect, "customers")
)

# Expression system will successfully build this UNION, but database execution will fail
union_query = SetOperationExpression(
    dialect,
    left=query1,
    right=query2,
    operation="UNION"
)
```

Although the above code is valid at the expression system level, it will fail during database execution due to column type mismatches.

### 2. Database-Specific Constraints

The expression system does not validate the following database-specific constraints:
- Column type compatibility
- Index limitations
- Trigger effects
- Foreign key constraints
- Database-specific syntax limitations

### 3. Reliance on Database Engine Validation

The expression system's responsibilities are:
- Correctly constructing SQL statements
- Handling parameter binding
- Adapting to syntax differences across databases

While the **database engine** is responsible for:
- Validating SQL semantics
- Performing type checking
- Ensuring constraint satisfaction
- Handling execution plan optimization

### 4. Best Practice Recommendations

1. **Thoroughly test in production environment**: Ensure all complex queries are tested on the target database
2. **Understand SQL standards**: Familiarize yourself with semantic requirements of SQL operations you're using
3. **Use appropriate error handling**: Capture and handle potential database execution errors
4. **Leverage database features**: Understand specific features and limitations of your target database

This design is intentional, as it allows the expression system to remain universal while letting the database engine perform its specialized validation functions.