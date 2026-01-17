# 字段定义 (Fields & Proxies)

在 `rhosocial-activerecord` 中，字段定义复用了 Pydantic 的语法，同时引入了 `FieldProxy` 来弥合 Python 对象与 SQL 查询之间的鸿沟。

## 基础字段定义

模型字段就是标准的 Python 类型注解，可以使用 `pydantic.Field` 来添加元数据和验证规则。

```python
from typing import Optional
from pydantic import Field
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    is_active: bool = True
    
    @classmethod
    def table_name(cls) -> str:
        return "products"
```

## FieldProxy: 类型安全的查询

传统的 ORM 常常需要使用字符串来引用字段（例如 `filter(name="Alice")`），这容易导致拼写错误且难以重构。
`FieldProxy` 允许你以 Python 表达式的方式构建查询。

### 启用 FieldProxy

在模型中定义一个 `ClassVar`：

```python
from typing import ClassVar
from rhosocial.activerecord import FieldProxy

class User(ActiveRecord):
    username: str
    age: int
    
    # 习惯命名为 'c' (column) 或 'f' (field)
    c: ClassVar[FieldProxy] = FieldProxy()
```

### 使用 FieldProxy

现在你可以使用 `User.c.field_name` 来构建表达式：

```python
# 相等
User.find_one(User.c.username == "alice")

# 比较
Product.find_where(Product.c.price > 100)

# 组合 (AND/OR)
User.find_where((User.c.age >= 18) & (User.c.is_active == True))

# IN 查询
User.find_where(User.c.status.in_(['active', 'pending']))

# LIKE 查询
User.find_where(User.c.username.like("admin%"))
```

> **提示**: IDE 会自动补全 `User.c` 后面的字段名（虽然它是动态代理，但配合良好的类型提示可以实现）。目前 `FieldProxy` 是动态的，但在未来的版本中我们可能会提供静态生成工具以获得更好的 IDE 支持。

## 映射遗留数据库列 (Legacy Columns)

有时候数据库的列名并不符合 Python 的命名规范（例如包含空格、特殊字符或驼峰命名），或者你希望在 Python 中使用不同的属性名。
使用 `UseColumn` 可以轻松解决这个问题。

```python
from typing import Annotated, Optional
from rhosocial.activerecord import UseColumn

class LegacyUser(ActiveRecord):
    # 数据库列名是 "USER-NAME"，Python 属性名是 "username"
    username: Annotated[str, UseColumn("USER-NAME")]
    
    # 数据库列名是 "db_id"，Python 属性名是 "id"
    id: Annotated[str, UseColumn("db_id")]
```

`rhosocial-activerecord` 会自动处理属性名与列名之间的转换，无论是在查询生成还是结果映射时。
