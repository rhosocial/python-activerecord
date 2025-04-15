# 原生SQL集成

本文档说明如何在需要更多控制或特定数据库功能时将原生SQL查询与ActiveRecord集成。

## 介绍

虽然ActiveRecord的查询构建器为大多数数据库操作提供了全面的接口，但在某些情况下，您可能需要使用原生SQL：

- 难以用查询构建器表达的复杂查询
- ActiveRecord不直接支持的数据库特定功能
- 关键查询的性能优化
- 需要与ActiveRecord模型集成的遗留SQL

ActiveRecord提供了几种将原生SQL集成到应用程序中的方法，同时仍然受益于ORM的功能。

## 在Where条件中使用原生SQL

使用原生SQL的最简单方法是在标准查询方法中：

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    __table_name__ = 'products'

# 在WHERE子句中使用原生SQL
products = Product.query().where('price > 100 AND category_id IN (1, 2, 3)').all()

# 使用带参数的原生SQL以确保安全
min_price = 100
categories = [1, 2, 3]
products = Product.query().where(
    'price > ? AND category_id IN (?, ?, ?)', 
    min_price, *categories
).all()
```

## 连接中的原生SQL

您可以在连接子句中使用原生SQL来实现更复杂的连接条件：

```python
# 使用原生SQL的复杂连接
results = Product.query()\
    .join('JOIN categories ON products.category_id = categories.id')\
    .join('LEFT JOIN inventory ON products.id = inventory.product_id')\
    .where('categories.active = ? AND inventory.stock > ?', True, 0)\
    .all()
```

## 执行原生SQL查询

为了完全控制，您可以直接执行原生SQL查询：

```python
# 执行原生SQL查询
sql = """
    SELECT p.*, c.name as category_name 
    FROM products p
    JOIN categories c ON p.category_id = c.id
    WHERE p.price > ? AND c.active = ?
    ORDER BY p.created_at DESC
    LIMIT 10
"""

results = Product.query().execute_raw(sql, 100, True)
```

`execute_raw`方法执行SQL并在可能的情况下将结果作为模型实例返回。

## 用于特定数据库功能的原生SQL

原生SQL对于数据库特定功能特别有用：

```python
# PostgreSQL特定的全文搜索
sql = """
    SELECT * FROM products
    WHERE to_tsvector('english', name || ' ' || description) @@ to_tsquery('english', ?)
    ORDER BY ts_rank(to_tsvector('english', name || ' ' || description), to_tsquery('english', ?)) DESC
"""

search_term = 'wireless headphones'
results = Product.query().execute_raw(sql, search_term, search_term)
```

## 将原生SQL与查询构建器结合

您可以将原生SQL与查询构建器结合以获得最大的灵活性：

```python
# 从查询构建器开始
query = Product.query()
    .select('products.*', 'categories.name AS category_name')
    .join('JOIN categories ON products.category_id = categories.id')

# 为复杂条件添加原生SQL
if complex_search_needed:
    query = query.where('EXISTS (SELECT 1 FROM product_tags pt JOIN tags t ON pt.tag_id = t.id WHERE pt.product_id = products.id AND t.name IN (?, ?))', 'featured', 'sale')

# 继续使用查询构建器
results = query.order_by('products.created_at DESC').limit(20).all()
```

## 使用原生SQL进行子查询

原生SQL对于复杂子查询很有用：

```python
# 查找至少有3条评论且平均评分高于4的产品
sql = """
    SELECT p.* FROM products p
    WHERE (
        SELECT COUNT(*) FROM reviews r 
        WHERE r.product_id = p.id
    ) >= 3
    AND (
        SELECT AVG(rating) FROM reviews r 
        WHERE r.product_id = p.id
    ) > 4
"""

highly_rated_products = Product.query().execute_raw(sql)
```

## 最佳实践

1. **使用参数**：始终使用带占位符（`?`）的参数化查询，而不是字符串连接，以防止SQL注入。

2. **隔离原生SQL**：将原生SQL保存在专用方法或类中，以提高可维护性。

3. **记录复杂查询**：添加注释解释复杂原生SQL查询的目的和逻辑。

4. **考虑查询可重用性**：对于经常使用的原生SQL，创建辅助方法或自定义查询类。

5. **彻底测试**：原生SQL绕过了ActiveRecord的一些保障措施，因此要在不同的数据库系统上仔细测试。

6. **监控性能**：原生SQL可以更高效，但如果不仔细设计，也可能引入性能问题。

## 安全考虑

使用原生SQL时，安全成为您的责任：

```python
# 不安全 - 容易受到SQL注入攻击
user_input = request.args.get('sort_column')
unsafe_query = f"SELECT * FROM products ORDER BY {user_input}"  # 永远不要这样做

# 安全 - 使用白名单方法
allowed_columns = {'name', 'price', 'created_at'}
user_input = request.args.get('sort_column')

if user_input in allowed_columns:
    # 安全，因为我们根据白名单进行了验证
    products = Product.query().order_by(user_input).all()
else:
    # 默认安全排序
    products = Product.query().order_by('name').all()
```

## 结论

原生SQL集成提供了一个逃生舱，当ActiveRecord的查询构建器不足以满足您的需求时可以使用。通过将原生SQL的强大功能与ActiveRecord的ORM功能相结合，您可以构建复杂的数据库交互，同时仍然保持使用模型对象的好处。