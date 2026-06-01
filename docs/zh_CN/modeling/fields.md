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

## 推导字段 (Derived Fields)

推导字段是只读的计算字段，其值由数据库在查询时动态计算。它们不存储在数据库中，而是通过 SQL 表达式在 SELECT 子句中生成。推导字段不会被 Pydantic 追踪，也不参与脏字段检测。

### 声明方式

有两种声明推导字段的方式：

#### Form A：ClassVar 赋值

```python
from typing import ClassVar
from rhosocial.activerecord.base import DerivedField
from rhosocial.activerecord.backend.expression import Column, Literal

class Product(ActiveRecord):
    __table_name__ = "product"
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    # 使用 ClassVar 赋值
    discounted_price: ClassVar[DerivedField] = DerivedField(
        lambda d: Column(d, "price") * Literal(d, 0.9)
    )
    total_value: ClassVar[DerivedField] = DerivedField(
        lambda d: Column(d, "price") * Column(d, "quantity")
    )
```

#### Form B：ClassVar + Annotated

```python
from typing import Annotated, ClassVar
from rhosocial.activerecord.base import DerivedField
from rhosocial.activerecord.backend.expression import Column, Literal

class Product(ActiveRecord):
    __table_name__ = "product"
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    # 使用 Annotated 声明，可附加类型信息
    discounted_price: ClassVar[Annotated[float, DerivedField(
        lambda d: Column(d, "price") * Literal(d, 0.9)
    )]]
    total_value: ClassVar[Annotated[float, DerivedField(
        lambda d: Column(d, "price") * Column(d, "quantity")
    )]]
```

### 使用 FieldProxy 构建表达式（推荐）

结合 `FieldProxy` 可以获得类型安全的列引用，避免手动拼写列名：

```python
from typing import ClassVar
from rhosocial.activerecord.base import DerivedField, FieldProxy
from rhosocial.activerecord.backend.expression import Literal

class Product(ActiveRecord):
    __table_name__ = "product"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    discounted_price: ClassVar[Annotated[float, DerivedField(
        lambda d: Product.c.price * Literal(d, 0.9)
    )]]
    total_value: ClassVar[Annotated[float, DerivedField(
        lambda d: Product.c.price * Product.c.quantity
    )]]
```

### 使用 UseColumn 自定义列别名

通过 `UseColumn` 可以为推导字段指定 SQL 别名，而不影响 Python 属性名：

```python
from typing import Annotated, ClassVar
from rhosocial.activerecord.base import DerivedField, UseColumn
from rhosocial.activerecord.backend.expression import Column, Literal

class Product(ActiveRecord):
    __table_name__ = "product"
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    # SQL 别名为 "disc"，Python 属性名为 "discounted_price"
    discounted_price: ClassVar[Annotated[float, DerivedField(
        lambda d: Column(d, "price") * Literal(d, 0.9)
    ), UseColumn("disc")]]
```

### 使用 UseAdapter 进行类型适配

`UseAdapter` 可以将数据库返回的值转换为 Python 类型：

```python
from typing import Annotated, Any, ClassVar, Dict, Optional, Set, Type
from rhosocial.activerecord.base import DerivedField, UseAdapter
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.expression import Column, Literal

class PriceToIntAdapter:
    """将浮点价格四舍五入为整数"""
    def to_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        return float(value)
    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        return int(round(value))
    @property
    def supported_types(self) -> Dict[Type, Set[Type]]:
        return {int: {float}}

class Product(ActiveRecord):
    __table_name__ = "product"
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    # 结果将四舍五入为整数
    total_int: ClassVar[Annotated[int, DerivedField(
        lambda d: Column(d, "price") * Column(d, "quantity")
    ), UseAdapter(PriceToIntAdapter(), int)]]
```

### 查询时使用推导字段

推导字段是可选的，必须通过 `derived` 参数显式请求：

```python
# 获取所有产品，并包含推导字段
products = Product.find_all(derived=True)  # 包含所有推导字段

# 只包含特定推导字段
products = Product.find_all(derived=["discounted_price", "total_value"])

# 使用字典自定义别名
products = Product.find_all(derived={"discount": Product.c.price * Literal(0.9)})

# 单个记录
product = Product.find_one(1, derived=True)

# 结合其他查询条件
products = Product.find_all(
    Product.c.price > 10,
    derived=["discounted_price"]
)
```

### 注意事项

1. **只读性**：推导字段的值只能读取，不能修改。
2. **不参与验证**：推导字段不经过 Pydantic 验证，因为它们是 ClassVar。
3. **不跟踪变更**：推导字段不在脏字段跟踪范围内。
4. **列名冲突**：推导字段的 `UseColumn` 别名不能与普通字段的列名冲突。
5. **性能**：推导字段在查询时计算，复杂表达式可能影响查询性能。
