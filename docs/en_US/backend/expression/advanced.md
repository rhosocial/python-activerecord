# Advanced Expressions

This document covers advanced SQL features such as Window Functions, CTEs (Common Table Expressions), Set Operations, Type Casting, and JSON functions.

## Type Casting

Type casting in rhosocial-activerecord uses the `TypeCastingMixin` which provides the `cast()` method for SQL type conversion operations. The cast operations are stored internally and applied during SQL generation, supporting multi-level type conversions through method chaining.

### Basic Usage with cast() Method

The preferred way is through the `cast()` method on expressions:

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.types import CustomType

col = Column(dialect, "amount")
expr = col.cast(CustomType(dialect, raw="money"))
sql, params = expr.to_sql()
# sql: 'CAST("amount" AS money)'
# params: ()
# PostgreSQL spells the same cast with its own operator: '"amount"::money'
```

### Using the cast() Function

For more flexibility, you can use the `cast()` function from the functions module:

```python
from rhosocial.activerecord.backend.expression import Column, IntegerColumn, Literal
from rhosocial.activerecord.backend.expression.functions import cast
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType

# Cast a column -- the target is a DataType instance, never a string
col = Column(dialect, "price")
expr = cast(dialect, col, IntegerType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST("price" AS INTEGER)'
# params: ()

# Cast a literal value
expr = cast(dialect, Literal(dialect, "123"), TextType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST(? AS TEXT)'
# params: ('123',)

# Cast an arithmetic expression -- arithmetic needs a numeric column class
expr = cast(dialect, IntegerColumn(dialect, "value") + 1, TextType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST("value" + ? AS TEXT)'
# params: (1,)
```

### Chained Type Conversions

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.types import (
    CustomType, DecimalType, FloatType,
)

col = Column(dialect, "amount")
# Multi-level type conversion: money -> decimal -> float
expr = col.cast(CustomType(dialect, raw="money"))
expr = expr.cast(DecimalType(dialect)).cast(FloatType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST(CAST(CAST("amount" AS money) AS DECIMAL) AS FLOAT)'
# params: ()
```

### With Type Modifiers

Type modifiers are constructor arguments of the `DataType`:

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.types import DecimalType, VarCharType

col = Column(dialect, "name")
expr = col.cast(VarCharType(dialect, length=100))
sql, params = expr.to_sql()
# sql: 'CAST("name" AS VARCHAR(100))'
# params: ()

col2 = Column(dialect, "price")
expr2 = col2.cast(DecimalType(dialect, precision=10, scale=2))
sql, params = expr2.to_sql()
# sql: 'CAST("price" AS DECIMAL(10,2))'
# params: ()
```

### Using in Queries

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.types import DecimalType

# Use in WHERE clause
col = Column(dialect, "amount")
predicate = col.cast(DecimalType(dialect)) > 100
sql, params = predicate.to_sql()
# sql: 'CAST("amount" AS DECIMAL) > ?'
# params: (100,)

# Use in arithmetic expressions
col1 = Column(dialect, "price1")
col2 = Column(dialect, "price2")
expr = col1.cast(DecimalType(dialect)) + col2.cast(DecimalType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST("price1" AS DECIMAL) + CAST("price2" AS DECIMAL)'
# params: ()
```

### PostgreSQL Type Casting Syntax

PostgreSQL uses the `::` operator for type casting, which is PostgreSQL-specific syntax:

| Standard SQL | PostgreSQL |
|--------------|------------|
| `CAST(x AS integer)` | `x::integer` |
| `CAST(x AS VARCHAR(100))` | `x::VARCHAR(100)` |
| `CAST(CAST(x AS money) AS numeric)` | `x::money::numeric` |

The PostgreSQL dialect automatically uses the `::` syntax to generate more concise SQL.

## Window Functions

Window functions perform calculations across a set of table rows that are somehow related to the current row.

### FunctionCall with OVER

A window function call is a `FunctionCall` carrying a `window_spec`: attach
it fluently with `.over(...)`, or pass `window_spec=` at construction.

```python
from rhosocial.activerecord.backend.expression import (
    Column, FunctionCall, Literal, WindowSpecification,
)
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

# Define Window Specification
window_spec = WindowSpecification(
    dialect,
    partition_by=[Column(dialect, "department")],
    order_by=OrderByClause(dialect, [(Column(dialect, "salary"), "DESC")])
)

# Create Window Function Call and attach the window specification
window_func = FunctionCall(dialect, "ROW_NUMBER").over(window_spec).as_("row_num")

sql, params = window_func.to_sql()
# sql: 'ROW_NUMBER() OVER (PARTITION BY "department" ORDER BY "salary" DESC) AS "row_num"'
# params: ()
```

### Window Frame Specification

Defines the frame of rows within the window partition.

```python
from rhosocial.activerecord.backend.expression import WindowFrameSpecification

frame_spec = WindowFrameSpecification(
    dialect,
    frame_type="ROWS",
    start_frame="UNBOUNDED PRECEDING",
    end_frame="CURRENT ROW"
)

sql, params = frame_spec.to_sql()
# sql: 'ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW'
# params: ()
```

## Common Table Expressions (CTEs)

CTEs provide a way to write auxiliary statements for use in a larger query.

### WithStatement

Represents a complete `WITH` statement: the CTE definitions plus the query they precede. A single CTE definition is a `CTEClause`.

```python
from rhosocial.activerecord.backend.expression import (
    CTEClause, Column, NamedRelationRef, QueryStatement, Subquery, WithStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table

# Define a CTE
cte_query = Subquery(dialect, "SELECT id, name FROM users WHERE status = ?", ("active",))
cte = CTEClause(dialect, name="active_users", query=cte_query)

# Main Query using the CTE
main_query = QueryStatement(
    dialect,
    select=[Column(dialect, "name")],
    from_=NamedRelationRef(dialect, Table(dialect, "active_users"))
)

# Combine into WITH query
with_query = WithStatement(dialect, ctes=[cte], query=main_query)

sql, params = with_query.to_sql()
# sql: 'WITH "active_users" AS ((SELECT id, name FROM users WHERE status = ?)) '
#      'SELECT "name" FROM "active_users"'
# params: ('active',)
```

## Set Operations

Combine the results of two or more queries into a single result set.

### SetOperation

Supports `UNION`, `UNION ALL`, `INTERSECT`, and `EXCEPT`. The operation is a
`SetOperationKind` member; `UNION ALL` is the `UNION_ALL` member.

```python
from rhosocial.activerecord.backend.expression import Subquery
from rhosocial.activerecord.backend.expression.query_sources import (
    SetOperation, SetOperationKind,
)

query1 = Subquery(dialect, "SELECT id FROM table1 WHERE col = ?", ("a",))
query2 = Subquery(dialect, "SELECT id FROM table2 WHERE col = ?", ("b",))

# UNION
union_op = SetOperation(
    dialect,
    op=SetOperationKind.UNION,
    left=query1,
    right=query2
)
sql, params = union_op.to_sql()
# sql: '(SELECT id FROM table1 WHERE col = ?) UNION (SELECT id FROM table2 WHERE col = ?)'
# params: ('a', 'b')

# INTERSECT
intersect_op = SetOperation(
    dialect,
    op=SetOperationKind.INTERSECT,
    left=query1,
    right=query2
)
sql, params = intersect_op.to_sql()
# sql: '(SELECT id FROM table1 WHERE col = ?) INTERSECT (SELECT id FROM table2 WHERE col = ?)'
# params: ('a', 'b')
```

## JSON Functions

Expressions for working with JSON data.

### JSONDocumentValue / JSONTextValue

Represents JSON path extraction. The operator picks the class: ``->``
yields a document and is a ``JSONDocumentValue``, ``->>`` yields text and
is a ``JSONTextValue``. Two classes rather than one class with a spelling
parameter, because the two results are different kinds of value -- a document
can be indexed into again, text cannot.

```python
from rhosocial.activerecord.backend.expression import (
    JSONDocumentValue,
    JSONTextValue,
)

col = Column(dialect, "data")
# Extract value from JSON path as text
json_extract = JSONTextValue(dialect, col, "$.user.name", operation="->>")

# A nested path is still a document, so it can be walked further
nested = JSONDocumentValue(dialect, col, "$.user", operation="->")

sql, params = json_extract.to_sql()
# sql: 'JSON_UNQUOTE(JSON_EXTRACT("data", '$.user.name'))'
# params: ()
# Dialects that spell the operator directly render '"data"->>?' form instead.
```

## Table Functions

Functions that return a set of rows, used in the `FROM` clause.

### TableFunctionExpression

Example: `UNNEST`, `JSON_TABLE`.

```python
from rhosocial.activerecord.backend.expression import TableFunctionExpression, Literal

arg = Literal(dialect, ["a", "b", "c"])
unnest_expr = TableFunctionExpression(
    dialect,
    "UNNEST",
    arg,
    alias="elements",
    column_names=["val"]
)

sql, params = unnest_expr.to_sql()
# sql: 'UNNEST(?) AS "elements"("val")'
# params: (["a", "b", "c"],)
```
