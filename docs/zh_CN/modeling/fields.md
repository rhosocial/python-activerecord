# 字段定义 (Fields & Proxies)

在 `rhosocial-activerecord` 中，字段定义复用了 Pydantic 的语法，同时引入了 `FieldProxy` 来弥合 Python 对象与 SQL 查询之间的鸿沟。

## 基础字段定义

模型字段就是标准的 Python 类型注解，可以使用 `pydantic.Field` 来添加元数据和验证规则。

> **注意**：默认情况下，类属性名（属性名）直接对应数据库表的字段名（列名），且**区分大小写**。如果它们不一致，请参阅下一节“映射遗留数据库列”。

```python
from typing import Optional
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord

class Product(ActiveRecord):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    is_active: bool = True
    
    @classmethod
    def table_name(cls) -> str:
        return "products"
```

## 映射遗留数据库列 (Legacy Columns)

**如果数据表字段名不是合法的 Python 属性名该怎么办？**

有时候数据库的列名并不符合 Python 的命名规范（例如包含空格、特殊字符或驼峰命名），或者你希望在 Python 中使用不同的属性名。
使用 `UseColumn` 可以轻松解决这个问题。

```python
from typing import Annotated, Optional
from rhosocial.activerecord.base import UseColumn

class LegacyUser(ActiveRecord):
    # 数据库列名是 "USER-NAME"，Python 属性名是 "username"
    username: Annotated[str, UseColumn("USER-NAME")]
    
    # 数据库列名是 "db_id"，Python 属性名是 "id"
    id: Annotated[str, UseColumn("db_id")]
```

`rhosocial-activerecord` 会自动处理属性名与列名之间的转换，无论是在查询生成还是结果映射时。

## FieldProxy: 类型安全的查询

传统的 ORM 常常需要使用字符串来引用字段（例如 `filter(name="Alice")`），这容易导致拼写错误且难以重构。
`FieldProxy` 允许你以 Python 表达式的方式构建查询。

### 启用 FieldProxy

在模型中定义一个 `ClassVar`：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord.base import FieldProxy

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
Product.find_all(Product.c.price > 100)

# 组合 (AND/OR)
User.find_all((User.c.age >= 18) & (User.c.is_active == True))

# IN 查询
User.find_all(User.c.status.in_(['active', 'pending']))

# LIKE 查询
User.find_all(User.c.username.like("admin%"))
```

> **提示**: IDE 会自动补全 `User.c` 后面的字段名（虽然它是动态代理，但配合良好的类型提示可以实现）。目前 `FieldProxy` 是动态的，但在未来的版本中我们可能会提供静态生成工具以获得更好的 IDE 支持。

> **FieldProxy 的优势**: 当字段单独定义了数据表字段名时（使用 `UseColumn`），FieldProxy 会自动使用自定义的字段名。例如，如果你定义了 `username: Annotated[str, UseColumn("USER-NAME")]`，那么 `User.c.username` 会自动引用数据库中的 `"USER-NAME"` 列，无需你手动处理这种映射关系。

### 设计理念：为何需要手动定义？

你可能会注意到，`FieldProxy` 并不是默认存在的，而是需要用户手动将其定义为 `ClassVar`。这是一个经过深思熟虑的设计选择，主要基于以下两个原因：

1.  **避免命名冲突 (Avoid Naming Conflicts)**
    ActiveRecord 模型中包含了大量的方法和属性（如 `save`, `delete`, `query`, `table_name` 等）。如果 ORM 自动向模型中注入一个类似 `c` 或 `fields` 的属性，极有可能与用户定义的数据库列名发生冲突（例如，如果你的表中恰好有一个列名为 `c` 或 `fields`）。
    通过强制用户手动定义，你可以自由选择代理对象的名称（通常习惯使用 `c`，但如果冲突，你也可以命名为 `f` 或 `columns`），从而完全掌控模型的命名空间。

2.  **支持表别名 (Support Table Aliases)**
    `FieldProxy` 的另一个重要作用是支持复杂的 SQL 查询，特别是自连接（Self-Join）。在自连接中，我们需要多次引用同一张表，但赋予不同的别名。通过实例化带有别名的 `FieldProxy`，我们可以轻松创建这类查询。

    **示例：员工与经理（自连接）**

    假设我们有一个 `User` 模型，其中 `manager_id` 指向同一个表中的 `id`。

    ```python
    class User(ActiveRecord):
        id: int
        name: str
        manager_id: Optional[int]
        
        # 默认代理（指向 'users' 表）
        c: ClassVar[FieldProxy] = FieldProxy()

    # 创建一个指向 'managers' 别名的代理
    ManagerAlias = User.c.with_table_alias("managers")

    # 查询所有用户及其经理的名称
    # SELECT users.name, managers.name as manager_name 
    # FROM users 
    # JOIN users AS managers ON users.manager_id = managers.id
    query = User.query() \
        .join(User, on=(User.c.manager_id == ManagerAlias.id), alias="managers") \
        .select(User.c.name, ManagerAlias.name.as_("manager_name")) \
        .all()
    ```
