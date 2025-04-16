# 动态查询构建

本文档说明如何使用ActiveRecord的查询构建器接口在运行时动态构建查询。

## 介绍

动态查询构建允许您根据运行时条件、用户输入或应用程序状态以编程方式构建数据库查询。这对于实现灵活的搜索功能、复杂过滤或在运行时不确定确切查询结构的情况特别有用。

## 基本动态查询构建

ActiveRecord的查询构建器设计为通过方法链支持动态构建。您可以从基本查询开始，有条件地添加子句：

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    __table_name__ = 'products'

def search_products(filters):
    """使用动态过滤器搜索产品。"""
    # 从基本查询开始
    query = Product.query()
    
    # 有条件地添加过滤器
    if 'category' in filters:
        query = query.where('category_id = ?', filters['category'])
    
    if 'min_price' in filters:
        query = query.where('price >= ?', filters['min_price'])
    
    if 'max_price' in filters:
        query = query.where('price <= ?', filters['max_price'])
    
    if 'search_term' in filters:
        search_term = f'%{filters["search_term"]}%'
        query = query.where('name LIKE ? OR description LIKE ?', 
                           search_term, search_term)
    
    # 如果指定了排序，则添加排序
    if 'sort_by' in filters:
        direction = 'DESC' if filters.get('sort_desc', False) else 'ASC'
        query = query.order_by(f'{filters["sort_by"]} {direction}')
    
    # 应用分页
    page = int(filters.get('page', 1))
    per_page = int(filters.get('per_page', 20))
    query = query.limit(per_page).offset((page - 1) * per_page)
    
    return query.all()

# 使用示例
results = search_products({
    'category': 5,
    'min_price': 10.00,
    'search_term': 'wireless',
    'sort_by': 'price',
    'sort_desc': True,
    'page': 2
})
```

## 处理动态WHERE条件

对于更复杂的过滤场景，您可能需要动态构建WHERE条件：

```python
def advanced_search(filters):
    query = User.query()
    
    # 动态构建WHERE条件
    where_conditions = []
    params = []
    
    if filters.get('name'):
        where_conditions.append('name LIKE ?')
        params.append(f'%{filters["name"]}%')
    
    if filters.get('status'):
        where_conditions.append('status = ?')
        params.append(filters['status'])
    
    if filters.get('min_age'):
        where_conditions.append('age >= ?')
        params.append(filters['min_age'])
    
    if filters.get('max_age'):
        where_conditions.append('age <= ?')
        params.append(filters['max_age'])
    
    # 如果存在任何条件，则应用所有条件
    if where_conditions:
        # 用AND连接条件
        combined_condition = ' AND '.join(where_conditions)
        query = query.where(combined_condition, *params)
    
    return query.all()
```

## 动态连接和关系

您还可以动态包含连接和关系：

```python
def get_orders(filters, include_relations=None):
    query = Order.query()
    
    # 动态添加连接/关系
    if include_relations:
        for relation in include_relations:
            if relation == 'customer':
                query = query.with_('customer')
            elif relation == 'items':
                query = query.with_('items')
            elif relation == 'items.product':
                query = query.with_('items.product')
    
    # 添加过滤器
    if 'status' in filters:
        query = query.where('status = ?', filters['status'])
    
    if 'date_from' in filters:
        query = query.where('created_at >= ?', filters['date_from'])
    
    if 'date_to' in filters:
        query = query.where('created_at <= ?', filters['date_to'])
    
    return query.all()

# 使用示例
orders = get_orders(
    {'status': 'processing', 'date_from': '2023-01-01'}, 
    include_relations=['customer', 'items.product']
)
```

## 动态字段选择

您可以动态选择要检索的字段：

```python
def get_users(fields=None):
    query = User.query()
    
    if fields:
        # 将字段列表转换为逗号分隔的字符串
        # 并确保正确引用标识符
        query = query.select(*fields)
    
    return query.all()

# 使用示例
users = get_users(fields=['id', 'username', 'email'])
```

## 使用字典构建复杂查询

对于高度动态的查询，您可以使用字典来定义查询结构：

```python
def build_query_from_dict(model_class, query_dict):
    query = model_class.query()
    
    # 应用where条件
    if 'where' in query_dict:
        for condition in query_dict['where']:
            field = condition['field']
            operator = condition.get('operator', '=')
            value = condition['value']
            
            # 处理不同的运算符
            if operator == 'LIKE':
                query = query.where(f'{field} LIKE ?', f'%{value}%')
            elif operator == 'IN':
                placeholders = ', '.join(['?'] * len(value))
                query = query.where(f'{field} IN ({placeholders})', *value)
            else:
                query = query.where(f'{field} {operator} ?', value)
    
    # 应用连接
    if 'joins' in query_dict:
        for join in query_dict['joins']:
            query = query.join(join)
    
    # 应用排序
    if 'order_by' in query_dict:
        for order in query_dict['order_by']:
            field = order['field']
            direction = order.get('direction', 'ASC')
            query = query.order_by(f'{field} {direction}')
    
    # 应用分组
    if 'group_by' in query_dict:
        query = query.group_by(*query_dict['group_by'])
    
    # 应用限制和偏移
    if 'limit' in query_dict:
        query = query.limit(query_dict['limit'])
    
    if 'offset' in query_dict:
        query = query.offset(query_dict['offset'])
    
    return query

# 使用示例
query_definition = {
    'where': [
        {'field': 'status', 'value': 'active'},
        {'field': 'created_at', 'operator': '>=', 'value': '2023-01-01'},
        {'field': 'category_id', 'operator': 'IN', 'value': [1, 2, 3]}
    ],
    'joins': [
        'JOIN categories ON products.category_id = categories.id'
    ],
    'order_by': [
        {'field': 'created_at', 'direction': 'DESC'}
    ],
    'limit': 20,
    'offset': 0
}

results = build_query_from_dict(Product, query_definition).all()
```

## 安全处理用户输入

当从用户输入动态构建查询时，始终要注意安全性：

```python
def safe_search(user_input):
    query = Product.query()
    
    # 允许过滤和排序的字段白名单
    allowed_filter_fields = {'category_id', 'brand_id', 'is_active'}
    allowed_sort_fields = {'price', 'name', 'created_at'}
    
    # 应用过滤器（仅适用于允许的字段）
    for field, value in user_input.get('filters', {}).items():
        if field in allowed_filter_fields:
            query = query.where(f'{field} = ?', value)
    
    # 应用排序（仅适用于允许的字段）
    sort_field = user_input.get('sort_field')
    if sort_field and sort_field in allowed_sort_fields:
        direction = 'DESC' if user_input.get('sort_desc') else 'ASC'
        query = query.order_by(f'{sort_field} {direction}')
    
    return query.all()
```

## 最佳实践

1. **验证输入**：在使用输入构建查询之前，始终验证和清理用户输入。

2. **使用参数化查询**：永远不要直接将值插入SQL字符串；始终使用带占位符的参数化查询。

3. **白名单字段**：当从用户输入接受字段名时，根据允许字段的白名单验证它们。

4. **处理边缘情况**：考虑当过滤器为空或无效时会发生什么。

5. **优化性能**：注意动态查询如何影响性能，特别是对于复杂连接或大型数据集。

6. **彻底测试**：使用各种输入组合测试动态查询构建器，以确保它们生成正确的SQL。

## 结论

动态查询构建是ActiveRecord的一个强大功能，它使您能够创建灵活、适应性强的数据库查询。通过利用查询构建器的方法链接口，您可以根据运行时条件以编程方式构建复杂查询，使您的应用程序对用户需求更加响应，同时保持干净、可维护的代码。