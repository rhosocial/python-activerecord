# Having子句

HAVING子句用于根据聚合条件过滤聚合查询中的组。虽然WHERE子句在分组之前过滤行，但HAVING子句在执行聚合后过滤组。rhosocial ActiveRecord为使用HAVING子句提供了一个简洁的API。

## 基本用法

`having()`方法允许您指定在聚合后应用于组的条件：

```python
# 查找拥有超过5名员工的部门
large_departments = Employee.query()\
    .select('department')\
    .group_by('department')\
    .count('id', 'employee_count')\
    .having('COUNT(id) > ?', (5,))\
    .aggregate()

# 查找平均价格大于100的产品类别
expensive_categories = Product.query()\
    .select('category')\
    .group_by('category')\
    .avg('price', 'avg_price')\
    .having('AVG(price) > ?', (100,))\
    .aggregate()
```

## 参数化HAVING条件

与WHERE子句一样，HAVING子句支持参数化查询以防止SQL注入：

```python
# 查找消费超过特定金额的客户
big_spenders = Order.query()\
    .select('customer_id')\
    .group_by('customer_id')\
    .sum('amount', 'total_spent')\
    .having('SUM(amount) > ?', (1000,))\
    .aggregate()
```

## 多个HAVING条件

您可以链接多个`having()`调用，以使用AND逻辑应用多个条件：

```python
# 查找拥有许多商品且平均价格高的产品类别
premium_categories = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .avg('price', 'avg_price')\
    .having('COUNT(id) > ?', (10,))\
    .having('AVG(price) > ?', (50,))\
    .aggregate()
```

## 在HAVING中使用聚合函数

HAVING子句通常包括聚合函数，以基于组属性进行过滤：

```python
# HAVING中的常见聚合函数
results = Order.query()\
    .select('customer_id')\
    .group_by('customer_id')\
    .count('id', 'order_count')\
    .sum('amount', 'total_amount')\
    .avg('amount', 'avg_amount')\
    .having('COUNT(id) > ?', (5,))  # 超过5个订单\
    .having('SUM(amount) > ?', (1000,))  # 总消费超过1000\
    .having('AVG(amount) > ?', (200,))  # 平均订单超过200\
    .aggregate()
```

## HAVING中的列引用

需要注意的是，HAVING子句应该引用原始列表达式，而不是别名。这遵循SQL标准行为：

```python
# 错误：在HAVING中使用别名
user_stats = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id', 'user_count')\
    .having('user_count > ?', (10,))  # 这将失败！\
    .aggregate()

# 正确：在HAVING中使用聚合函数
user_stats = User.query()\
    .select('status')\
    .group_by('status')\
    .count('id', 'user_count')\
    .having('COUNT(id) > ?', (10,))  # 这样可以工作\
    .aggregate()
```

如果rhosocial ActiveRecord检测到HAVING子句中可能使用了别名，它会发出警告。

## 结合WHERE和HAVING

您可以在同一查询中同时使用WHERE和HAVING，用于不同的过滤目的：

```python
# WHERE在分组前过滤行，HAVING在聚合后过滤组
results = Order.query()\
    .where('status = ?', ('completed',))  # 只包括已完成的订单\
    .select('customer_id')\
    .group_by('customer_id')\
    .count('id', 'order_count')\
    .sum('amount', 'total_amount')\
    .having('COUNT(id) > ?', (3,))  # 拥有超过3个已完成订单的客户\
    .having('SUM(amount) > ?', (500,))  # 消费超过500的客户\
    .aggregate()
```

## 复杂HAVING条件

您可以在HAVING子句中使用复杂条件，包括多个聚合函数和逻辑运算符：

```python
# 带有多个条件的复杂HAVING
results = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .avg('price', 'avg_price')\
    .having('COUNT(id) > 10 AND AVG(price) > 50')\
    .aggregate()

# 在HAVING中使用OR
results = Customer.query()\
    .select('country')\
    .group_by('country')\
    .count('id', 'customer_count')\
    .sum('lifetime_value', 'total_value')\
    .having('COUNT(id) > 1000 OR SUM(lifetime_value) > 1000000')\
    .aggregate()
```

## HAVING与JOIN

HAVING子句与JOIN一起使用效果很好，可用于复杂的聚合查询：

```python
# 查找订购了特定产品的客户
results = Order.query()\
    .join('JOIN order_items ON orders.id = order_items.order_id')\
    .join('JOIN products ON order_items.product_id = products.id')\
    .where('products.category = ?', ('electronics',))\
    .select('orders.customer_id')\
    .group_by('orders.customer_id')\
    .count('DISTINCT products.id', 'unique_products')\
    .having('COUNT(DISTINCT products.id) > ?', (3,))  # 订购了超过3种不同电子产品的客户\
    .aggregate()
```

## 性能考虑

- HAVING子句在分组和聚合之后应用，这可能会消耗大量资源
- 尽可能使用WHERE在分组之前过滤行
- 只对必须在聚合后应用的条件使用HAVING
- 复杂的HAVING条件可能会影响查询性能，特别是在大型数据集上

## 数据库兼容性

HAVING子句被所有主要数据库后端支持，但可能存在细微的行为差异：

- 某些数据库可能允许在HAVING子句中引用别名（非标准SQL）
- HAVING子句中的函数可用性可能因数据库而异

rhosocial ActiveRecord遵循SQL标准行为，其中HAVING子句应该使用聚合函数或GROUP BY子句中的列，而不是SELECT子句中的别名。