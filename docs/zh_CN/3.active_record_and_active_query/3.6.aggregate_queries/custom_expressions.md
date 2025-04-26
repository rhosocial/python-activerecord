# 自定义表达式

rhosocial ActiveRecord提供了一个强大的表达式系统，允许您为查询构建复杂的SQL表达式。这些表达式可以用于SELECT子句、WHERE条件、HAVING子句以及查询的其他部分。

## 表达式类型

rhosocial ActiveRecord中提供了以下表达式类型：

| 表达式类型 | 描述 | 类 |
|-----------------|-------------|-------|
| 算术 | 数学运算 | `ArithmeticExpression` |
| 函数 | SQL函数调用 | `FunctionExpression` |
| Case | 条件逻辑 | `CaseExpression` |
| 条件 | COALESCE、NULLIF等 | `ConditionalExpression` |
| 子查询 | 嵌套查询 | `SubqueryExpression` |
| 分组集合 | CUBE、ROLLUP、GROUPING SETS | `GroupingSetExpression` |
| JSON | JSON操作 | `JsonExpression` |
| 窗口 | 窗口函数 | `WindowExpression` |
| 聚合 | 聚合函数 | `AggregateExpression` |

## 算术表达式

算术表达式允许您在查询中执行数学运算：

```python
from rhosocial.activerecord.query.expression import ArithmeticExpression

# 计算利润率
product_margins = Product.query()\
    .select('id', 'name', 'price', 'cost')\
    .select_expr(
        ArithmeticExpression(
            ArithmeticExpression('price', '-', 'cost'),
            '/',
            'price',
            'profit_margin'
        )
    )\
    .select_expr(
        ArithmeticExpression(
            ArithmeticExpression('price', '-', 'cost'),
            '*',
            '100',
            'profit_percentage'
        )
    )\
    .all()

# 计算总价值
inventory_value = Product.query()\
    .select('id', 'name')\
    .select_expr(
        ArithmeticExpression('price', '*', 'stock', 'inventory_value')
    )\
    .all()
```

支持的运算符包括`+`、`-`、`*`、`/`和`%`（取模）。

## 函数表达式

函数表达式允许您调用SQL函数：

```python
from rhosocial.activerecord.query.expression import FunctionExpression

# 字符串函数
user_data = User.query()\
    .select('id')\
    .select_expr(FunctionExpression('UPPER', 'name', alias='upper_name'))\
    .select_expr(FunctionExpression('LOWER', 'email', alias='lower_email'))\
    .select_expr(FunctionExpression('LENGTH', 'name', alias='name_length'))\
    .all()

# 日期函数
order_dates = Order.query()\
    .select('id')\
    .select_expr(FunctionExpression('YEAR', 'created_at', alias='year'))\
    .select_expr(FunctionExpression('MONTH', 'created_at', alias='month'))\
    .select_expr(FunctionExpression('DAY', 'created_at', alias='day'))\
    .all()

# 数学函数
product_stats = Product.query()\
    .select('id', 'name', 'price')\
    .select_expr(FunctionExpression('ROUND', 'price', '2', alias='rounded_price'))\
    .select_expr(FunctionExpression('CEIL', 'price', alias='ceiling_price'))\
    .select_expr(FunctionExpression('FLOOR', 'price', alias='floor_price'))\
    .all()
```

函数表达式可以嵌套并与其他表达式组合。

## CASE表达式

CASE表达式允许您在查询中实现条件逻辑：

```python
from rhosocial.activerecord.query.expression import CaseExpression

# 简单CASE表达式
product_categories = Product.query()\
    .select('id', 'name', 'price')\
    .select_expr(
        CaseExpression()
            .when('price < 10', '"Budget"')
            .when('price < 50', '"Regular"')
            .when('price < 100', '"Premium"')
            .else_result('"Luxury"')
            .as_('category')
    )\
    .all()

# 搜索CASE表达式
user_status = User.query()\
    .select('id', 'name')\
    .select_expr(
        CaseExpression()
            .when('last_login > NOW() - INTERVAL 1 DAY', '"Active"')
            .when('last_login > NOW() - INTERVAL 7 DAY', '"Recent"')
            .when('last_login > NOW() - INTERVAL 30 DAY', '"Inactive"')
            .else_result('"Dormant"')
            .as_('status')
    )\
    .all()

# 嵌套CASE表达式
product_pricing = Product.query()\
    .select('id', 'name', 'price', 'category')\
    .select_expr(
        CaseExpression()
            .when('category = "Electronics"',
                CaseExpression()
                    .when('price < 100', '"Budget Electronics"')
                    .when('price < 500', '"Mid-range Electronics"')
                    .else_result('"High-end Electronics"')
            )
            .when('category = "Clothing"',
                CaseExpression()
                    .when('price < 20', '"Budget Clothing"')
                    .when('price < 50', '"Regular Clothing"')
                    .else_result('"Designer Clothing"')
            )
            .else_result('"Other"')
            .as_('pricing_category')
    )\
    .all()
```

## 条件表达式

条件表达式提供了特殊的SQL条件函数：

```python
from rhosocial.activerecord.query.expression import ConditionalExpression

# COALESCE - 返回第一个非NULL值
user_display = User.query()\
    .select('id')\
    .select_expr(
        ConditionalExpression.coalesce('display_name', 'username', 'email', alias='display')
    )\
    .all()

# NULLIF - 如果两个表达式相等，则返回NULL
zero_as_null = Order.query()\
    .select('id', 'product_id')\
    .select_expr(
        ConditionalExpression.nullif('quantity', '0', alias='quantity_or_null')
    )\
    .all()

# GREATEST - 返回最大值
max_price = Product.query()\
    .select('id', 'name')\
    .select_expr(
        ConditionalExpression.greatest('regular_price', 'sale_price', alias='display_price')
    )\
    .all()

# LEAST - 返回最小值
min_price = Product.query()\
    .select('id', 'name')\
    .select_expr(
        ConditionalExpression.least('regular_price', 'sale_price', alias='display_price')
    )\
    .all()
```

## 子查询表达式

子查询表达式允许您在表达式中嵌入查询：

```python
from rhosocial.activerecord.query.expression import SubqueryExpression

# 使用子查询获取相关数据
product_with_orders = Product.query()\
    .select('id', 'name', 'price')\
    .select_expr(
        SubqueryExpression(
            Order.query()
                .select('COUNT(*)')
                .where('product_id = products.id')
                .limit(1),
            alias='order_count'
        )
    )\
    .all()

# 使用子查询进行过滤
popular_products = Product.query()\
    .select('id', 'name', 'price')\
    .where(
        'id IN',
        SubqueryExpression(
            Order.query()
                .select('product_id')
                .group_by('product_id')
                .having('COUNT(*) > 10')
        )
    )\
    .all()

# 使用子查询进行计算
product_price_comparison = Product.query()\
    .select('id', 'name', 'price')\
    .select_expr(
        ArithmeticExpression(
            'price',
            '/',
            SubqueryExpression(
                Product.query().select('AVG(price)')
            ),
            'price_ratio'
        )
    )\
    .all()
```

## 分组集合表达式

分组集合表达式允许您执行高级分组操作：

```python
from rhosocial.activerecord.query.expression import GroupingSetExpression

# CUBE - 生成所有可能的分组组合
sales_cube = Order.query()\
    .select('product_category', 'region', 'SUM(amount) as total_sales')\
    .group_by_expr(
        GroupingSetExpression.cube(['product_category', 'region'])
    )\
    .order_by('product_category', 'region')\
    .all()

# ROLLUP - 生成层次结构分组
sales_rollup = Order.query()\
    .select('year', 'quarter', 'month', 'SUM(amount) as total_sales')\
    .group_by_expr(
        GroupingSetExpression.rollup(['year', 'quarter', 'month'])
    )\
    .order_by('year', 'quarter', 'month')\
    .all()

# GROUPING SETS - 指定多个分组集
sales_grouping_sets = Order.query()\
    .select('product_category', 'region', 'payment_method', 'SUM(amount) as total_sales')\
    .group_by_expr(
        GroupingSetExpression.grouping_sets([
            ['product_category', 'region'],
            ['product_category', 'payment_method'],
            ['region', 'payment_method']
        ])
    )\
    .order_by('product_category', 'region', 'payment_method')\
    .all()
```

数据库支持：

- PostgreSQL：完全支持CUBE、ROLLUP和GROUPING SETS
- MySQL/MariaDB：从8.0/10.2版本开始支持ROLLUP，不支持CUBE和GROUPING SETS
- SQLite：不支持高级分组集合

## 组合表达式

您可以组合多种表达式类型来创建复杂的查询：

```python
# 组合多种表达式类型
complex_query = Product.query()\
    .select('id', 'name', 'category')\
    .select_expr(
        # 算术表达式
        ArithmeticExpression('price', '*', '1.1', 'price_with_tax')
    )\
    .select_expr(
        # CASE表达式
        CaseExpression()
            .when('price < 20', '"Low"')
            .when('price < 50', '"Medium"')
            .else_result('"High"')
            .as_('price_category')
    )\
    .select_expr(
        # 子查询表达式
        SubqueryExpression(
            Order.query()
                .select('COUNT(*)')
                .where('product_id = products.id'),
            alias='order_count'
        )
    )\
    .select_expr(
        # 函数表达式
        FunctionExpression('CONCAT', 'name', '": "', 'category', alias='display_name')
    )\
    .where(
        # 条件表达式
        'stock > 0'
    )\
    .order_by('category', 'price')\
    .all()
```

## 在聚合查询中使用表达式

表达式在聚合查询中特别有用：

```python
# 在聚合查询中使用表达式
category_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .select(
        'COUNT(*) as product_count',
        'AVG(price) as avg_price',
        'MIN(price) as min_price',
        'MAX(price) as max_price'
    )\
    .select_expr(
        ArithmeticExpression('MAX(price)', '-', 'MIN(price)', 'price_range')
    )\
    .select_expr(
        ArithmeticExpression(
            ArithmeticExpression('MAX(price)', '-', 'MIN(price)'),
            '/',
            'AVG(price)',
            'relative_range'
        )
    )\
    .having('COUNT(*) > 5')\
    .order_by('category')\
    .all()
```

## 数据库兼容性

虽然rhosocial ActiveRecord提供了一个统一的表达式API，但并非所有数据库都支持所有表达式类型：

- **基本表达式**（算术、函数、CASE、条件）在所有支持的数据库中都可用
- **窗口表达式**在PostgreSQL、MySQL 8.0+、MariaDB 10.2+和SQLite 3.25+中可用
- **高级分组集合**（CUBE、ROLLUP、GROUPING SETS）在PostgreSQL中完全支持，在MySQL/MariaDB中部分支持（仅ROLLUP），在SQLite中不支持

rhosocial ActiveRecord会尝试在可能的情况下模拟不支持的功能，但在某些情况下可能会引发异常。

## 最佳实践

使用表达式时的一些最佳实践：

1. **优先使用表达式API**：尽可能使用表达式API而不是原始SQL字符串，以获得更好的类型安全性和数据库兼容性。

2. **考虑性能**：复杂的表达式可能会影响查询性能，特别是在大型数据集上。使用EXPLAIN分析查询计划。

3. **处理NULL值**：表达式中的NULL处理可能会导致意外结果。使用条件表达式（如COALESCE）来处理NULL值。

4. **测试跨数据库兼容性**：如果您的应用程序需要在多个数据库上运行，请测试所有使用的表达式。

5. **组合表达式**：不要害怕组合多种表达式类型来创建复杂的查询。这通常比使用原始SQL更清晰和更可维护。

## 结论

rhosocial ActiveRecord的表达式系统提供了一种强大而灵活的方式来构建复杂的数据库查询。通过使用表达式而不是原始SQL字符串，您可以创建更安全、更可维护和更可移植的代码。