# 公共表表达式（CTEs）

本节介绍ActiveRecord中的公共表表达式（CTEs）功能，它允许您编写更易读和易维护的复杂查询。

## 概述

公共表表达式（CTEs）是临时命名的结果集，您可以在SELECT、INSERT、UPDATE或DELETE语句中引用它们。它们使用SQL中的WITH子句定义，仅在查询执行期间存在。CTEs通过将复杂查询分解为更简单的命名组件，使其更易读。

ActiveRecord通过`CTEQueryMixin`类提供了对CTEs的全面支持，该类包含在标准的`ActiveQuery`实现中。

## 主要特性

- 使用SQL字符串或ActiveQuery实例定义CTEs
- 支持递归CTEs，用于层次数据查询
- 支持物化提示（当数据库支持时）
- 支持在单个查询中使用多个CTEs
- 链式方法调用，用于增量构建复杂查询

## 基本用法

### 定义简单的CTE

```python
# 定义一个选择活跃用户的CTE
query = User.query().with_cte(
    'active_users',
    "SELECT * FROM users WHERE status = 'active'"
).from_cte('active_users').all()
```

### 使用ActiveQuery实例定义CTE

为了安全起见，建议使用ActiveQuery实例定义CTE，因为它可以正确地参数化值：

```python
# 使用ActiveQuery定义子查询
subquery = User.query().where('status = ?', ('active',))

# 在CTE中使用子查询
query = User.query().with_cte(
    'active_users',
    subquery
).from_cte('active_users').order_by('name').all()
```

### 使用带列别名的CTEs

```python
# 定义带有显式列名的CTE
query = Order.query().with_cte(
    'order_summary',
    "SELECT order_number, total_amount FROM orders",
    columns=['order_no', 'amount']  # 在CTE中重命名列
).from_cte('order_summary')

# 从CTE中选择所有列
query.select('order_summary.*')

# 由于我们绕过了模型，使用字典查询获取结果
results = query.to_dict(direct_dict=True).all()
```

### 在单个查询中使用多个CTEs

```python
# 定义多个CTEs
query = Order.query()

# 第一个CTE：活跃订单
query.with_cte(
    'active_orders',
    "SELECT * FROM orders WHERE status IN ('pending', 'paid')"
)

# 第二个CTE：昂贵订单
query.with_cte(
    'expensive_orders',
    "SELECT * FROM active_orders WHERE total_amount > 300.00"
)

# 使用第二个CTE
query.from_cte('expensive_orders')

results = query.all()
```

## 递归CTEs

递归CTEs特别适用于查询层次数据，如组织结构图、类别树或物料清单。

### 基本递归CTE

```python
# 定义递归CTE来遍历树结构
recursive_sql = """
                SELECT id, name, parent_id, 1 as level \
                FROM nodes \
                WHERE id = 1
                UNION ALL
                SELECT n.id, n.name, n.parent_id, t.level + 1
                FROM nodes n
                         JOIN tree t ON n.parent_id = t.id \
                """

query = Node.query().with_recursive_cte("tree", recursive_sql)
query.from_cte("tree")
query.order_by("level, id")

results = query.to_dict(direct_dict=True).all()
```

### 带深度限制的递归CTE

```python
# 定义带最大深度限制的递归CTE
recursive_sql = """
                SELECT id, name, parent_id, 1 as level \
                FROM nodes \
                WHERE id = 1
                UNION ALL
                SELECT n.id, n.name, n.parent_id, t.level + 1
                FROM nodes n
                         JOIN tree t ON n.parent_id = t.id
                WHERE t.level < 2 \
                """ #  -- 将递归限制为深度2

query = Node.query().with_recursive_cte("tree", recursive_sql)
query.from_cte("tree")
query.order_by("level, id")

results = query.to_dict(direct_dict=True).all()
```

### 在层次数据中查找路径

```python
# 查找从根节点到特定节点的路径
recursive_sql = """
                -- 锚成员：从目标节点开始
                SELECT id, name, parent_id, CAST(id AS TEXT) as path
                FROM nodes
                WHERE id = 5

                UNION ALL

                -- 递归成员：添加父节点
                SELECT n.id, n.name, n.parent_id, CAST(n.id AS TEXT) || ',' || t.path
                FROM nodes n
                         JOIN path_finder t ON n.id = t.parent_id \
                """

query = Node.query().with_recursive_cte("path_finder", recursive_sql)
query.from_cte("path_finder")
query.order_by("length(path) DESC")  # 最长路径优先（完整路径）

results = query.to_dict(direct_dict=True).all()
```

## 数据库支持

ActiveRecord提供了方法来检查您的数据库是否支持各种CTE功能：

```python
# 检查数据库是否支持CTEs
if User.query().supports_cte():
    # 使用CTEs
    pass

# 检查数据库是否支持递归CTEs
if User.query().supports_recursive_cte():
    # 使用递归CTEs
    pass

# 检查数据库是否支持物化提示
if User.query().supports_materialized_hint():
    # 使用物化提示
    pass

# 检查数据库是否支持多个CTEs
if User.query().supports_multiple_ctes():
    # 使用多个CTEs
    pass
```

## 物化提示

一些数据库支持CTEs的物化提示，这可能会影响数据库处理CTE的方式：

```python
# 带物化提示的CTE
query = User.query().with_cte(
    'active_users',
    "SELECT * FROM users WHERE status = 'active'",
    materialized=True  # 强制物化
).from_cte('active_users').all()

# 带NOT MATERIALIZED提示的CTE
query = User.query().with_cte(
    'active_users',
    "SELECT * FROM users WHERE status = 'active'",
    materialized=False  # 防止物化
).from_cte('active_users').all()
```

## 最佳实践

1. **使用ActiveQuery实例**：尽可能使用ActiveQuery实例而不是原始SQL字符串来定义CTEs，以获得更好的安全性和可维护性。

2. **检查数据库支持**：始终检查您的数据库是否支持您想要使用的CTE功能。

3. **使用有意义的名称**：给您的CTEs起描述性的名称，反映其用途。

4. **考虑性能**：CTEs可以提高查询可读性，但并不总是能提高性能。根据需要进行测试和优化。

5. **限制递归深度**：对于递归CTEs，始终包含一个条件来限制递归深度，以防止无限循环。

## 结论

公共表表达式提供了一种强大的方式，以更易读和易维护的格式构建复杂查询。ActiveRecord对CTE的支持使得在Python应用程序中利用这一SQL功能变得容易，特别是对于层次数据查询和复杂的多步操作。