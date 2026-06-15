# 属性图查询 (Property Graph Query)

本库提供基于 SQL 2023 (ISO/IEC 9075-16:2023) 标准的属性图查询支持，包括 PGQ（Property Graph Query）DDL 和 DML。

## 概述

属性图查询允许将关系数据建模为图结构（顶点和边），并使用 `MATCH` 子句进行图模式匹配。

核心概念：
- **顶点 (Vertex)**：表示实体，映射到数据库表
- **边 (Edge)**：表示关系，映射到数据库表（含方向）
- **属性图 (Property Graph)**：顶点和边的集合定义

## MATCH 子句

`MatchClause` 用于在 SQL 查询中表达图模式匹配。

### 定义顶点和边

```python
from rhosocial.activerecord.backend.expression.graph import (
    GraphVertex, GraphEdge, GraphEdgeDirection, MatchClause
)

# 创建顶点
person = GraphVertex(dialect, variable="p", table="persons")
product = GraphVertex(dialect, variable="pr", table="products")

# 创建边（从 person 到 product 的有向边）
purchased = GraphEdge(dialect, variable="pu", table="purchases",
                      direction=GraphEdgeDirection.RIGHT)
```

### MATCH 模式

```python
# 定义 MATCH 路径
match = MatchClause(dialect, person, purchased, product)
sql, params = match.to_sql()
# sql: 'MATCH (p) - [pu] -> (pr)'
# params: ()
```

## GRAPH_TABLE 表达式

`GraphTableExpression` 将图匹配结果作为表表达式使用。

```python
from rhosocial.activerecord.backend.expression.graph import (
    GraphTableExpression, MatchClause, GraphColumn, ColumnsClause
)

# 定义图表表达式
graph_table = GraphTableExpression(
    dialect,
    match_clause=match,
    columns=ColumnsClause(dialect, columns=[
        GraphColumn(dialect, name="person_name", type="VARCHAR"),
        GraphColumn(dialect, name="product_name", type="VARCHAR"),
    ])
)
```

## 属性图 DDL

创建、修改和删除属性图。

### CREATE PROPERTY GRAPH

```python
from rhosocial.activerecord.backend.expression.graph import (
    CreatePropertyGraphExpression, VertexTable, EdgeTable
)

# 定义顶点和边表
vertex = VertexTable(dialect, table_name="persons", graph_label="Person")
edge = EdgeTable(dialect, table_name="knows",
                 source_vertex="Person", dest_vertex="Person")

# 创建属性图
create_graph = CreatePropertyGraphExpression(
    dialect,
    graph_name="social_graph",
    vertices=[vertex],
    edges=[edge]
)
# sql: 'CREATE PROPERTY GRAPH "social_graph" ...'
```

### DROP PROPERTY GRAPH

```python
from rhosocial.activerecord.backend.expression.graph import DropPropertyGraphExpression

drop_graph = DropPropertyGraphExpression(
    dialect,
    graph_name="social_graph",
    if_exists=True
)
```

### ALTER PROPERTY GRAPH

```python
from rhosocial.activerecord.backend.expression.graph import AlterPropertyGraphExpression

alter_graph = AlterPropertyGraphExpression(
    dialect,
    graph_name="social_graph",
    action="ADD",  # 或 "DROP"
    element_type="VERTEX TABLE",
    element_name="new_table"
)
```

## 方言支持

| 功能 | Mixin | 方法 |
|------|-------|------|
| MATCH 格式化 | `GraphMixin` | `format_graph_vertex()`、`format_graph_edge()`、`format_match_clause()` |
| GRAPH_TABLE 格式化 | `GraphTableMixin` | `format_graph_table_expression()`、`format_table_properties_clause()` |
| PGQ DDL | `GraphTableMixin` | `format_create/drop/alter_property_graph_statement()` |

方言通过能力查询方法检查支持：

```python
if dialect.supports_graph_match():
    # 支持 MATCH 子句

if dialect.supports_graph_table():
    # 支持 GRAPH_TABLE 表达式

if dialect.supports_property_graph_ddl():
    # 支持属性图 DDL
```

> **注意**：属性图查询是 SQL 2023 标准中新增的功能，目前只有部分数据库（如 Oracle、PostgreSQL 扩展）提供支持。使用前请确认目标数据库的兼容性。
