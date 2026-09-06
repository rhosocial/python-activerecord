# 类型适配器

## 概述

类型适配器处理 SQLite 数据类型和 Python 类型之间的转换。SQLite 使用动态类型系统（类型亲和性），后端会自动管理类型转换。

## 类型映射

### 基本 SQLite 类型亲和性

| SQLite 类型 | Python 类型 | 备注 |
|------------|------------|------|
| INTEGER | `int` | 1、2、4、6 或 8 字节 |
| REAL | `float` | 8 字节 IEEE 浮点数 |
| TEXT | `str` | UTF-8 编码 |
| BLOB | `bytes` | 原始二进制数据 |
| NULL | `None` | 空值 |

SQLite 使用类型亲和性而不是严格类型。声明为 `VARCHAR` 的列仍然存储任何类型的数据——亲和性只是决定 SQLite 如何处理该值。

### Python 到 SQLite 的转换

| Python 类型 | SQLite 存储 | 转换 |
|-------------|------------|------|
| `int` | INTEGER | 直接 |
| `float` | REAL | 直接 |
| `str` | TEXT | 直接 |
| `bytes` | BLOB | 直接 |
| `bool` | INTEGER | `True` → 1，`False` → 0 |
| `None` | NULL | 直接 |

### SQLite 到 Python 的转换

| SQLite 类型 | Python 类型 | 转换 |
|------------|------------|------|
| INTEGER | `int` | 直接 |
| REAL | `float` | 直接 |
| TEXT | `str` | 直接 |
| BLOB | `bytes` | 直接 |
| INTEGER (0/1) | `bool` | 当列具有 BOOLEAN 亲和性时 |

## 特殊类型

后端为几种没有原生 SQLite 等价物的 Python 类型提供自动序列化和反序列化：

### datetime 和 date

```python
from datetime import datetime, date

# 存储为 ISO 8601 TEXT
# datetime: "2026-01-15T10:30:00.000000"
# date: "2026-01-15"

user = User(created_at=datetime.now())
user.save()  # 自动序列化为 TEXT

user = User.find_one(1)
print(user.created_at)  # 自动反序列化为 datetime
```

| Python 类型 | SQLite 存储 | 格式 |
|-------------|------------|------|
| `datetime.datetime` | TEXT | ISO 8601 带微秒 |
| `datetime.date` | TEXT | ISO 8601 仅日期 |

### UUID

```python
import uuid

# 存储为 TEXT（36 个字符）
user = User(id=uuid.uuid4())
user.save()  # "550e8400-e29b-41d4-a716-446655440000"

user = User.find_one(1)
print(type(user.id))  # <class 'uuid.UUID'>
```

### Decimal

```python
from decimal import Decimal

# 存储为 TEXT 以获得精确精度
product = Product(price=Decimal("19.99"))
product.save()

product = Product.find_one(1)
print(type(product.price))  # <class 'decimal.Decimal'>
```

### dict 和 list (JSON)

需要 JSON1 扩展（自 SQLite 3.38.0 起内置）：

```python
# 存储为 JSON TEXT
user = User(settings={"theme": "dark", "notifications": True})
user.save()  # '{"theme": "dark", "notifications": true}'

user = User.find_one(1)
print(type(user.settings))  # <class 'dict'>
```

| Python 类型 | SQLite 存储 | 所需扩展 |
|-------------|------------|---------|
| `dict` | TEXT (JSON) | JSON1 |
| `list` | TEXT (JSON) | JSON1 |

### 特殊类型总结

| Python 类型 | SQLite 存储 | 格式 | 自动转换 |
|-------------|------------|------|---------|
| `datetime.datetime` | TEXT | ISO 8601 | 是 |
| `datetime.date` | TEXT | ISO 8601 | 是 |
| `uuid.UUID` | TEXT | 36 字符字符串 | 是 |
| `decimal.Decimal` | TEXT | 字符串表示 | 是 |
| `dict` | TEXT | JSON | 是（需要 JSON1） |
| `list` | TEXT | JSON | 是（需要 JSON1） |

## 自定义类型适配器

要为您的自定义 Python 类注册类型转换器：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")

class MyClass:
    def __init__(self, value):
        self.value = value

class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        import json
        return json.dumps({"value": value.value})

    @staticmethod
    def from_sql(value, dialect):
        import json
        data = json.loads(value)
        return MyClass(data["value"])

backend.type_registry.register(MyClass, MyClassAdapter)
```

更多详情请参阅 [自定义](../customization/README.md)。

## 检查类型支持

```python
from rhosocial.activerecord.backend.dialect.protocols import JSONSupport

dialect = backend.dialect

# 检查 JSON 支持（需要 JSON1 扩展）
if isinstance(dialect, JSONSupport) and dialect.supports_json_type():
    # JSON 类型可用
    pass
```

## 另请参阅

- [后端特定功能](../backend_specific_features/README.md) — SQLite 特定功能
- [自定义](../customization/README.md) — 自定义类型和适配器
- [核心：自定义类型](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/custom_types)

💡 *AI 提示*："类型系统如何在 Python 类型和 SQLite 类型之间进行转换？"
