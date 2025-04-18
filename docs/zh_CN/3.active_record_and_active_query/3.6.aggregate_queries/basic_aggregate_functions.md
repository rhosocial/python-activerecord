# 基本聚合函数

rhosocial ActiveRecord提供了一套全面的基本聚合函数，允许您对数据库中的行执行计算。这些函数对于数据分析和报告至关重要。

## 可用的聚合函数

以下基本聚合函数在所有数据库后端中都可用：

| 函数 | 描述 | 方法 |
|----------|-------------|--------|
| COUNT | 计算行数或非NULL值的数量 | `count()` |
| SUM | 计算列中值的总和 | `sum()` |
| AVG | 计算列中值的平均值 | `avg()` |
| MIN | 查找列中的最小值 | `min()` |
| MAX | 查找列中的最大值 | `max()` |

## 使用聚合函数

聚合函数可以通过两种方式使用：

1. **标量模式**：立即执行并返回单个值
2. **聚合查询模式**：与GROUP BY一起添加到查询中，用于更复杂的聚合

### 标量模式

在标量模式下，聚合函数立即执行并返回单个值：

```python
# 计算所有用户数量
total_users = User.query().count()

# 所有订单金额总和
total_amount = Order.query().sum('amount')

# 产品平均价格
avg_price = Product.query().avg('price')

# 最低和最高价格
min_price = Product.query().min('price')
max_price = Product.query().max('price')
```

您可以将聚合函数与WHERE条件结合使用：

```python
# 计算活跃用户数量
active_count = User.query().where('status = ?', (1,)).count()

# 已完成订单的金额总和
completed_total = Order.query()\
    .where('status = ?', ('completed',))\
    .sum('amount')
```

### 使用DISTINCT

`count()`方法支持`distinct`参数，用于只计算不同的值：

```python
# 计算不同类别的数量
category_count = Product.query().count('category', distinct=True)
```

## 聚合查询模式

在聚合查询模式下，您可以将多个聚合函数与GROUP BY子句结合使用：

```python
# 按部门分组并计算统计数据
dept_stats = Employee.query()\
    .select('department')\
    .group_by('department')\
    .count('id', 'employee_count')\
    .sum('salary', 'total_salary')\
    .avg('salary', 'avg_salary')\
    .min('salary', 'min_salary')\
    .max('salary', 'max_salary')\
    .aggregate()

# 结果将是一个字典列表：
# [
#   {'department': 'Engineering', 'employee_count': 42, 'total_salary': 4200000, 'avg_salary': 100000, ...},
#   {'department': 'Marketing', 'employee_count': 18, 'total_salary': 1440000, 'avg_salary': 80000, ...},
#   ...
# ]
```

在聚合查询模式下，查询不会立即执行，直到您调用`aggregate()`方法，该方法将结果作为字典列表返回。

## 结果别名

您可以为聚合结果列提供别名：

```python
# 使用别名
user_stats = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id', 'user_count')\
    .aggregate()

# 不使用别名（默认列名将是函数名）
user_stats = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id')\
    .aggregate()
```

## NULL值处理

聚合函数根据SQL标准行为处理NULL值：

- COUNT(*)包括所有行
- COUNT(column)排除该列中的NULL值
- SUM、AVG、MIN、MAX忽略NULL值
- 如果所有值都是NULL，SUM和AVG返回NULL，而COUNT返回0

```python
# 计算所有行，包括email列中有NULL值的行
total_users = User.query().count()

# 只计算email列非NULL值的行
users_with_email = User.query().count('email')
```

## 与JOIN结合使用

聚合函数可以与JOIN结合使用，用于更复杂的查询：

```python
# 计算每个客户的订单数
customer_orders = Order.query()\
    .join('JOIN customers ON orders.customer_id = customers.id')\
    .select('customers.name')\
    .group_by('customers.name')\
    .count('orders.id', 'order_count')\
    .sum('orders.amount', 'total_spent')\
    .aggregate()
```

## 错误处理

聚合函数优雅地处理错误：

- 如果查询失败，将引发适当的异常
- 对于标量查询，NULL结果在Python中转换为None
- 类型转换根据数据库列类型自动处理

## 性能考虑

- 聚合函数在数据库服务器上执行，而不是在Python中执行
- 对于大型数据集，考虑在GROUP BY子句中使用的列上添加适当的索引
- 在可能的情况下，在聚合之前使用WHERE过滤数据，以减少处理的数据量