# Query Clauses

This document details the classes in `rhosocial.activerecord.backend.expression.query_parts` that represent specific SQL query clauses. These classes collect parameters and delegate SQL generation to the backend dialect.

## JoinType

Enumeration of SQL JOIN types. The stored value is the bare word (`inner`,
`left`, ...); the dialect spells the JOIN keyword.

```python
from rhosocial.activerecord.backend.expression.query_parts import JoinType

# The member value is the bare word; the dialect spells the JOIN keyword
for member in JoinType:
    print(f"{member.name:<12} {member.value}")
```

## WhereClause

Represents a `WHERE` clause in a SQL query.

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import WhereClause

# The constructor and and_() as the library declares them
print(inspect.signature(WhereClause.__init__))
print(inspect.signature(WhereClause.and_))
```

### Usage

```python
from rhosocial.activerecord.backend.expression import (
    Column, ComparisonOperator, ComparisonPredicate, IntegerColumn, Literal,
    StringColumn,
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause

# WHERE status = 'active' -- a typed column wraps the plain value in a Literal
where_clause = WhereClause(
    dialect,
    condition=StringColumn(dialect, "status") == "active"
)
sql, params = where_clause.to_sql()
# sql: 'WHERE "status" = ?'
# params: ('active',)

# The same predicate spelled out as an explicit node
where_clause = WhereClause(
    dialect,
    condition=ComparisonPredicate(
        dialect,
        ComparisonOperator.EQ,
        Column(dialect, "status"),
        Literal(dialect, "active"),
    )
)

# Chaining AND conditions: WHERE status = 'active' AND age > 18
where_clause = where_clause.and_(IntegerColumn(dialect, "age") > 18)
sql, params = where_clause.to_sql()
# sql: 'WHERE "status" = ? AND "age" > ?'
# params: ('active', 18)
```

## GroupByHavingClause

Represents combined `GROUP BY` and `HAVING` clauses. Enforces the rule that `HAVING` requires `GROUP BY`.

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause

print(inspect.signature(GroupByHavingClause.__init__))
```

### Usage

```python
from rhosocial.activerecord.backend.expression import Column, FunctionCall
from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause

# GROUP BY category HAVING COUNT(id) > 5
group_clause = GroupByHavingClause(
    dialect,
    group_by=[Column(dialect, "category")],
    having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > 5
)
sql, params = group_clause.to_sql()
# sql: 'GROUP BY "category" HAVING COUNT("id") > ?'
# params: (5,)
```

## OrderByClause

Represents an `ORDER BY` clause.

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

print(inspect.signature(OrderByClause.__init__))
```

### Usage

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

# ORDER BY created_at DESC, name ASC
order_by = OrderByClause(
    dialect,
    expressions=[
        (Column(dialect, "created_at"), "DESC"),
        (Column(dialect, "name"), "ASC")
    ]
)
sql, params = order_by.to_sql()
# sql: 'ORDER BY "created_at" DESC, "name" ASC'
# params: ()
```

## LimitOffsetClause

Represents `LIMIT` and `OFFSET` clauses.

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import LimitOffsetClause

print(inspect.signature(LimitOffsetClause.__init__))
```

### Usage

```python
from rhosocial.activerecord.backend.expression.query_parts import LimitOffsetClause

# LIMIT 10 OFFSET 20
limit_clause = LimitOffsetClause(dialect, limit=10, offset=20)
sql, params = limit_clause.to_sql()
# sql: 'LIMIT ? OFFSET ?'
# params: (10, 20)
```

## QualifyClause

Represents a `QUALIFY` clause (used in databases like Snowflake/BigQuery to filter window function results).

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import QualifyClause

print(inspect.signature(QualifyClause.__init__))
```

### Usage

```python
from rhosocial.activerecord.backend.expression import FunctionCall
from rhosocial.activerecord.backend.expression.query_parts import QualifyClause

# QUALIFY ROW_NUMBER() <= 3
row_number_func = FunctionCall(dialect, "ROW_NUMBER")
qualify_clause = QualifyClause(
    dialect,
    condition=row_number_func <= 3
)
sql, params = qualify_clause.to_sql()
# sql: 'QUALIFY ROW_NUMBER() <= ?'
# params: (3,)
```

## ForUpdateClause

Represents a `FOR UPDATE` locking clause.

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause

print(inspect.signature(ForUpdateClause.__init__))
```

### Usage

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause

# FOR UPDATE OF "users" NOWAIT
lock_clause = ForUpdateClause(
    dialect,
    of_columns=[Column(dialect, "users")],
    nowait=True
)
sql, params = lock_clause.to_sql()
# sql: 'FOR UPDATE OF "users" NOWAIT'
# params: ()
```

## JoinClause

Represents a `JOIN` clause. Supports chaining.

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import JoinClause

print(inspect.signature(JoinClause.__init__))
for name in ("join", "inner_join", "left_join", "right_join", "full_join", "cross_join"):
    print(name, inspect.signature(getattr(JoinClause, name)))
```

### Usage

```python
from rhosocial.activerecord.backend.expression import (
    Column, ComparisonOperator, ComparisonPredicate, NamedRelationRef,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.query_parts import JoinClause

# users JOIN orders ON users.id = orders.user_id
join_expr = JoinClause(
    dialect,
    left_table=NamedRelationRef(dialect, Table(dialect, "users")),
    right_table=NamedRelationRef(dialect, Table(dialect, "orders")),
    join_type="INNER JOIN",
    condition=ComparisonPredicate(
        dialect,
        ComparisonOperator.EQ,
        Column(dialect, "id", "users"),
        Column(dialect, "user_id", "orders"),
    )
)
sql, params = join_expr.to_sql()
# sql: '"users" INNER JOIN "orders" ON "users"."id" = "orders"."user_id"'
# params: ()

# Chaining: users JOIN orders ... LEFT JOIN products ...
complex_join = join_expr.left_join(
    right_table=NamedRelationRef(dialect, Table(dialect, "products")),
    condition=ComparisonPredicate(
        dialect,
        ComparisonOperator.EQ,
        Column(dialect, "product_id", "orders"),
        Column(dialect, "id", "products"),
    )
)
sql, params = complex_join.to_sql()
# sql: '("users" INNER JOIN "orders" ON "users"."id" = "orders"."user_id") '
#      'LEFT JOIN "products" ON "orders"."product_id" = "products"."id"'
# params: ()
```

## GroupingClause

Represents grouping operations like `ROLLUP`, `CUBE`.

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import GroupingClause

print(inspect.signature(GroupingClause.__init__))
```

### Usage

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.query_parts import GroupingClause

# ROLLUP("year", "month")
rollup = GroupingClause(
    dialect,
    operation="ROLLUP",
    expressions=[Column(dialect, "year"), Column(dialect, "month")]
)
sql, params = rollup.to_sql()
# sql: 'ROLLUP("year", "month")'
# params: ()
```
