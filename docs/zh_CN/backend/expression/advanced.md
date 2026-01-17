# 高级表达式 (Advanced Expressions)

本文档涵盖了高级 SQL 功能，如窗口函数、CTE（公用表表达式）、集合操作和 JSON 函数。

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
