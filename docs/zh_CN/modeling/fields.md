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

## 指定 SQL 列类型 (UseSqlType)

默认情况下，`ActiveRecord` 会根据 Python 字段类型**自动推断**数据库列类型（`str` → 文本、`int` → 整数、`bool` → 布尔等）。当自动推断不满足需求（例如需要精确的 `VARCHAR(100)`、`DECIMAL(10,2)`、`JSONB`，或想显式控制列类型）时，使用 `UseSqlType` 注解来**显式指定 SQL 数据类型**。

`UseSqlType` 接受一个或多个 `DataType` 实例：

```python
from typing import Annotated, Optional
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import (
    VarCharType, DecimalType, JsonType, DateTimeType, IntegerType,
)

class User(ActiveRecord):
    __table_name__ = "users"

    # 显式指定 VARCHAR(100)，而非默认的 TEXT
    username: Annotated[str, UseSqlType(VarCharType(length=100))]

    # 显式指定精确小数 DECIMAL(10,2)
    balance: Annotated[Optional[float], UseSqlType(DecimalType(precision=10, scale=2))]

    # 结构化 JSON
    metadata: Annotated[Optional[dict], UseSqlType(JsonType())]

    # 日期时间
    created_at: Annotated[str, UseSqlType(DateTimeType())]

    # 32 位自增主键
    id: Annotated[int, UseSqlType(IntegerType())]
```

### 通用类型与后端特定类型

`DataType` 分为两类，`UseSqlType` 对它们一视同仁：

- **通用类型**（如 `VarCharType`、`IntegerType`、`TextType`、`JsonType`）：跨后端可移植，每个后端都将其渲染为自身原生 SQL（如 SQLite 将 `VARCHAR(100)` 渲染为 `TEXT`，MySQL 渲染为 `VARCHAR(100)`）。
- **后端特定类型**（如 `PostgresJsonBType`、`MySQLEnumType`，命名以后端名为前缀）：只在注册它的后端上渲染；其他后端会**跳过**该类型（而非静默替换为有损形式）。

### 声明顺序 = 后端优先级

`UseSqlType` 可以同时声明**多个**类型。DDL 生成时，框架选择**第一个**当前方言能够渲染的类型；全部不匹配时回退到自动推断（`suggest_column_type`），再失败则报错。

```python
from typing import Annotated
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import JsonType
# 以下为后端特定类型（来自对应后端包）
from rhosocial.activerecord.backend.impl.postgres.expression.types import PostgresJsonBType
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLLongTextType

# 优先级：PostgreSQL 用 JSONB，MySQL 5.7 以下用 LONGTEXT（JSON 不可用），其他用通用 JSON
payload: Annotated[dict, UseSqlType(
    PostgresJsonBType(), JsonType(), MySQLLongTextType(),
)]
```

这样声明使得**同一个模型**可以跨多个后端部署，每个后端自动选择最合适的列类型。

> **与 `UseColumn` 的关系**：`UseColumn` 控制**列名**（Python 属性名 ↔ 数据库列名），`UseSqlType` 控制**列类型**（SQL 数据类型），两者互不冲突，可同时使用。
>
> 数据类型体系的完整说明（生命周期、值对象语义、通用/后端特定配合）见[数据类型](../backend/expression/types.md)。

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

### 多个 FieldProxy：为不同表别名创建独立代理

`FieldProxy` 本身也是一个**字段**（`ClassVar`），因此像普通字段一样，**想定义几个都可以**——`c`、`c1`、`c2`、`c_mgr`、`c_sub`…… 你可以为每个代理指定**不同的表别名**，让它们分别指向同一张表的不同实例。

这在**联结查询，尤其是自连接（Self-Join）** 中非常有用：不需要在每次查询时调用 `with_table_alias()` 动态创建，而是把别名代理作为模型定义的一部分预先声明，复用起来更清晰。

#### 通过构造函数预绑定表别名

`FieldProxy` 构造函数接受 `table_alias` 参数，创建时就绑定别名：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord.base import FieldProxy

class Employee(ActiveRecord):
    __table_name__ = "employees"
    id: int
    name: str
    manager_id: Optional[int]  # 指向同一张表的 id

    # 默认代理：指向 'employees' 表本身
    c: ClassVar[FieldProxy] = FieldProxy()

    # 第二个代理：预绑定 'managers' 表别名
    c_mgr: ClassVar[FieldProxy] = FieldProxy(table_alias="managers")

    # 第三个代理：预绑定 'subordinates' 表别名
    c_sub: ClassVar[FieldProxy] = FieldProxy(table_alias="subordinates")
```

#### 自连接：查询员工及其经理

```python
# 员工表自连接：JOIN employees AS managers
# c_mgr 自动生成 "managers"."name" 等引用
query = Employee.query() \
    .join(Employee, on=(Employee.c.manager_id == Employee.c_mgr.id), alias="managers") \
    .select(Employee.c.name.as_("emp"), Employee.c_mgr.name.as_("manager"))

sql, params = query.to_sql()
# SELECT "employees"."name" AS "emp", "managers"."name" AS "manager"
# FROM "employees"
# JOIN "employees" AS "managers" ON "employees"."manager_id" = "managers"."id"

rows = query.all()  # 每个员工的 emp + manager 名称
```

#### 更深层自连接：员工 → 经理 → 上级经理

定义多个别名代理后，可以轻松级联多层自连接：

```python
query = Employee.query() \
    .join(Employee, on=(Employee.c.manager_id == Employee.c_mgr.id), alias="managers") \
    .join(Employee, on=(Employee.c_mgr.manager_id == Employee.c_sub.id), alias="subordinates") \
    .select(
        Employee.c.name.as_("emp"),
        Employee.c_mgr.name.as_("manager"),
        Employee.c_sub.name.as_("grand_manager"),
    )

# SELECT "employees"."name" AS "emp", "managers"."name" AS "manager",
#        "subordinates"."name" AS "grand_manager"
# FROM ("employees" JOIN "employees" AS "managers" ON "employees"."manager_id" = "managers"."id")
# JOIN "employees" AS "subordinates" ON "managers"."manager_id" = "subordinates"."id"
```

#### 在 WHERE 条件中使用别名代理

别名代理不仅可用于 `select`，同样可用于 `join` 的 `on`、`where` 等任何需要列引用的地方：

```python
# 查找经理名为 Alice 的所有直接下属
query = Employee.query() \
    .join(Employee, on=(Employee.c.manager_id == Employee.c_mgr.id), alias="managers") \
    .where(Employee.c_mgr.name == "Alice") \
    .select(Employee.c.name)
```

#### 与 `with_table_alias()` 的对比

| 方式 | 用法 | 适用场景 |
|------|------|----------|
| `FieldProxy(table_alias="...")` | 定义时预绑定 | 别名固定、需要反复使用，作为模型的一部分声明 |
| `c.with_table_alias("...")` | 使用时动态创建 | 别名临时、一次性使用 |

两种方式生成的 SQL **完全相同**；预绑定方式把「这张表有哪些别名实例」集中声明在模型里，自连接语义一目了然。

## 推导字段 (Derived Fields)

推导字段是**只读的计算字段**，其值在查询时由数据库 SQL 表达式动态生成。它不存储在数据库表中，不会被 Pydantic 验证，也不会被脏字段跟踪。

典型用途：价格计算（折扣价、含税价）、全名拼接、JSON 提取、聚合结果引用等。

声明与使用的完整说明请参阅：[**推导字段 (Derived Fields)**](./derived_fields.md)。

查询时，推导字段是可选的，必须通过 `derived` 参数显式请求：

```python
# 获取所有产品，并包含推导字段
products = Product.find_all(derived=True)  # 包含所有推导字段

# 只包含特定推导字段
products = Product.find_all(derived=["discounted_price", "total_value"])

# 单个记录
product = Product.find_one(1, derived=True)

# 结合其他查询条件
products = Product.find_all(
    Product.c.price > 10,
    derived=["discounted_price"]
)
```