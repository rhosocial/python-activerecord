# Query Clauses

This document details the classes in `rhosocial.activerecord.backend.expression.query_parts` that represent specific SQL query clauses. These classes collect parameters and delegate SQL generation to the backend dialect.

## JoinType

Enumeration of SQL JOIN types.

```python
class JoinType(Enum):
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL JOIN"
    CROSS = "CROSS JOIN"
    # ...
```

## WhereClause

Represents a `WHERE` clause in a SQL query.

```python
class WhereClause(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", condition: "bases.SQLPredicate"): ...
    
    def and_(self, predicate: "bases.SQLPredicate") -> 'WhereClause': ...
```

### Usage

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

## GroupByHavingClause

Represents combined `GROUP BY` and `HAVING` clauses. Enforces the rule that `HAVING` requires `GROUP BY`.

```python
class GroupByHavingClause(bases.BaseExpression):
    def __init__(self,
                 dialect: "SQLDialectBase",
                 group_by: Optional[List["bases.BaseExpression"]] = None,
                 having: Optional["bases.SQLPredicate"] = None): ...
```

### Usage

```python
# GROUP BY category HAVING COUNT(id) > 5
# group_clause = GroupByHavingClause(
#     dialect,
#     group_by=[Column(dialect, "category")],
#     having=FunctionCall(dialect, "COUNT", Column(dialect, "id")) > Literal(dialect, 5)
# )
# -> ('GROUP BY "category" HAVING COUNT("id") > ?', (5,))
```

## OrderByClause

Represents an `ORDER BY` clause.

```python
class OrderByClause(bases.BaseExpression):
    def __init__(self,
                 dialect: "SQLDialectBase",
                 expressions: List[Union[
                     "bases.BaseExpression",
                     Tuple["bases.BaseExpression", str]
                 ]]): ...
```

### Usage

```python
# ORDER BY created_at DESC, name ASC
# order_by = OrderByClause(
#     dialect,
#     expressions=[
#         (Column(dialect, "created_at"), "DESC"),
#         (Column(dialect, "name"), "ASC")
#     ]
# )
# -> ('ORDER BY "created_at" DESC, "name" ASC', ())
```

## LimitOffsetClause

Represents `LIMIT` and `OFFSET` clauses.

```python
class LimitOffsetClause(bases.BaseExpression):
    def __init__(self,
                 dialect: "SQLDialectBase",
                 limit: Optional[Union[int, "bases.BaseExpression"]] = None,
                 offset: Optional[Union[int, "bases.BaseExpression"]] = None): ...
```

### Usage

```python
# LIMIT 10 OFFSET 20
# limit_clause = LimitOffsetClause(dialect, limit=10, offset=20)
# -> ('LIMIT ? OFFSET ?', (10, 20))
```

## QualifyClause

Represents a `QUALIFY` clause (used in databases like Snowflake/BigQuery to filter window function results).

```python
class QualifyClause(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", condition: "bases.SQLPredicate"): ...
```

### Usage

```python
# QUALIFY ROW_NUMBER() OVER (...) <= 3
# qualify_clause = QualifyClause(
#     dialect,
#     condition=row_number_func <= Literal(dialect, 3)
# )
# -> ('QUALIFY ROW_NUMBER() OVER (...) <= ?', (3,))
```

## ForUpdateClause

Represents a `FOR UPDATE` locking clause.

```python
class ForUpdateClause(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase",
                 of_columns: Optional[List[Union[str, "bases.BaseExpression"]]] = None,
                 nowait: bool = False,
                 skip_locked: bool = False,
                 dialect_options: Optional[Dict[str, Any]] = None): ...
```

### Usage

```python
# FOR UPDATE OF users NOWAIT
lock_clause = ForUpdateClause(
    dialect,
    of_columns=[Column(dialect, "users")],
    nowait=True
)
```

## JoinExpression

Represents a `JOIN` expression. Supports chaining.

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

### Usage

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

## GroupingExpression

Represents grouping operations like `ROLLUP`, `CUBE`.

```python
class GroupingExpression(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase",
                 operation: str,
                 expressions: List["bases.BaseExpression"]): ...
```

### Usage

```python
# ROLLUP(year, month)
rollup = GroupingExpression(
    dialect,
    operation="ROLLUP",
    expressions=[Column(dialect, "year"), Column(dialect, "month")]
)
```
