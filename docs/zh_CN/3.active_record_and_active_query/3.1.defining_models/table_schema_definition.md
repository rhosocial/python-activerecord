# 表结构定义

本文档解释了如何为ActiveRecord模型定义表结构。表结构定义了数据库表的结构，包括字段名称、类型和约束。

## 基本结构定义

在rhosocial ActiveRecord中，表结构通过模型类定义来定义。类的每个属性代表数据库表中的一列。

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    id: int
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
```

在这个例子中：
- `id`、`username`、`email`、`created_at`和`updated_at`是必填字段
- `is_active`有一个默认值`True`

## 表名配置

默认情况下，表名从类名的蛇形命名法派生。例如，名为`UserProfile`的类会映射到名为`user_profile`的表。

您可以使用`__table_name__`类属性显式设置表名：

```python
class User(ActiveRecord):
    __table_name__ = 'app_users'  # 映射到'app_users'表
    
    id: int
    username: str
    # 其他字段...
```

## 主键配置

默认情况下，ActiveRecord假定主键字段名为`id`。您可以通过设置`__primary_key__`类属性来自定义：

```python
class Product(ActiveRecord):
    __primary_key__ = 'product_id'  # 使用'product_id'作为主键
    
    product_id: int
    name: str
    # 其他字段...
```

## 字段类型和数据库映射

rhosocial ActiveRecord利用Pydantic的类型系统，并将Python类型映射到适当的数据库列类型。以下是常见Python类型如何映射到数据库类型：

| Python类型 | SQLite | MySQL | PostgreSQL |
|-------------|--------|-------|------------|
| `int` | INTEGER | INT | INTEGER |
| `float` | REAL | DOUBLE | DOUBLE PRECISION |
| `str` | TEXT | VARCHAR | VARCHAR |
| `bool` | INTEGER | TINYINT | BOOLEAN |
| `datetime` | TEXT | DATETIME | TIMESTAMP |
| `date` | TEXT | DATE | DATE |
| `bytes` | BLOB | BLOB | BYTEA |
| `dict`, `list` | TEXT (JSON) | JSON | JSONB |
| `UUID` | TEXT | CHAR(36) | UUID |

## 字段约束

您可以使用Pydantic的`Field`函数为字段添加约束：

```python
from pydantic import Field

class Product(ActiveRecord):
    id: int
    name: str = Field(..., min_length=3, max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., pattern=r'^[A-Z][a-z]+$')
```

常见约束包括：
- `min_length`/`max_length`：用于字符串长度验证
- `gt`/`ge`/`lt`/`le`：用于数值验证（大于、大于等于、小于、小于等于）
- `regex`/`pattern`：用于字符串模式验证
- `default`：如果未提供则使用的默认值

## 可选字段

您可以使用Python的`typing.Optional`类型提示将字段标记为可选：

```python
from typing import Optional

class User(ActiveRecord):
    id: int
    username: str
    email: str
    bio: Optional[str] = None  # 可选字段，默认为None
```

## 默认值

您可以为字段指定默认值：

```python
class User(ActiveRecord):
    id: int
    username: str
    is_active: bool = True  # 默认为True
    login_count: int = 0  # 默认为0
```

## 计算字段

您可以定义计算属性，这些属性不存储在数据库中，但在访问时计算：

```python
class Order(ActiveRecord):
    id: int
    subtotal: float
    tax_rate: float = 0.1
    
    @property
    def total(self) -> float:
        """计算包含税的总额。"""
        return self.subtotal * (1 + self.tax_rate)
```

## 字段文档

使用文档字符串或Pydantic的`Field`描述来记录字段是一个好习惯：

```python
from pydantic import Field

class User(ActiveRecord):
    id: int
    username: str = Field(
        ...,
        description="用户登录的唯一用户名"
    )
    email: str = Field(
        ...,
        description="用户接收通知的电子邮件地址"
    )
```

## 架构验证

当您创建或更新模型实例时，Pydantic会自动根据您的架构定义验证数据。如果验证失败，将引发`ValidationError`，其中包含有关验证问题的详细信息。

## 高级架构功能（❌ 未实现）

### 索引

您可以使用`__indexes__`类属性在模型上定义索引：

```python
class User(ActiveRecord):
    __indexes__ = [
        ('username',),  # 单列索引
        ('first_name', 'last_name'),  # 复合索引
        {'columns': ('email',), 'unique': True}  # 唯一索引
    ]
    
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
```

### 自定义列类型

要更精确地控制数据库列类型，您可以使用带有`sa_column_type`参数的`Field`函数：

```python
from pydantic import Field

class Product(ActiveRecord):
    id: int
    name: str
    description: str = Field(
        ...,
        sa_column_type="TEXT"  # 在数据库中强制使用TEXT类型
    )
```

## 结论

通过rhosocial ActiveRecord模型定义表结构提供了一种干净、类型安全的方式来构建数据库。Python类型提示和Pydantic验证的结合确保了数据在整个应用程序中保持完整性。