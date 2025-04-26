# 窗口函数

窗口函数是SQL的一个强大特性，它允许您对与当前行相关的一组行执行计算，而不像聚合函数那样将结果折叠成单个行。rhosocial ActiveRecord通过其查询API提供了对窗口函数的全面支持。

## 窗口函数简介

窗口函数通过OVER子句定义的"窗口"对一组行执行计算。它们对于分析查询特别有用，您可以比较每一行与相关行或计算运行总计、移动平均值和排名。

```python
# 基本窗口函数示例：按类别内的价格对产品进行排名
ranked_products = Product.query()\
    .select('id', 'name', 'category', 'price')\
    .window(
        FunctionExpression('RANK'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='price_rank'
    )\
    .order_by('category', 'price_rank')\
    .all()
```

## 窗口函数组件

rhosocial ActiveRecord中的窗口函数由几个组件组成：

1. **基础函数**：要应用的函数（例如，RANK, SUM, AVG）
2. **PARTITION BY**：将行划分为组（可选）
3. **ORDER BY**：确定每个分区内行的顺序（可选）
4. **框架规范**：定义要包含在窗口中的行（可选）

## 支持的窗口函数

rhosocial ActiveRecord支持各种类型的窗口函数：

### 排名函数

```python
# ROW_NUMBER：为每行分配唯一的顺序编号
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('ROW_NUMBER'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='row_num'
    )\
    .all()

# RANK：为并列分配相同的排名，有间隙
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('RANK'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='price_rank'
    )\
    .all()

# DENSE_RANK：为并列分配相同的排名，无间隙
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('DENSE_RANK'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='dense_price_rank'
    )\
    .all()

# NTILE：将行划分为指定数量的组
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('NTILE', '4'),  # 划分为四分位数
        partition_by=['category'],
        order_by=['price DESC'],
        alias='price_quartile'
    )\
    .all()
```

### 聚合窗口函数

```python
# SUM：按日期的销售额运行总计
Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('SUM', 'amount'),
        order_by=['date'],
        alias='running_total'
    )\
    .order_by('date')\
    .all()

# AVG：销售额的移动平均值
Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('AVG', 'amount'),
        order_by=['date'],
        frame_type='ROWS',
        frame_start='6 PRECEDING',
        frame_end='CURRENT ROW',
        alias='moving_avg_7days'
    )\
    .order_by('date')\
    .all()

# COUNT：每个客户的订单计数与运行总计
Order.query()\
    .select('customer_id', 'date', 'amount')\
    .window(
        FunctionExpression('COUNT', '*'),
        partition_by=['customer_id'],
        order_by=['date'],
        alias='order_number'
    )\
    .window(
        FunctionExpression('SUM', 'amount'),
        partition_by=['customer_id'],
        order_by=['date'],
        alias='customer_running_total'
    )\
    .order_by('customer_id', 'date')\
    .all()
```

### 值函数

```python
# FIRST_VALUE：每个类别中的第一个价格
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('FIRST_VALUE', 'price'),
        partition_by=['category'],
        order_by=['price DESC'],
        alias='highest_price'
    )\
    .all()

# LAST_VALUE：每个类别中的最后一个价格
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('LAST_VALUE', 'price'),
        partition_by=['category'],
        order_by=['price DESC'],
        frame_type='ROWS',
        frame_start='UNBOUNDED PRECEDING',
        frame_end='UNBOUNDED FOLLOWING',  # 对LAST_VALUE很重要
        alias='lowest_price'
    )\
    .all()

# LAG：有序序列中的前一个价格
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('LAG', 'price', '1'),  # 偏移1行
        partition_by=['category'],
        order_by=['price DESC'],
        alias='next_lower_price'
    )\
    .all()

# LEAD：有序序列中的下一个价格
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('LEAD', 'price', '1'),  # 偏移1行
        partition_by=['category'],
        order_by=['price DESC'],
        alias='next_higher_price'
    )\
    .all()
```

## 窗口框架规范

窗口框架定义了相对于当前行要包含在窗口中的行：

```python
# 默认框架（RANGE UNBOUNDED PRECEDING AND CURRENT ROW）
Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('SUM', 'amount'),
        order_by=['date'],
        alias='running_total'
    )\
    .all()

# 基于行的框架：包括当前行在内的最后7行
Order.query()\
    .select('date', 'amount')\
    .window(
        FunctionExpression('AVG', 'amount'),
        order_by=['date'],
        frame_type='ROWS',
        frame_start='6 PRECEDING',
        frame_end='CURRENT ROW',
        alias='moving_avg_7days'
    )\
    .all()

# 基于范围的框架：所有具有相同值的行
Employee.query()\
    .select('department', 'salary')\
    .window(
        FunctionExpression('AVG', 'salary'),
        partition_by=['department'],
        order_by=['salary'],
        frame_type='RANGE',
        frame_start='CURRENT ROW',
        frame_end='CURRENT ROW',
        alias='avg_for_same_salary'
    )\
    .all()

# 无界框架：分区中的所有行
Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('AVG', 'price'),
        partition_by=['category'],
        frame_type='ROWS',
        frame_start='UNBOUNDED PRECEDING',
        frame_end='UNBOUNDED FOLLOWING',
        alias='category_avg_price'
    )\
    .all()
```

## 命名窗口

您可以定义命名窗口以在多个窗口函数中重用：

```python
# 定义命名窗口
query = Product.query()\
    .select('category', 'name', 'price')\
    .define_window(
        'category_window',
        partition_by=['category'],
        order_by=['price DESC']
    )

# 在多个函数中使用命名窗口
results = query\
    .window(
        FunctionExpression('ROW_NUMBER'),
        window_name='category_window',
        alias='row_num'
    )\
    .window(
        FunctionExpression('RANK'),
        window_name='category_window',
        alias='price_rank'
    )\
    .window(
        FunctionExpression('PERCENT_RANK'),
        window_name='category_window',
        alias='percent_rank'
    )\
    .all()
```

## 实际示例

### 百分位计算

```python
# 计算每个产品在其类别内的价格百分位排名
product_percentiles = Product.query()\
    .select('category', 'name', 'price')\
    .window(
        FunctionExpression('PERCENT_RANK'),
        partition_by=['category'],
        order_by=['price'],
        alias='price_percentile'
    )\
    .order_by('category', 'price_percentile')\
    .all()
```

### 时间序列分析

```python
# 计算月环比增长率
monthly_sales = Order.query()\
    .select(
        'EXTRACT(YEAR FROM date) as year',
        'EXTRACT(MONTH FROM date) as month',
        'SUM(amount) as monthly_total'
    )\
    .group_by('EXTRACT(YEAR FROM date)', 'EXTRACT(MONTH FROM date)')\
    .order_by('year', 'month')\
    .window(
        FunctionExpression('LAG', 'monthly_total', '1'),
        order_by=['year', 'month'],
        alias='previous_month'
    )\
    .select('(monthly_total - previous_month) / previous_month * 100 as growth_rate')\
    .aggregate()
```

### 累积分布

```python
# 计算薪资的累积分布
salary_distribution = Employee.query()\
    .select('department', 'salary')\
    .window(
        FunctionExpression('CUME_DIST'),
        partition_by=['department'],
        order_by=['salary'],
        alias='salary_percentile'
    )\
    .order_by('department', 'salary')\
    .all()
```

## 数据库兼容性

窗口函数支持因数据库而异：

- **PostgreSQL**：完全支持所有窗口函数和框架规范
- **MySQL**：从8.0+版本开始提供基本支持
- **MariaDB**：从10.2+版本开始提供基本支持
- **SQLite**：从3.25+版本开始提供基本支持

rhosocial ActiveRecord在运行时检查数据库兼容性，并在使用不支持的功能时引发适当的异常：

```python
# 这将在较旧的数据库版本上引发WindowFunctionNotSupportedError
try:
    results = Product.query()\
        .select('category', 'name', 'price')\
        .window(
            FunctionExpression('RANK'),
            partition_by=['category'],
            order_by=['price DESC'],
            alias='price_rank'
        )\
        .all()
except WindowFunctionNotSupportedError as e:
    print(f"窗口函数不支持：{e}")
    # 回退到非窗口实现
```

## 性能考虑

- 窗口函数可能会消耗大量资源，特别是对于大型数据集
- 在PARTITION BY和ORDER BY子句中使用的列上使用适当的索引
- 尽可能限制窗口框架大小（例如，使用ROWS BETWEEN 10 PRECEDING AND CURRENT ROW而不是UNBOUNDED PRECEDING）
- 考虑为复杂的多窗口查询实现中间结果
- 使用EXPLAIN测试窗口函数查询以了解其执行计划