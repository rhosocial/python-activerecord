# 高级表达式 (Advanced Expressions)

本文档涵盖了高级 SQL 功能，如窗口函数、CTE（公用表表达式）、集合操作、类型转换和 JSON 函数。

## 类型转换

rhosocial-activerecord 中的类型转换使用 `TypeCastingMixin`，它提供了 `cast()` 方法用于 SQL 类型转换操作。类型转换操作在内部存储，并在 SQL 生成时应用，支持通过链式调用进行多级类型转换。

### 基本用法：cast() 方法

推荐的方式是在表达式上使用 `cast()` 方法：

```python
from rhosocial.activerecord.backend.expression import Column

col = Column(dialect, "amount")
expr = col.cast("money")
sql, params = expr.to_sql()
# PostgreSQL: ("amount"::money, ())
# 其他后端: (CAST("amount" AS money), ())
```

### 使用 cast() 函数

如需更灵活的控制，可以使用 functions 模块中的 `cast()` 函数：

```python
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.functions import cast

# 转换列
col = Column(dialect, "price")
expr = cast(dialect, col, "integer")
sql, params = expr.to_sql()
# PostgreSQL: ("price"::integer, ())
# 其他后端: (CAST("price" AS integer), ())

# 转换字面值
expr = cast(dialect, "123", "INTEGER")
sql, params = expr.to_sql()
# PostgreSQL: ('123'::INTEGER, ())
# 其他后端: (CAST('123' AS INTEGER), ())

# 转换算术表达式
expr = cast(dialect, Column(dialect, "value") + Literal(dialect, 1), "TEXT")
sql, params = expr.to_sql()
# PostgreSQL: ("value" + 1)::TEXT, ())
# 其他后端: (CAST("value" + 1 AS TEXT), ())
```

### 链式类型转换

```python
from rhosocial.activerecord.backend.expression import Column

col = Column(dialect, "amount")
# 多级类型转换：money -> numeric -> float8
expr = col.cast("money").cast("numeric").cast("float8")
sql, params = expr.to_sql()
# PostgreSQL: ("amount"::money::numeric::float8, ())
```

### 带类型修饰符

类型修饰符应直接包含在类型字符串中：

```python
from rhosocial.activerecord.backend.expression import Column

col = Column(dialect, "name")
expr = col.cast("VARCHAR(100)")
sql, params = expr.to_sql()
# PostgreSQL: ("name"::VARCHAR(100), ())

col2 = Column(dialect, "price")
expr2 = col2.cast("NUMERIC(10,2)")
sql, params = expr2.to_sql()
# PostgreSQL: ("price"::NUMERIC(10,2), ())
```

### 在查询中使用

```python
from rhosocial.activerecord.backend.expression import Column

# 在 WHERE 子句中使用
col = Column(dialect, "amount")
predicate = col.cast("numeric") > 100
sql, params = predicate.to_sql()
# PostgreSQL: ("amount"::numeric > %s, (100,))

# 在算术表达式中使用
col1 = Column(dialect, "price1")
col2 = Column(dialect, "price2")
expr = col1.cast("numeric") + col2.cast("numeric")
sql, params = expr.to_sql()
# PostgreSQL: ("price1"::numeric + "price2"::numeric, ())
```

### PostgreSQL 类型转换语法

PostgreSQL 使用 `::` 操作符进行类型转换，这是 PostgreSQL 特有的语法：

| 标准 SQL | PostgreSQL |
|----------|------------|
| `CAST(x AS integer)` | `x::integer` |
| `CAST(x AS VARCHAR(100))` | `x::VARCHAR(100)` |
| `CAST(CAST(x AS money) AS numeric)` | `x::money::numeric` |

PostgreSQL dialect 会自动使用 `::` 语法生成更简洁的 SQL。

## 窗口函数 (Window Functions)

窗口函数对与当前行相关的表行集执行计算。

### WindowFunctionCall

表示对窗口函数的调用（例如 `ROW_NUMBER() OVER (...)`）。

```python
from rhosocial.activerecord.backend.expression import WindowFunctionCall, WindowSpecification, Column, Literal
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

# 定义窗口规范
window_spec = WindowSpecification(
    dialect,
    partition_by=[Column(dialect, "department")],
    order_by=OrderByClause(dialect, [(Column(dialect, "salary"), "DESC")])
)

# 创建窗口函数调用
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

定义窗口分区内的行框架。

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

## 公用表表达式 (CTEs)

CTE 提供了一种编写辅助语句以在较大查询中使用的方法。

### WithQueryExpression

表示包含一个或多个 CTE 的 `WITH` 子句。

```python
from rhosocial.activerecord.backend.expression import WithQueryExpression, CTEExpression, Subquery, QueryExpression, TableExpression, Column

# 定义 CTE
cte_query = Subquery(dialect, "SELECT id, name FROM users WHERE status = ?", ("active",))
cte = CTEExpression(dialect, name="active_users", query=cte_query)

# 使用 CTE 的主查询
main_query = QueryExpression(
    dialect,
    select=[Column(dialect, "name")],
    from_=TableExpression(dialect, "active_users")
)

# 组合成 WITH 查询
with_query = WithQueryExpression(dialect, ctes=[cte], main_query=main_query)

sql, params = with_query.to_sql()
# sql: 'WITH "active_users" AS (SELECT id, name FROM users WHERE status = ?) SELECT "name" FROM "active_users"'
# params: ("active",)
```

## 集合操作 (Set Operations)

将两个或多个查询的结果组合成单个结果集。

### SetOperationExpression

支持 `UNION`、`UNION ALL`、`INTERSECT` 和 `EXCEPT`。

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

## JSON 函数

用于处理 JSON 数据的表达式。

### JSONExpression

表示 JSON 路径提取或操作。

```python
from rhosocial.activerecord.backend.expression import JSONExpression, Column

col = Column(dialect, "data")
# 从 JSON 路径提取值
json_extract = JSONExpression(dialect, col, "$.user.name", operation="->>")

sql, params = json_extract.to_sql()
# sql: '"data"->>?', 或特定方言的等价形式，如 'JSON_EXTRACT("data", ?)'
# params: ("$.user.name",)
```

## 表函数 (Table Functions)

返回行集的函数，用于 `FROM` 子句。

### TableFunctionExpression

例如：`UNNEST`、`JSON_TABLE`。

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

## 图查询 (Graph Queries - SQL/PGQ)

支持属性图查询 (SQL/PGQ 标准)。

### GraphVertex & GraphEdge

表示图模式中的顶点和边。

```python
from rhosocial.activerecord.backend.expression.graph import GraphVertex, GraphEdge, GraphEdgeDirection, MatchClause

# 定义顶点
v1 = GraphVertex(dialect, "n", "Person")
# sql: (n IS "Person")

# 定义边
e1 = GraphEdge(dialect, "e", "KNOWS", GraphEdgeDirection.RIGHT)
# sql: -[e IS "KNOWS"]->
```

### MatchClause

表示用于图模式匹配的 `MATCH` 子句。

```python
# 匹配模式: (n)-[e]->(m)
v2 = GraphVertex(dialect, "m", "Person")
match_clause = MatchClause(dialect, v1, e1, v2)

sql, params = match_clause.to_sql()
# sql: 'MATCH (n IS "Person")-[e IS "KNOWS"]->(m IS "Person")'
# params: ()
```
