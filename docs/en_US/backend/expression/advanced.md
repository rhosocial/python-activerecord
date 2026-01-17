# Advanced Expressions

This document covers advanced SQL features such as Window Functions, CTEs (Common Table Expressions), Set Operations, and JSON functions.

## Window Functions

Window functions perform calculations across a set of table rows that are somehow related to the current row.

### WindowFunctionCall

Represents a call to a window function (e.g., `ROW_NUMBER() OVER (...)`).

```python
from rhosocial.activerecord.backend.expression import WindowFunctionCall, WindowSpecification, Column, Literal
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

# Define Window Specification
window_spec = WindowSpecification(
    dialect,
    partition_by=[Column(dialect, "department")],
    order_by=OrderByClause(dialect, [(Column(dialect, "salary"), "DESC")])
)

# Create Window Function Call
window_func = WindowFunctionCall(
    dialect,
    function_name="ROW_NUMBER",
    window_spec=window_spec,
    alias="row_num"
)

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

### WithQueryExpression

Represents a `WITH` clause containing one or more CTEs.

```python
from rhosocial.activerecord.backend.expression import WithQueryExpression, CTEExpression, Subquery, QueryExpression, TableExpression, Column

# Define a CTE
cte_query = Subquery(dialect, "SELECT id, name FROM users WHERE status = ?", ("active",))
cte = CTEExpression(dialect, name="active_users", query=cte_query)

# Main Query using the CTE
main_query = QueryExpression(
    dialect,
    select=[Column(dialect, "name")],
    from_=TableExpression(dialect, "active_users")
)

# Combine into WITH query
with_query = WithQueryExpression(dialect, ctes=[cte], main_query=main_query)

sql, params = with_query.to_sql()
# sql: 'WITH "active_users" AS (SELECT id, name FROM users WHERE status = ?) SELECT "name" FROM "active_users"'
# params: ("active",)
```

## Set Operations

Combine the results of two or more queries into a single result set.

### SetOperationExpression

Supports `UNION`, `UNION ALL`, `INTERSECT`, and `EXCEPT`.

```python
from rhosocial.activerecord.backend.expression import SetOperationExpression, Subquery

query1 = Subquery(dialect, "SELECT id FROM table1 WHERE col = ?", ("a",))
query2 = Subquery(dialect, "SELECT id FROM table2 WHERE col = ?", ("b",))

# UNION
union_op = SetOperationExpression(
    dialect,
    left=query1,
    right=query2,
    operation="UNION"
)
sql, params = union_op.to_sql()
# sql: '(SELECT id FROM table1 WHERE col = ?) UNION (SELECT id FROM table2 WHERE col = ?)'
# params: ("a", "b")

# INTERSECT
intersect_op = SetOperationExpression(
    dialect,
    left=query1,
    right=query2,
    operation="INTERSECT"
)
sql, params = intersect_op.to_sql()
# sql: '(SELECT id FROM table1 WHERE col = ?) INTERSECT (SELECT id FROM table2 WHERE col = ?)'
# params: ("a", "b")
```

## JSON Functions

Expressions for working with JSON data.

### JSONExpression

Represents JSON path extraction or operations.

```python
from rhosocial.activerecord.backend.expression import JSONExpression, Column

col = Column(dialect, "data")
# Extract value from JSON path
json_extract = JSONExpression(dialect, col, "$.user.name", operation="->>")

sql, params = json_extract.to_sql()
# sql: '"data"->>?', or dialect-specific equivalent like 'JSON_EXTRACT("data", ?)'
# params: ("$.user.name",)
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

## Graph Queries (SQL/PGQ)

Support for Property Graph Queries (SQL/PGQ standard).

### GraphVertex & GraphEdge

Represent vertices and edges in a graph pattern.

```python
from rhosocial.activerecord.backend.expression.graph import GraphVertex, GraphEdge, GraphEdgeDirection, MatchClause

# Define Vertex
v1 = GraphVertex(dialect, "n", "Person")
# sql: (n IS "Person")

# Define Edge
e1 = GraphEdge(dialect, "e", "KNOWS", GraphEdgeDirection.RIGHT)
# sql: -[e IS "KNOWS"]->
```

### MatchClause

Represents a `MATCH` clause for graph pattern matching.

```python
# Match pattern: (n)-[e]->(m)
v2 = GraphVertex(dialect, "m", "Person")
match_clause = MatchClause(dialect, v1, e1, v2)

sql, params = match_clause.to_sql()
# sql: 'MATCH (n IS "Person")-[e IS "KNOWS"]->(m IS "Person")'
# params: ()
```
