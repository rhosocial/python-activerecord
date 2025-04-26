# 统计查询

rhosocial ActiveRecord提供了直接在数据库查询中执行统计分析的能力。本文档介绍如何使用聚合函数和表达式来执行各种统计计算。

## 基本统计函数

大多数数据库支持一组可用于聚合查询的基本统计函数：

```python
# 产品价格的基本统计
product_stats = Product.query()\
    .select(
        'COUNT(price) as count',
        'AVG(price) as mean',
        'MIN(price) as minimum',
        'MAX(price) as maximum',
        'SUM(price) as sum',
        'MAX(price) - MIN(price) as range'
    )\
    .aggregate()

# 按类别统计
category_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .select(
        'COUNT(price) as count',
        'AVG(price) as mean',
        'MIN(price) as minimum',
        'MAX(price) as maximum',
        'SUM(price) as sum',
        'MAX(price) - MIN(price) as range'
    )\
    .aggregate()
```

## 方差和标准差

许多数据库支持方差和标准差计算：

```python
# 计算方差和标准差
from rhosocial.activerecord.query.expression import FunctionExpression

product_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .select_expr(FunctionExpression('STDDEV', 'price', alias='std_dev'))\
    .select_expr(FunctionExpression('VARIANCE', 'price', alias='variance'))\
    .aggregate()
```

数据库特定的函数名称可能有所不同：

- PostgreSQL：`STDDEV`、`STDDEV_POP`、`STDDEV_SAMP`、`VAR_POP`、`VAR_SAMP`
- MySQL/MariaDB：`STD`、`STDDEV`、`STDDEV_POP`、`STDDEV_SAMP`、`VARIANCE`、`VAR_POP`、`VAR_SAMP`
- SQLite：有限的内置支持，但可以使用表达式计算

## 百分位数和分布

对于支持窗口函数的数据库，您可以计算百分位数和分布：

```python
# 使用窗口函数计算中位数（第50个百分位数）
median_price = Product.query()\
    .select('category')\
    .group_by('category')\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.5'),
        partition_by=['category'],
        order_by=['price'],
        alias='median_price'
    )\
    .aggregate()

# 计算各种百分位数
percentiles = Product.query()\
    .select('category')\
    .group_by('category')\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.25'),
        partition_by=['category'],
        order_by=['price'],
        alias='percentile_25'
    )\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.5'),
        partition_by=['category'],
        order_by=['price'],
        alias='percentile_50'
    )\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.75'),
        partition_by=['category'],
        order_by=['price'],
        alias='percentile_75'
    )\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.9'),
        partition_by=['category'],
        order_by=['price'],
        alias='percentile_90'
    )\
    .aggregate()
```

不同数据库的百分位数函数：

- PostgreSQL：`PERCENTILE_CONT`、`PERCENTILE_DISC`
- MySQL/MariaDB：从8.0/10.3版本开始支持窗口函数
- SQLite：从3.25版本开始有限支持窗口函数

## 相关性和回归

一些数据库支持相关性和回归分析：

```python
# 计算价格和评分之间的相关性
from rhosocial.activerecord.query.expression import FunctionExpression

correlation = Product.query()\
    .select('category')\
    .group_by('category')\
    .select_expr(FunctionExpression('CORR', 'price', 'rating', alias='price_rating_correlation'))\
    .aggregate()

# 线性回归
regression = Product.query()\
    .select('category')\
    .group_by('category')\
    .select_expr(FunctionExpression('REGR_SLOPE', 'price', 'rating', alias='slope'))\
    .select_expr(FunctionExpression('REGR_INTERCEPT', 'price', 'rating', alias='intercept'))\
    .select_expr(FunctionExpression('REGR_R2', 'price', 'rating', alias='r_squared'))\
    .aggregate()
```

数据库支持：

- PostgreSQL：完全支持相关性和回归函数
- MySQL/MariaDB：有限支持
- SQLite：不支持内置相关性和回归函数

## 频率分布和直方图

您可以使用CASE表达式和聚合函数创建频率分布和直方图：

```python
# 创建价格范围的频率分布
from rhosocial.activerecord.query.expression import CaseExpression

price_distribution = Product.query()\
    .select_expr(
        CaseExpression()
            .when('price < 10', '"0-9.99"')
            .when('price < 20', '"10-19.99"')
            .when('price < 30', '"20-29.99"')
            .when('price < 40', '"30-39.99"')
            .when('price < 50', '"40-49.99"')
            .else_result('"50+"')
            .as_('price_range')
    )\
    .select('COUNT(*) as count')\
    .group_by('price_range')\
    .order_by('price_range')\
    .all()
```

## 时间序列分析

您可以使用日期/时间函数进行时间序列分析：

```python
# 按月分析销售趋势
monthly_sales = Order.query()\
    .select(
        'EXTRACT(YEAR FROM created_at) as year',
        'EXTRACT(MONTH FROM created_at) as month'
    )\
    .select('SUM(total) as monthly_total')\
    .group_by('year', 'month')\
    .order_by('year', 'month')\
    .all()

# 计算同比增长
from rhosocial.activerecord.query.expression import WindowExpression, FunctionExpression

yoy_growth = Order.query()\
    .select(
        'EXTRACT(YEAR FROM created_at) as year',
        'EXTRACT(MONTH FROM created_at) as month',
        'SUM(total) as monthly_total'
    )\
    .group_by('year', 'month')\
    .window(
        FunctionExpression('LAG', 'monthly_total', '12'),
        partition_by=[],
        order_by=['year', 'month'],
        alias='prev_year_total'
    )\
    .select_expr(
        ArithmeticExpression(
            ArithmeticExpression('monthly_total', '-', 'prev_year_total'),
            '/',
            'prev_year_total',
            'yoy_growth'
        )
    )\
    .order_by('year', 'month')\
    .all()
```

## 描述性统计摘要

您可以组合多个统计函数来创建描述性统计摘要：

```python
# 创建完整的描述性统计摘要
descriptive_stats = Product.query()\
    .select('category')\
    .group_by('category')\
    .select(
        'COUNT(price) as count',
        'AVG(price) as mean',
        'MIN(price) as minimum',
        'MAX(price) as maximum',
        'SUM(price) as sum',
        'MAX(price) - MIN(price) as range'
    )\
    .select_expr(FunctionExpression('STDDEV', 'price', alias='std_dev'))\
    .select_expr(FunctionExpression('VARIANCE', 'price', alias='variance'))\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.25'),
        partition_by=['category'],
        order_by=['price'],
        alias='q1'
    )\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.5'),
        partition_by=['category'],
        order_by=['price'],
        alias='median'
    )\
    .window(
        FunctionExpression('PERCENTILE_CONT', '0.75'),
        partition_by=['category'],
        order_by=['price'],
        alias='q3'
    )\
    .select_expr(
        ArithmeticExpression('q3', '-', 'q1', 'iqr')
    )\
    .order_by('category')\
    .all()
```

## 高级统计技术

对于更高级的统计分析，您可能需要结合使用数据库查询和专门的Python统计库：

```python
# 从数据库获取原始数据
product_data = Product.query()\
    .select('category', 'price', 'rating')\
    .all()

# 使用pandas和scipy进行高级分析
import pandas as pd
import scipy.stats as stats

# 转换为pandas DataFrame
df = pd.DataFrame(product_data)

# 按类别分组并应用高级统计
by_category = df.groupby('category')
advanced_stats = by_category.apply(lambda x: pd.Series({
    'skewness': stats.skew(x['price']),
    'kurtosis': stats.kurtosis(x['price']),
    'shapiro_test_p': stats.shapiro(x['price'])[1],  # 正态性检验
    'price_rating_corr': x['price'].corr(x['rating']),
    'spearman_corr': stats.spearmanr(x['price'], x['rating'])[0]
}))
```

## 数据库兼容性

统计函数的支持因数据库而异：

- **PostgreSQL**：提供最全面的统计函数支持，包括高级窗口函数、百分位数和回归分析
- **MySQL/MariaDB**：在较新版本中支持大多数基本统计函数和窗口函数
- **SQLite**：支持基本聚合函数，在较新版本中有限支持窗口函数

## 最佳实践

使用统计查询时的一些最佳实践：

1. **考虑性能**：复杂的统计查询可能很昂贵，特别是在大型数据集上。考虑使用索引、物化视图或预计算统计信息。

2. **处理NULL值**：统计函数通常以特定方式处理NULL值。确保您了解每个函数的NULL处理行为。

3. **数据库与应用程序计算**：对于简单的统计，在数据库中计算通常更高效。对于复杂的统计，可能需要在应用程序中使用专门的库。

4. **验证结果**：不同的数据库可能对相同的统计函数有略微不同的实现。始终验证结果的准确性。

5. **考虑样本大小**：在解释统计结果时，考虑样本大小和数据分布。

## 结论

rhosocial ActiveRecord的统计查询功能使您能够直接在数据库中执行强大的数据分析，减少数据传输并提高性能。通过结合数据库的统计能力和Python的数据科学生态系统，您可以创建强大的分析解决方案。