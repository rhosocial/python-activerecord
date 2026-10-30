# 高级表达式 (Advanced Expressions)

本文档涵盖了高级 SQL 功能，如窗口函数、CTE（公用表表达式）、集合操作、类型转换和 JSON 函数。

## 类型转换

rhosocial-activerecord 中的类型转换使用 `TypeCastingMixin`，它提供了 `cast()` 方法用于 SQL 类型转换操作。类型转换操作在内部存储，并在 SQL 生成时应用，支持通过链式调用进行多级类型转换。

### 基本用法：cast() 方法

推荐的方式是在表达式上使用 `cast()` 方法：

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.types import CustomType

col = Column(dialect, "amount")
expr = col.cast(CustomType(dialect, raw="money"))
sql, params = expr.to_sql()
# sql: 'CAST("amount" AS money)'
# params: ()
# PostgreSQL 用自有运算符表示同一个类型转换：'"amount"::money'
```

### 使用 cast() 函数

如需更灵活的控制，可以使用 functions 模块中的 `cast()` 函数：

```python
from rhosocial.activerecord.backend.expression import Column, IntegerColumn, Literal
from rhosocial.activerecord.backend.expression.functions import cast
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType

# 转换列 —— 目标类型必须是 DataType 实例，不能是字符串
col = Column(dialect, "price")
expr = cast(dialect, col, IntegerType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST("price" AS INTEGER)'
# params: ()

# 转换字面值
expr = cast(dialect, Literal(dialect, "123"), TextType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST(? AS TEXT)'
# params: ('123',)

# 转换算术表达式 —— 算术运算需要数值类型的列类
expr = cast(dialect, IntegerColumn(dialect, "value") + 1, TextType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST("value" + ? AS TEXT)'
# params: (1,)
```

### 链式类型转换

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.types import (
    CustomType, DecimalType, FloatType,
)

col = Column(dialect, "amount")
# 多级类型转换：money -> decimal -> float
expr = col.cast(CustomType(dialect, raw="money"))
expr = expr.cast(DecimalType(dialect)).cast(FloatType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST(CAST(CAST("amount" AS money) AS DECIMAL) AS FLOAT)'
# params: ()
```

### 带类型修饰符

类型修饰符是 `DataType` 的构造参数：

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

### 在查询中使用

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.types import DecimalType

# 在 WHERE 子句中使用
col = Column(dialect, "amount")
predicate = col.cast(DecimalType(dialect)) > 100
sql, params = predicate.to_sql()
# sql: 'CAST("amount" AS DECIMAL) > ?'
# params: (100,)

# 在算术表达式中使用
col1 = Column(dialect, "price1")
col2 = Column(dialect, "price2")
expr = col1.cast(DecimalType(dialect)) + col2.cast(DecimalType(dialect))
sql, params = expr.to_sql()
# sql: 'CAST("price1" AS DECIMAL) + CAST("price2" AS DECIMAL)'
# params: ()
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

### 带 OVER 的 FunctionCall

窗口函数调用就是携带 `window_spec` 的 `FunctionCall`：用 `.over(...)`
流式附加窗口规范，或在构造时传入 `window_spec=`。

```python
from rhosocial.activerecord.backend.expression import (
    Column, FunctionCall, Literal, WindowSpecification,
)
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause

# 定义窗口规范
window_spec = WindowSpecification(
    dialect,
    partition_by=[Column(dialect, "department")],
    order_by=OrderByClause(dialect, [(Column(dialect, "salary"), "DESC")])
)

# 创建窗口函数调用并附加窗口规范
window_func = FunctionCall(dialect, "ROW_NUMBER").over(window_spec).as_("row_num")

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

### WithStatement

表示完整的 `WITH` 语句：CTE 定义加上它们所引导的查询。单个 CTE 定义是 `CTEClause`。

```python
from rhosocial.activerecord.backend.expression import (
    CTEClause, Column, NamedRelationRef, QueryStatement, Subquery, WithStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table

# 定义 CTE
cte_query = Subquery(dialect, "SELECT id, name FROM users WHERE status = ?", ("active",))
cte = CTEClause(dialect, name="active_users", query=cte_query)

# 使用 CTE 的主查询
main_query = QueryStatement(
    dialect,
    select=[Column(dialect, "name")],
    from_=NamedRelationRef(dialect, Table(dialect, "active_users"))
)

# 组合成 WITH 查询
with_query = WithStatement(dialect, ctes=[cte], query=main_query)

sql, params = with_query.to_sql()
# sql: 'WITH "active_users" AS ((SELECT id, name FROM users WHERE status = ?)) '
#      'SELECT "name" FROM "active_users"'
# params: ('active',)
```

## 集合操作 (Set Operations)

将两个或多个查询的结果组合成单个结果集。

### SetOperation

支持 `UNION`、`UNION ALL`、`INTERSECT` 和 `EXCEPT`。运算类型是
`SetOperationKind` 的成员；`UNION ALL` 对应 `UNION_ALL` 成员。

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

## JSON 函数

用于处理 JSON 数据的表达式。

### JSONDocumentValue / JSONTextValue

表示 JSON 路径提取。运算符决定用哪个类：`->` 得到文档，是
`JSONDocumentValue`；`->>` 得到文本，是 `JSONTextValue`。
之所以是两个类而不是一个类加一个拼写参数，是因为两者得到的值是不同的
种类 —— 文档可以继续向下索引，文本不行。

```python
from rhosocial.activerecord.backend.expression import (
    JSONDocumentValue,
    JSONTextValue,
)

col = Column(dialect, "data")
# 从 JSON 路径提取值（文本）
json_extract = JSONTextValue(dialect, col, "$.user.name", operation="->>")

# 嵌套路径仍然是文档，可以继续往下走
nested = JSONDocumentValue(dialect, col, "$.user", operation="->")

sql, params = json_extract.to_sql()
# sql: 'JSON_UNQUOTE(JSON_EXTRACT("data", '$.user.name'))'
# params: ()
# 直接拼运算符的方言会渲染成 '"data"->>?' 的形式。
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
