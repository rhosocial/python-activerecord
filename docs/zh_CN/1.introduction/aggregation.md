# 高级聚合功能

rhosocial ActiveRecord 提供了一个强大而富有表现力的聚合系统，在功能和易用性方面超越了许多竞争对手的 ORM。

## 丰富的表达式系统

该框架实现了一个全面的 SQL 表达式系统，支持广泛的聚合操作：

- **聚合函数**：标准函数（COUNT, SUM, AVG, MIN, MAX）支持 DISTINCT
- **窗口函数**：完全支持具有复杂框架规范的窗口函数
- **CASE 表达式**：查询中的条件逻辑
- **数学表达式**：查询中的算术运算
- **子查询**：复杂的嵌套查询
- **JSON 表达式**：数据库无关的 JSON 操作

## 高级分组操作

rhosocial ActiveRecord 支持 SQL 标准的高级分组操作：

- **CUBE**：多维分析，具有所有可能的分组组合
- **ROLLUP**：具有递进小计的层次聚合
- **GROUPING SETS**：自定义聚合组合

## 标量和聚合函数模式

聚合 API 提供了两种便捷的执行模式：

1. **标量函数模式**：适用于没有分组的简单聚合
   ```python
   # 直接返回计数
   count = User.query().count()
   ```

2. **聚合函数模式**：适用于具有分组的复杂聚合
   ```python
   # 返回具有多种聚合的结果
   results = User.query()
       .group_by('department')
       .count('id', 'user_count')
       .sum('salary', 'total_salary')
       .aggregate()
   ```

## 跨数据库兼容性

聚合系统自动适应不同的数据库方言，提供一致的 API，同时生成特定于数据库的 SQL。

## 高级查询示例

```python
# 使用 CUBE 进行多维分析
result = User.query()
    .select('department', 'role')
    .cube('department', 'role')
    .count('id', 'count')
    .sum('salary', 'total')
    .aggregate()

# 窗口函数
result = User.query()
    .select('department')
    .window(
        AggregateExpression('AVG', 'salary'),
        partition_by=['department'],
        order_by=['hire_date'],
        frame_type='ROWS',
        frame_start='UNBOUNDED PRECEDING',
        frame_end='CURRENT ROW',
        alias='avg_salary'
    )
    .all()

# 带聚合的 JSON 操作
result = User.query()
    .json_expr('settings', '$.theme', 'extract', alias='theme')
    .group_by('theme')
    .count('id', 'user_count')
    .aggregate()
```

与其他 ORM 相比，rhosocial ActiveRecord 的聚合功能提供了权力和简单性的平衡：

- 比 SQLAlchemy 的聚合 API 更直观
- 比 Django ORM 的有限聚合函数更强大
- 比 Peewee 的基本聚合支持更全面