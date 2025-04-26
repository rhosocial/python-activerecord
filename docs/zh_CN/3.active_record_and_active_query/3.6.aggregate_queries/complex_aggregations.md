# 复杂聚合

rhosocial ActiveRecord提供了强大的功能，用于构建超越基本分组和简单聚合函数的复杂聚合查询。本文档探讨了高级聚合技术，使您能够解决复杂的数据分析问题。

## 组合多个聚合函数

聚合查询最强大的特性之一是能够在单个查询中组合多个聚合函数：

```python
# 按类别的全面产品统计
category_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .count('id', 'product_count')\
    .sum('stock', 'total_stock')\
    .avg('price', 'avg_price')\
    .min('price', 'min_price')\
    .max('price', 'max_price')\
    .aggregate()

# 结果：
# [
#   {
#     'category': 'Electronics',
#     'product_count': 42,
#     'total_stock': 1250,
#     'avg_price': 299.99,
#     'min_price': 19.99,
#     'max_price': 1999.99
#   },
#   ...
# ]
```

这种方法比运行多个单独的查询要高效得多，因为它只需要一次数据库往返。

## 条件聚合

您可以在聚合函数中使用CASE表达式来执行条件聚合：

```python
# 按状态计算订单数量
order_stats = Order.query()\
    .select(
        'COUNT(CASE WHEN status = "pending" THEN 1 END) as pending_count',
        'COUNT(CASE WHEN status = "processing" THEN 1 END) as processing_count',
        'COUNT(CASE WHEN status = "shipped" THEN 1 END) as shipped_count',
        'COUNT(CASE WHEN status = "delivered" THEN 1 END) as delivered_count',
        'COUNT(CASE WHEN status = "cancelled" THEN 1 END) as cancelled_count'
    )\
    .aggregate()

# 按产品类别计算收入
revenue_by_category = Order.query()\
    .join('JOIN order_items ON orders.id = order_items.order_id')\
    .join('JOIN products ON order_items.product_id = products.id')\
    .select('products.category')\
    .group_by('products.category')\
    .select(
        'SUM(CASE WHEN orders.status = "completed" THEN order_items.price * order_items.quantity ELSE 0 END) as completed_revenue',
        'SUM(CASE WHEN orders.status = "cancelled" THEN order_items.price * order_items.quantity ELSE 0 END) as cancelled_revenue'
    )\
    .aggregate()
```

## 聚合中的子查询

您可以使用子查询创建更复杂的聚合：

```python
# 查找价格高于其类别平均价格的产品
from rhosocial.activerecord.query.expression import SubqueryExpression

# 首先，创建一个计算每个类别平均价格的子查询
avg_price_subquery = Product.query()\
    .select('category', 'AVG(price) as avg_category_price')\
    .group_by('category')

# 然后在主查询中使用它
premium_products = Product.query()\
    .join(f'JOIN ({avg_price_subquery.to_sql()[0]}) as category_avg ON products.category = category_avg.category')\
    .where('products.price > category_avg.avg_category_price')\
    .select('products.*', 'category_avg.avg_category_price')\
    .all()
```

或者，您可以使用SubqueryExpression类处理更复杂的场景：

```python
# 查找员工数量高于平均水平的部门
avg_dept_size = Employee.query().count() / Department.query().count()

large_departments = Department.query()\
    .select('departments.name')\
    .select_expr(SubqueryExpression(
        Employee.query()\
            .select('COUNT(*)')\
            .where('department_id = departments.id'),
        'employee_count'
    ))\
    .having(f'employee_count > {avg_dept_size}')\
    .order_by('employee_count DESC')\
    .aggregate()
```

## 带表达式的聚合函数

您可以在聚合函数中使用表达式进行更复杂的计算：

```python
# 计算加权平均值
weighted_avg = Order.query()\
    .select('SUM(price * quantity) / SUM(quantity) as weighted_avg_price')\
    .aggregate()

# 计算总计的百分比
product_share = Product.query()\
    .select('category')\
    .group_by('category')\
    .select_expr(ArithmeticExpression(
        FunctionExpression('SUM', 'price * stock'),
        '/',
        SubqueryExpression(Product.query().select('SUM(price * stock)')),
        'revenue_share'
    ))\
    .select('SUM(price * stock) * 100.0 / (SELECT SUM(price * stock) FROM products) as percentage')\
    .aggregate()
```

## 多级聚合

您可以通过组合子查询创建多级聚合：

```python
# 第一级：按产品计算月度销售
monthly_product_sales = Order.query()\
    .join('JOIN order_items ON orders.id = order_items.order_id')\
    .select(
        'EXTRACT(YEAR FROM orders.created_at) as year',
        'EXTRACT(MONTH FROM orders.created_at) as month',
        'order_items.product_id',
        'SUM(order_items.quantity) as units_sold',
        'SUM(order_items.price * order_items.quantity) as revenue'
    )\
    .where('orders.status = ?', ('completed',))\
    .group_by(
        'EXTRACT(YEAR FROM orders.created_at)',
        'EXTRACT(MONTH FROM orders.created_at)',
        'order_items.product_id'
    )

# 第二级：查找每月销量最高的产品
top_products_by_month = f"""
    SELECT year, month, product_id, units_sold, revenue
    FROM ({monthly_product_sales.to_sql()[0]}) as monthly_sales
    WHERE (year, month, units_sold) IN (
        SELECT year, month, MAX(units_sold)
        FROM ({monthly_product_sales.to_sql()[0]}) as max_sales
        GROUP BY year, month
    )
    ORDER BY year, month
"""

# 执行原始SQL查询
top_products = Product.query().execute_raw(top_products_by_month)
```

## 数据透视表和交叉表

您可以使用条件聚合创建数据透视表：

```python
# 创建按产品类别和月份的销售数据透视表
pivot_table = Order.query()\
    .join('JOIN order_items ON orders.id = order_items.order_id')\
    .join('JOIN products ON order_items.product_id = products.id')\
    .select('products.category')\
    .group_by('products.category')\
    .select(
        'SUM(CASE WHEN EXTRACT(MONTH FROM orders.created_at) = 1 THEN order_items.price * order_items.quantity ELSE 0 END) as jan_sales',
        'SUM(CASE WHEN EXTRACT(MONTH FROM orders.created_at) = 2 THEN order_items.price * order_items.quantity ELSE 0 END) as feb_sales',
        'SUM(CASE WHEN EXTRACT(MONTH FROM orders.created_at) = 3 THEN order_items.price * order_items.quantity ELSE 0 END) as mar_sales',
        # ... 其他月份依此类推
    )\
    .aggregate()
```

## 层次聚合

对于支持它的数据库，您可以使用ROLLUP进行层次聚合：

```python
# 按年、月和日的销售报告，带小计
sales_report = Order.query()\
    .select(
        'EXTRACT(YEAR FROM created_at) as year',
        'EXTRACT(MONTH FROM created_at) as month',
        'EXTRACT(DAY FROM created_at) as day',
        'SUM(amount) as total_sales'
    )\
    .rollup(
        'EXTRACT(YEAR FROM created_at)',
        'EXTRACT(MONTH FROM created_at)',
        'EXTRACT(DAY FROM created_at)'
    )\
    .aggregate()

# 这将包括以下行：
# - 每个特定日期
# - 月度小计（day为NULL）
# - 年度小计（month和day都为NULL）
# - 总计（year、month和day都为NULL）
```

## 性能考虑

- 复杂聚合可能会消耗大量资源，特别是在大型数据集上
- 在JOIN、WHERE和GROUP BY子句中使用的列上使用适当的索引
- 考虑为多步骤聚合实现中间结果
- 使用EXPLAIN测试复杂查询，以了解其执行计划
- 对于非常复杂的聚合，考虑使用数据库特定的功能或存储过程

## 数据库兼容性

复杂聚合支持因数据库而异：

- **PostgreSQL**提供了最全面的复杂聚合支持
- **MySQL/MariaDB**支持大多数功能，但某些表达式可能有限制
- **SQLite**对高级功能的支持更为有限

当使用特定数据库后端不支持的功能时，rhosocial ActiveRecord将引发适当的异常。