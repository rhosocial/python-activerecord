# JSON操作

rhosocial ActiveRecord提供了一套全面的与数据库无关的JSON操作，允许您处理存储在数据库中的JSON数据。这些操作对于处理半结构化数据和灵活模式特别有用。

## 数据库中的JSON支持

不同数据库系统对JSON的支持程度各不相同：

- **PostgreSQL**：广泛的原生JSON和JSONB支持（从9.2+版本开始）
- **MySQL/MariaDB**：良好的JSON支持（从MySQL 5.7+和MariaDB 10.2+开始）
- **SQLite**：通过JSON1扩展提供基本JSON支持（从3.9+版本开始）

rhosocial ActiveRecord抽象了这些差异，在所有支持的数据库中提供一致的API。

## JSON操作方法

以下JSON操作方法在`AggregateQueryMixin`类中可用：

| 方法 | 描述 |
|--------|-------------|
| `json_extract` | 从JSON路径提取值 |
| `json_extract_text` | 从JSON路径提取文本值 |
| `json_contains` | 检查JSON在特定路径是否包含特定值 |
| `json_exists` | 检查JSON路径是否存在 |
| `json_type` | 获取JSON路径处值的类型 |
| `json_length` | 获取JSON数组或对象的长度 |
| `json_keys` | 获取JSON对象的键 |
| `json_remove` | 移除JSON路径处的值 |
| `json_insert` | 如果路径不存在，在JSON路径处插入值 |
| `json_replace` | 如果路径存在，替换JSON路径处的值 |
| `json_set` | 在JSON路径处设置值（插入或替换） |

## 基本JSON提取

最常见的JSON操作是从JSON数据中提取值：

```python
# 从JSON列中提取简单值
user_settings = User.query()\
    .select('id', 'name')\
    .json_extract('settings', '$.theme', 'theme')\
    .json_extract('settings', '$.notifications.email', 'email_notifications')\
    .all()

# 提取为文本（移除JSON字符串的引号）
user_preferences = User.query()\
    .select('id')\
    .json_extract_text('preferences', '$.language', 'language')\
    .all()
```

## 使用JSON条件进行过滤

您可以在WHERE子句中使用JSON操作来过滤数据：

```python
# 查找使用特定主题的用户
dark_theme_users = User.query()\
    .where("JSON_EXTRACT(settings, '$.theme') = ?", ('dark',))\
    .all()

# 使用子查询中的json_extract的替代方法
dark_theme_users = User.query()\
    .select('id', 'name')\
    .json_extract('settings', '$.theme', 'theme')\
    .where('theme = ?', ('dark',))\
    .all()

# 查找启用了电子邮件通知的用户
email_users = User.query()\
    .where("JSON_EXTRACT(settings, '$.notifications.email') = ?", (True,))\
    .all()
```

## 检查JSON包含和存在性

您可以检查JSON数据是否包含特定值或路径是否存在：

```python
# 检查用户是否有特定角色
admins = User.query()\
    .select('id', 'name')\
    .json_contains('roles', '$', 'admin', 'is_admin')\
    .where('is_admin = ?', (1,))\
    .all()

# 检查配置路径是否存在
configured_users = User.query()\
    .select('id', 'name')\
    .json_exists('settings', '$.theme', 'has_theme')\
    .where('has_theme = ?', (1,))\
    .all()
```

## 获取JSON元数据

您可以检索有关JSON值的元数据：

```python
# 获取JSON值的类型
user_data_types = User.query()\
    .select('id', 'name')\
    .json_type('data', '$.preferences', 'pref_type')\
    .json_type('data', '$.roles', 'roles_type')\
    .all()

# 获取JSON数组或对象的长度
user_roles = User.query()\
    .select('id', 'name')\
    .json_length('roles', '$', 'role_count')\
    .all()
```

## 修改JSON数据

您可以使用JSON操作来修改JSON数据：

```python
# 移除JSON路径处的值
user = User.find(1)
user.settings = User.query()\
    .json_remove('settings', '$.old_preference')\
    .scalar()
user.save()

# 插入新值（如果路径不存在）
user.settings = User.query()\
    .json_insert('settings', '$.new_preference', 'value')\
    .scalar()
user.save()

# 替换现有值（如果路径存在）
user.settings = User.query()\
    .json_replace('settings', '$.theme', 'light')\
    .scalar()
user.save()

# 设置值（插入或替换）
user.settings = User.query()\
    .json_set('settings', '$.theme', 'light')\
    .scalar()
user.save()
```

## 在聚合中使用JSON

您可以将JSON操作与聚合函数结合使用：

```python
# 按JSON属性分组
theme_counts = User.query()\
    .json_extract('settings', '$.theme', 'theme')\
    .group_by('theme')\
    .select('theme', 'COUNT(*) as count')\
    .all()

# 聚合JSON数组长度
role_stats = User.query()\
    .select(
        'AVG(JSON_LENGTH(roles, "$")) as avg_roles',
        'MAX(JSON_LENGTH(roles, "$")) as max_roles',
        'MIN(JSON_LENGTH(roles, "$")) as min_roles'
    )\
    .aggregate()
```

## 数据库特定的考虑因素

虽然rhosocial ActiveRecord提供了一个统一的API，但在使用JSON操作时需要考虑一些数据库特定的因素：

### PostgreSQL

- 支持两种JSON类型：`json`（文本存储）和`jsonb`（二进制存储，更高效）
- 提供丰富的JSON操作符和函数
- 支持JSON索引（对于`jsonb`类型）

### MySQL/MariaDB

- 仅支持单一JSON类型
- 提供一组全面的JSON函数
- 支持JSON路径表达式的功能性索引

### SQLite

- 通过JSON1扩展提供JSON支持
- 基本JSON函数集
- 有限的索引支持

## 最佳实践

使用JSON操作时的一些最佳实践：

1. **适当使用JSON**：JSON适用于半结构化数据，但对于频繁查询的结构化数据，使用常规列可能更高效。

2. **考虑索引**：对于经常查询的JSON路径，考虑使用数据库特定的JSON索引功能。

3. **验证JSON数据**：在应用程序级别验证JSON数据，以确保其符合预期的结构。

4. **处理NULL值**：JSON操作通常在处理NULL值时有特定行为，确保您的代码处理这些情况。

5. **了解性能影响**：复杂的JSON操作可能比常规列操作更昂贵，特别是在大型数据集上。

## 结论

rhosocial ActiveRecord的JSON操作提供了一种强大的方式来处理数据库中的半结构化数据。通过提供一个统一的API，它简化了跨不同数据库系统处理JSON数据的复杂性，同时保留了每个系统的强大功能。