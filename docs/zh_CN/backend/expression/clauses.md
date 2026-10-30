# 查询子句 (Query Clauses)

本文档详细介绍了 `rhosocial.activerecord.backend.expression.query_parts` 中表示特定 SQL 查询子句的类。这些类收集参数并将 SQL 生成委托给后端方言。

## JoinType (连接类型)

SQL 连接类型的枚举。存储值是裸词（`inner`、`left` 等），JOIN 关键字由方言拼出。

```python
from rhosocial.activerecord.backend.expression.query_parts import JoinType

# 成员值是裸词，JOIN 关键字由方言拼出
for member in JoinType:
    print(f"{member.name:<12} {member.value}")
```

## WhereClause (WHERE 子句)

表示 SQL 查询中的 `WHERE` 子句。

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import WhereClause

# 库实际声明的构造函数与 and_()
print(inspect.signature(WhereClause.__init__))
print(inspect.signature(WhereClause.and_))
```

### 用法

```python
from rhosocial.activerecord.backend.expression import (
    Column, ComparisonOperator, ComparisonPredicate, IntegerColumn, Literal,
    StringColumn,
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause

# WHERE status = 'active' —— 带类型的列会把普通值自动包成 Literal
where_clause = WhereClause(
    dialect,
    condition=StringColumn(dialect, "status") == "active"
)
sql, params = where_clause.to_sql()
# sql: 'WHERE "status" = ?'
# params: ('active',)

# 同一个谓词也可以用显式节点拼出来
where_clause = WhereClause(
    dialect,
    condition=ComparisonPredicate(
        dialect,
        ComparisonOperator.EQ,
        Column(dialect, "status"),
        Literal(dialect, "active"),
    )
)

# 链式 AND 条件：WHERE status = 'active' AND age > 18
where_clause = where_clause.and_(IntegerColumn(dialect, "age") > 18)
sql, params = where_clause.to_sql()
# sql: 'WHERE "status" = ? AND "age" > ?'
# params: ('active', 18)
```

## GroupByHavingClause (GROUP BY 和 HAVING 子句)

表示组合的 `GROUP BY` 和 `HAVING` 子句。强制执行 `HAVING` 需要 `GROUP BY` 的规则。

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause

print(inspect.signature(GroupByHavingClause.__init__))
```

### 用法

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

## OrderByClause (ORDER BY 子句)

表示 `ORDER BY` 子句。

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

print(inspect.signature(OrderByClause.__init__))
```

### 用法

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

## LimitOffsetClause (LIMIT 和 OFFSET 子句)

表示 `LIMIT` 和 `OFFSET` 子句。

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import LimitOffsetClause

print(inspect.signature(LimitOffsetClause.__init__))
```

### 用法

```python
from rhosocial.activerecord.backend.expression.query_parts import LimitOffsetClause

# LIMIT 10 OFFSET 20
limit_clause = LimitOffsetClause(dialect, limit=10, offset=20)
sql, params = limit_clause.to_sql()
# sql: 'LIMIT ? OFFSET ?'
# params: (10, 20)
```

## QualifyClause (QUALIFY 子句)

表示 `QUALIFY` 子句（在 Snowflake/BigQuery 等数据库中用于过滤窗口函数结果）。

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import QualifyClause

print(inspect.signature(QualifyClause.__init__))
```

### 用法

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

## ForUpdateClause (FOR UPDATE 子句)

表示 `FOR UPDATE` 锁定子句。

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause

print(inspect.signature(ForUpdateClause.__init__))
```

### 用法

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

## JoinClause (JOIN 子句)

表示 `JOIN` 子句。支持链式调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import JoinClause

print(inspect.signature(JoinClause.__init__))
for name in ("join", "inner_join", "left_join", "right_join", "full_join", "cross_join"):
    print(name, inspect.signature(getattr(JoinClause, name)))
```

### 用法

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

# 链式调用：users JOIN orders ... LEFT JOIN products ...
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

## GroupingClause (分组子句)

表示 `ROLLUP`、`CUBE` 等分组操作。

```python
import inspect
from rhosocial.activerecord.backend.expression.query_parts import GroupingClause

print(inspect.signature(GroupingClause.__init__))
```

### 用法

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
