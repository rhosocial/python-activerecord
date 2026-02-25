# 查询子句 (Query Clauses)

本文档详细介绍了 `rhosocial.activerecord.backend.expression.query_parts` 中表示特定 SQL 查询子句的类。这些类收集参数并将 SQL 生成委托给后端方言。

## JoinType (连接类型)

SQL 连接类型的枚举。

```python
class JoinType(Enum):
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL JOIN"
    CROSS = "CROSS JOIN"
    # ...
```

## WhereClause (WHERE 子句)

表示 SQL 查询中的 `WHERE` 子句。

```python
class WhereClause(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", condition: "bases.SQLPredicate"): ...
    
    def and_(self, predicate: "bases.SQLPredicate") -> 'WhereClause': ...
```

### 用法

```python
# WHERE status = 'active'
# where_clause = WhereClause(
#     dialect,
#     condition=Column(dialect, "status") == Literal(dialect, "active")
# )
# -> ('WHERE "status" = ?', ('active',))

# Chaining AND conditions
# WHERE age > 18 AND status = 'active'
# where_clause.and_(Column(dialect, "age") > Literal(dialect, 18))
# -> ('WHERE "status" = ? AND "age" > ?', ('active', 18))
```

## GroupByHavingClause (GROUP BY 和 HAVING 子句)

表示组合的 `GROUP BY` 和 `HAVING` 子句。强制执行 `HAVING` 需要 `GROUP BY` 的规则。

```python
class GroupByHavingClause(bases.BaseExpression):
    def __init__(self,
                 dialect: "SQLDialectBase",
                 group_by: Optional[List["bases.BaseExpression"]] = None,
                 having: Optional["bases.SQLPredicate"] = None): ...
```

### 用法

```python
# GROUP BY category HAVING COUNT(id) > 5
# group_clause = GroupByHavingClause(
#     dialect,
#     group_by=[Column(dialect, "category")],
#     having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 5)
# )
# -> ('GROUP BY "category" HAVING COUNT("id") > ?', (5,))
```

## OrderByClause (ORDER BY 子句)

表示 `ORDER BY` 子句。

```python
class OrderByClause(bases.BaseExpression):
    def __init__(self,
                 dialect: "SQLDialectBase",
                 expressions: List[Union[
                     "bases.BaseExpression",
                     Tuple["bases.BaseExpression", str]
                 ]]): ...
```

### 用法

```python# ORDER BY created_at DESC, name ASC
# order_by = OrderByClause(
#     dialect,
#     expressions=[
#         (Column(dialect, "created_at"), "DESC"),
#         (Column(dialect, "name"), "ASC")
#     ]
# )
# -> ('ORDER BY "created_at" DESC, "name" ASC', ())
```

## LimitOffsetClause (LIMIT 和 OFFSET 子句)

表示 `LIMIT` 和 `OFFSET` 子句。

```python
class LimitOffsetClause(bases.BaseExpression):
    def __init__(self,
                 dialect: "SQLDialectBase",
                 limit: Optional[Union[int, "bases.BaseExpression"]] = None,
                 offset: Optional[Union[int, "bases.BaseExpression"]] = None): ...
```

### 用法

```python
# LIMIT 10 OFFSET 20
# limit_clause = LimitOffsetClause(dialect, limit=10, offset=20)
# -> ('LIMIT ? OFFSET ?', (10, 20))
```

## QualifyClause (QUALIFY 子句)

表示 `QUALIFY` 子句（在 Snowflake/BigQuery 等数据库中用于过滤窗口函数结果）。

```python
class QualifyClause(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", condition: "bases.SQLPredicate"): ...
```

### 用法

```python
# QUALIFY ROW_NUMBER() OVER (...) <= 3
# qualify_clause = QualifyClause(
#     dialect,
#     condition=row_number_func <= Literal(dialect, 3)
# )
# -> ('QUALIFY ROW_NUMBER() OVER (...) <= ?', (3,))
```

## ForUpdateClause (FOR UPDATE 子句)

表示 `FOR UPDATE` 锁定子句。

```python
class ForUpdateClause(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase",
                 of_columns: Optional[List[Union[str, "bases.BaseExpression"]]] = None,
                 nowait: bool = False,
                 skip_locked: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None): ...
```

### 用法

```python
# FOR UPDATE OF users NOWAIT
lock_clause = ForUpdateClause(
    dialect,
    of_columns=[Column(dialect, "users")],
    nowait=True
)
```

## JoinExpression (JOIN 表达式)

表示 `JOIN` 表达式。支持链式调用。

```python
class JoinExpression(bases.BaseExpression):
    def __init__(self,
                 dialect: "SQLDialectBase",
                 left_table: Union[str, "core.TableExpression", "core.Subquery", "QueryExpression", "JoinExpression"],
                 right_table: Union[str, "core.TableExpression", "core.Subquery", "QueryExpression", "JoinExpression"],
                 join_type: str = "JOIN",
                 condition: Optional["bases.SQLPredicate"] = None,
                 using: Optional[List[str]] = None,
                 natural: bool = False,
                 alias: Optional[str] = None,
                 dialect_options: Optional[Dict[str, Any]] = None): ...

    def join(self, right_table, join_type="JOIN", condition=None, using=None, natural=False, alias=None) -> "JoinExpression": ...
    def inner_join(self, right_table, condition=None, using=None, alias=None) -> "JoinExpression": ...
    def left_join(self, right_table, condition=None, using=None, alias=None) -> "JoinExpression": ...
    def right_join(self, right_table, condition=None, using=None, alias=None) -> "JoinExpression": ...
    def full_join(self, right_table, condition=None, using=None, alias=None) -> "JoinExpression": ...
    def cross_join(self, right_table, alias=None) -> "JoinExpression": ...
```

### 用法

```python
# users JOIN orders ON users.id = orders.user_id
# join_expr = JoinExpression(
#     dialect,
#     left_table=TableExpression(dialect, "users"),
#     right_table=TableExpression(dialect, "orders"),
#     join_type="INNER JOIN",
#     condition=Column(dialect, "id", "users") == Column(dialect, "user_id", "orders")
# )
# -> ('"users" INNER JOIN "orders" ON "users"."id" = "orders"."user_id"', ())

# Chaining: users JOIN orders ... LEFT JOIN products ...
# complex_join = join_expr.left_join(
#     right_table=TableExpression(dialect, "products"),
#     condition=Column(dialect, "product_id", "orders") == Column(dialect, "id", "products")
# )
# -> ('"users" INNER JOIN "orders" ON "users"."id" = "orders"."user_id" LEFT JOIN "products" ON "orders"."product_id" = "products"."id"', ())
```

## GroupingExpression (分组表达式)

表示 `ROLLUP`、`CUBE` 等分组操作。

```python
class GroupingExpression(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase",
                 operation: str,
                 expressions: List["bases.BaseExpression"]): ...
```

### 用法

```python
# ROLLUP(year, month)
rollup = GroupingExpression(
    dialect,
    operation="ROLLUP",
    expressions=[Column(dialect, "year"), Column(dialect, "month")]
)
```
