# 聚合查询

聚合查询允许您对数据库中的行组执行计算。rhosocial ActiveRecord提供了一套全面的工具，用于构建和执行从简单计数到复杂统计分析的聚合查询。

## 概述

聚合函数对多行进行操作并返回单个值。常见的例子包括COUNT、SUM、AVG、MIN和MAX。rhosocial ActiveRecord通过`AggregateQueryMixin`类实现这些函数，该类扩展了基本查询功能，增加了聚合能力。

## 目录

- [基本聚合函数](basic_aggregate_functions.md)
  - COUNT、SUM、AVG、MIN、MAX
  - 在聚合函数中使用DISTINCT
  - 标量与分组聚合

- [分组操作](group_by_operations.md)
  - 按列分组数据
  - 多列分组
  - 分组中NULL值的处理

- [Having子句](having_clauses.md)
  - 过滤分组结果
  - 结合WHERE和HAVING
  - 在HAVING中使用聚合函数

- [复杂聚合](complex_aggregations.md)
  - 组合多个聚合函数
  - 聚合中的子查询
  - 条件聚合

- [窗口函数](window_functions.md)
  - OVER子句基础
  - 数据分区
  - 窗口框架规范
  - 命名窗口
  - 常用窗口函数（ROW_NUMBER、RANK等）

- [统计查询](statistical_queries.md)
  - 统计函数
  - 百分位数和分布
  - 相关性和回归

- [JSON操作](json_operations.md)
  - JSON提取（EXTRACT）
  - JSON文本提取（EXTRACT_TEXT）
  - JSON包含检查（CONTAINS）
  - JSON路径存在检查（EXISTS）
  - JSON类型检索（TYPE）
  - JSON元素操作（REMOVE/INSERT/REPLACE/SET）

- [自定义表达式](custom_expressions.md)
  - 算术表达式
  - 函数表达式
  - CASE表达式
  - 条件表达式（COALESCE、NULLIF等）
  - 子查询表达式
  - 分组集合表达式（CUBE、ROLLUP、GROUPING SETS）

## 数据库兼容性

并非所有数据库都支持相同的聚合功能。rhosocial ActiveRecord在不同的数据库后端之间提供了一致的API，但某些高级功能可能并非在所有数据库上都可用：

- **基本聚合**（COUNT、SUM、AVG、MIN、MAX）被所有数据库支持
- **窗口函数**由PostgreSQL、MySQL 8.0+、MariaDB 10.2+和SQLite 3.25+支持
- **JSON操作**由PostgreSQL、MySQL 5.7+、MariaDB 10.2+和SQLite 3.9+支持（语法可能不同）
- **高级分组**（CUBE、ROLLUP、GROUPING SETS）由PostgreSQL完全支持，MySQL/MariaDB部分支持（仅ROLLUP），SQLite不支持

该库会自动适应您的数据库的功能，并在使用不支持的功能时引发适当的异常。