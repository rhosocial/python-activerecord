# ActiveRecord 字段代理（FieldProxy）完整实现指南

## 1. 概述

字段代理（FieldProxy）是一个强大的功能，允许用户通过 `Model.proxy_name.field_name` 语法访问模型字段，并生成对应的 SQL 表达式对象。该功能支持：

- 普通字段访问
- UseColumn 注解字段
- 动态表别名
- 预设表别名
- 列别名
- 自连接查询

## 2. 实现原理

### 2.1 核心实现

字段代理通过 Python 的描述符协议实现：

```python
from typing import ClassVar, TYPE_CHECKING
from ..backend.expression.core import Column

if TYPE_CHECKING:
    from ..backend.dialect.base import SQLDialectBase
    from ..model import ActiveRecord


# 为 Column 类添加别名方法
def _as_(self, alias: str):
    """Set column alias"""
    self.alias = alias
    return self


# 将 as_ 方法附加到 Column 类
Column.as_ = _as_


class FieldProxy:
    """Field proxy descriptor for accessing fields via Model.proxy_name.field_name syntax"""

    def __init__(self, table_alias: str = None):
        """
        Initialize field proxy
        :param table_alias: Optional table alias, if provided all columns from this proxy will use this table alias
        """
        self._table_alias = table_alias

    def __get__(self, instance, owner):
        # 返回一个动态字段访问器
        class _FieldAccessor:
            def __init__(self, model_class: 'ActiveRecord', static_table_alias: str = None):
                self._model_class = model_class
                self._table_alias = static_table_alias  # 可能是初始化时设置的别名

            def with_table_alias(self, alias: str):
                """Set table alias"""
                new_accessor = _FieldAccessor(self._model_class, alias)
                return new_accessor

            def __getattr__(self, field_name: str):
                # 使用 Pydantic 的 model_fields 来获取字段信息
                if field_name not in self._model_class.model_fields:
                    raise AttributeError(f"Field '{field_name}' does not exist on model '{self._model_class.__name__}'")

                # 使用 ColumnNameMixin 的方法来获取正确的列名
                # 这正确处理 UseColumn 注解，如果字段有 UseColumn 则返回自定义列名，否则返回字段名
                column_name = self._model_class._get_column_name(field_name)

                # 使用表别名（如果设置了的话）作为表名
                table_name = self._table_alias if self._table_alias else self._model_class.table_name()

                # 创建列表达式对象，使用真实的方言
                backend = self._model_class.backend()
                dialect: 'SQLDialectBase' = backend.backend
                return Column(dialect, column_name, table=table_name)

        return _FieldAccessor(owner, self._table_alias)
```

### 2.2 使用方式

```python
from pydantic import Field
from typing import ClassVar, Optional
from typing_extensions import Annotated
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.base.fields import UseColumn

class User(ActiveRecord):
    __table_name__: ClassVar[str] = "users"
    __primary_key__: ClassVar[str] = "id"  # 显式指定主键列名
    
    # 普通字段 - 字段名和列名相同
    id: Optional[int] = Field(default=None, json_schema_extra={'primary_key': True})
    name: str
    age: int
    email: str
    
    # UseColumn 注解字段 - 字段名和列名不同
    user_id: Annotated[Optional[int], UseColumn("id")] = Field(default=None, json_schema_extra={'primary_key': True})
    user_name: Annotated[str, UseColumn("name")]
    user_age: Annotated[int, UseColumn("age")]
    user_email: Annotated[str, UseColumn("email")]
    
    # 普通字段代理 - 使用默认表名
    c: ClassVar[FieldProxy] = FieldProxy()
    fields: ClassVar[FieldProxy] = FieldProxy()
    cols: ClassVar[FieldProxy] = FieldProxy()
    
    # 预设表别名的字段代理 - 用于自连接查询
    u1: ClassVar[FieldProxy] = FieldProxy(table_alias='u1')  # 第一个表别名
    u2: ClassVar[FieldProxy] = FieldProxy(table_alias='u2')  # 第二个表别名
    referrer: ClassVar[FieldProxy] = FieldProxy(table_alias='r')  # 推荐人表别名
    referred: ClassVar[FieldProxy] = FieldProxy(table_alias='ref')  # 被推荐人表别名
```

## 3. 功能特性

### 3.1 基本字段访问

```python
# 普通字段访问
User.query().where(User.c.age > 25)
User.query().where((User.fields.status == 'active') & (User.fields.age > 18))
User.query().select(User.cols.id, User.cols.name, User.cols.email)
```

### 3.2 UseColumn 注解字段访问

```python
# UseColumn 注解字段访问
User.query().where(User.c.user_age > 30)  # 映射到 'age' 列
```

### 3.3 列别名

```python
# 列别名
User.query().select(User.c.name.as_('user_name'))
```

### 3.4 动态表别名（自连接查询）

```python
# 动态表别名（自连接查询）
user1 = User.c.with_table_alias('u1')
user2 = User.c.with_table_alias('u2')
User.query().where((user1.age == user2.age) & (user1.id != user2.id))
```

### 3.5 预设表别名（自连接查询）

```python
# 预设表别名（自连接查询）
User.query().where((User.u1.age == User.u2.age) & (User.u1.id != User.u2.id))
```

### 3.6 混合使用

```python
# 混合使用
User.query().select(
    User.u1.name.as_('user1_name'),
    User.u2.name.as_('user2_name')
).where(User.u1.age > User.u2.age)
```

## 4. 扩展应用

### 4.1 高级查询构建

```python
# 复杂条件构建
User.query().where(
    (User.c.age > 18) & 
    (User.c.status == 'active') & 
    (User.c.created_at > datetime.now() - timedelta(days=30))
)

# 聚合函数支持
User.query().select(
    User.c.department,
    User.c.salary.avg().as_('avg_salary'),
    User.c.id.count().as_('employee_count')
).group_by(User.c.department)
```

### 4.2 关系查询增强

```python
# 关联查询
User.query().join(Order).where(Order.c.total > User.c.salary)

# 嵌套关系查询
User.query().join(Order).join(Product).where(
    (User.c.age > 25) & 
    (Product.c.category == 'electronics')
)
```

### 4.3 数据验证和类型安全

```python
# 由于字段代理直接关联模型字段，IDE可以提供完整的类型提示
# 错误的字段名会在开发时被发现
User.query().where(User.c.non_existent_field == 'value')  # IDE会提示错误
```

### 4.4 动态查询构建

```python
# 条件查询构建
def build_user_query(filters):
    query = User.query()
    if 'min_age' in filters:
        query = query.where(User.c.age >= filters['min_age'])
    if 'status' in filters:
        query = query.where(User.c.status == filters['status'])
    return query

# 动态字段选择
def select_fields(model, field_names):
    fields = [getattr(model.c, name) for name in field_names]
    return model.query().select(*fields)
```

### 4.5 高级SQL功能支持

```python
# 窗口函数
User.query().select(
    User.c.name,
    User.c.salary.rank().over(
        partition_by=[User.c.department],
        order_by=[User.c.salary.desc()]
    ).as_('salary_rank')
)

# CTE（公共表表达式）
with_recursive_users = User.query().where(User.c.manager_id.is_null()).union_all(
    User.query().join(with_recursive_users).where(
        User.c.manager_id == with_recursive_users.c.id
    )
)
```

### 4.6 数据转换和计算

```python
# 字段计算
User.query().select(
    User.c.name,
    (User.c.salary * 12).as_('annual_salary'),
    (User.c.age > 18).as_('is_adult')
)

# 字符串操作
User.query().select(
    User.c.name.upper().as_('uppercase_name'),
    User.c.email.contains('@gmail.com').as_('is_gmail_user')
)
```

## 5. 安全性和性能

### 5.1 SQL注入防护

```python
# 字段代理确保所有查询参数都经过适当的参数化处理
User.query().where(User.c.name == user_input)  # 自动参数化，防止SQL注入
```

### 5.2 字段级权限控制

```python
# 字段代理可以集成权限控制
if user.has_permission('view_salary'):
    query = User.query().select(User.c.salary)
else:
    query = User.query().select(User.c.name, User.c.email)  # 排除敏感字段
```

## 6. 总结

字段代理（FieldProxy）实现为ActiveRecord模式提供了强大而灵活的查询构建能力。通过简单的语法，用户可以：

- 访问模型字段并生成SQL表达式
- 使用列别名和表别名
- 构建复杂的自连接查询
- 获得类型安全和IDE支持
- 实现高级SQL功能

该实现完全集成到现有的activerecord架构中，与表达式-方言系统完全兼容，为用户提供了直观、安全和功能丰富的查询构建体验。
