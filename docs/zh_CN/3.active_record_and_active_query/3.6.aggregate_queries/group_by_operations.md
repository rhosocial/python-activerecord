# 分组操作

GROUP BY子句是聚合查询的基本组成部分，它允许您在应用聚合函数之前将数据组织成组。rhosocial ActiveRecord为使用GROUP BY操作提供了一个简洁直观的API。

## 基本分组

`group_by()`方法允许您指定一个或多个列来对数据进行分组：

```python
# 按状态对用户分组并计数
user_counts = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id', 'user_count')\
    .aggregate()

# 结果: [{'status': 'active', 'user_count': 42}, {'status': 'inactive', 'user_count': 15}, ...]
```

当您使用`group_by()`时，您还必须在`select()`调用中选择您要分组的列，以便将它们包含在结果中。

## 多列分组

您可以按多个列进行分组，以创建更详细的聚合：

```python
# 按年和月对销售进行分组
monthly_sales = Sale.query()\
    .select('YEAR(date) as year', 'MONTH(date) as month')\
    .group_by('YEAR(date)', 'MONTH(date)')\
    .sum('amount', 'total_sales')\
    .aggregate()

# 按类别和状态对产品进行分组
product_stats = Product.query()\
    .select('category', 'status')\
    .group_by('category', 'status')\
    .count('id', 'product_count')\
    .aggregate()
```

## GROUP BY中的列别名

需要注意的是，GROUP BY应该使用原始列表达式，而不是别名。rhosocial ActiveRecord会自动从GROUP BY列中去除别名并发出警告：

```python
# 这样可以工作但会生成警告
user_stats = User.query()\
    .select('status AS user_status')\
    .group_by('status AS user_status')  # 警告：别名将被去除\
    .count('id', 'count')\
    .aggregate()

# 更好的方法
user_stats = User.query()\
    .select('status AS user_status')\
    .group_by('status')\
    .count('id', 'count')\
    .aggregate()
```

## 使用表限定的列进行分组

在使用JOIN时，重要的是用表名限定您的列，以避免歧义：

```python
# 按客户对订单进行分组
customer_orders = Order.query()\
    .join('JOIN customers ON orders.customer_id = customers.id')\
    .select('customers.id', 'customers.name')\
    .group_by('customers.id', 'customers.name')\
    .count('orders.id', 'order_count')\
    .sum('orders.amount', 'total_amount')\
    .aggregate()
```

## 使用表达式进行分组

您可以按SQL表达式进行分组，而不仅仅是简单的列：

```python
# 按日期部分分组
monthly_stats = Event.query()\
    .select('EXTRACT(YEAR FROM date) as year', 'EXTRACT(MONTH FROM date) as month')\
    .group_by('EXTRACT(YEAR FROM date)', 'EXTRACT(MONTH FROM date)')\
    .count('id', 'event_count')\
    .aggregate()

# 按计算值分组
price_ranges = Product.query()\
    .select('FLOOR(price / 100) * 100 as price_range')\
    .group_by('FLOOR(price / 100) * 100')\
    .count('id', 'product_count')\
    .aggregate()
```

## 分组中NULL值的处理

在SQL中，使用GROUP BY时，NULL值会被分在一起。这种行为在rhosocial ActiveRecord中得到保留：

```python
# 按可选字段对用户分组
user_groups = User.query()\
    .select('department')\
    .group_by('department')\
    .count('id', 'user_count')\
    .aggregate()

# 结果可能包括一个department为None的组
```

如果您想以不同方式处理NULL值，可以在查询中使用COALESCE或IFNULL：

```python
# 将NULL部门替换为'未分配'
user_groups = User.query()\
    .select('COALESCE(department, "未分配") as department')\
    .group_by('COALESCE(department, "未分配")')\
    .count('id', 'user_count')\
    .aggregate()
```

## 高级分组技术

### 结合GROUP BY和HAVING

将GROUP BY与HAVING结合使用，根据聚合结果过滤组：

```python
# 查找拥有超过10名员工的部门
large_departments = Employee.query()\
    .select('department')\
    .group_by('department')\
    .count('id', 'employee_count')\
    .having('COUNT(id) > ?', (10,))\
    .aggregate()
```

### 结合GROUP BY和ORDER BY

您可以使用ORDER BY对分组结果进行排序：

```python
# 按类别分组并按计数降序排序
category_counts = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .order_by('product_count DESC')\
    .aggregate()
```

### 结合GROUP BY和LIMIT

您可以限制返回的组数：

```python
# 获取按产品数量排序的前5个类别
top_categories = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .order_by('product_count DESC')\
    .limit(5)\
    .aggregate()
```

## 性能考虑

- GROUP BY操作在大型数据集上可能会消耗大量资源
- 在GROUP BY子句中使用的列上添加索引以提高性能
- 在分组之前使用WHERE过滤数据，以减少处理的数据量
- 只对必须在分组后应用的条件使用HAVING

## 数据库兼容性

基本的GROUP BY功能被所有数据库后端支持。然而，一些高级分组功能可能会根据数据库有不同的语法或限制：

- **SQLite**：支持基本的GROUP BY操作，但对复杂表达式的支持有限
- **MySQL/MariaDB**：支持带有扩展（如WITH ROLLUP）的GROUP BY
- **PostgreSQL**：提供最全面的GROUP BY支持，包括CUBE和GROUPING SETS

rhosocial ActiveRecord尽可能地抽象这些差异，在不同的数据库后端之间提供一致的API。