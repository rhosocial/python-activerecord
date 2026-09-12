# 自定义

## 概述

rhosocial-activerecord 设计为可扩展的。您可以在多个级别自定义框架：

1. **自定义表达式** —— 为 SQLite 特定的 SQL 语法创建新的表达式类
2. **自定义数据类型** —— 为自定义列类型定义新的 DataType 子类
3. **自定义类型适配器** —— 注册 Python 对象和数据库值之间的转换器

## 自定义架构

框架使用**委托 + 组合**模式：

- **表达式**通过委托其绑定方言的 `format_*()` 方法来生成 SQL
- **数据类型**通过委托 `dialect.format_data_type()` 生成 DDL SQL
- **方言**由小型、专注的 mixin 组合而成
- **类型适配器**在 Python 值和数据库值之间进行转换，注册在 `TypeRegistry` 中

这意味着您可以在不修改核心库的情况下扩展任何层。

## 何时自定义

| 需求 | 方法 |
|------|------|
| SQLite 有一个表达式库中没有的函数 | 自定义表达式 |
| SQLite 有一个类型系统中没有的列类型 | 自定义数据类型 |
| Python 对象需要自定义序列化 | 自定义类型适配器 |

## 自定义表达式

SQLite 后端使用 SQLite 特定的 SQL 语法扩展核心表达式类。要添加新的表达式类型：

```python
from rhosocial.activerecord.backend.expression.bases import BaseExpression

class MyCustomExpression(BaseExpression):
    def __init__(self, dialect, *args):
        super().__init__(dialect)
        self.args = args

    @property
    def format_method(self) -> str:
        # 绝不复写 to_sql()——只需声明渲染该表达式的方言方法名；
        # 由方言实现 format_my_custom_sql(self, expression) 生成 SQLite 特定的 SQL。
        return "format_my_custom_sql"
```

### 示例：JSON Path 表达式

```python
from rhosocial.activerecord.backend.expression.base import BaseExpression

class JsonPathExpression(BaseExpression):
    def __init__(self, dialect, column, path):
        super().__init__(dialect)
        self.column = column
        self.path = path

    @property
    def format_method(self) -> str:
        # 渲染该表达式的方言 format_*() 方法名。
        # 绝不复写 to_sql()——渲染由 BaseExpression 统一实现；
        # 由方言实现 format_json_path(self, expression)。
        return "format_json_path"

    @property
    def params(self):
        return (self.path,)
```

详细指南请参阅 [自定义表达式](../../../../en_US/backend/template/customization/custom_expressions.md)。

## 自定义数据类型

SQLite 使用动态类型系统。要添加对新 Python 类型的支持：

```python
from rhosocial.activerecord.backend.impl.sqlite.types import SQLiteDataType

@SQLiteDataType.handles(MyClass)
class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        import json
        return json.dumps(value.__dict__)

    @staticmethod
    def from_sql(value, dialect):
        import json
        return MyClass(**json.loads(value))
```

详细指南请参阅 [自定义数据类型](../../../../en_US/backend/template/customization/custom_types.md)。

## 自定义类型适配器

要注册自定义类型转换器：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.type_registry.register(MyClass, MyAdapter)
```

### 适配器接口

```python
class MyAdapter:
    @staticmethod
    def to_sql(value, dialect):
        """将 Python 值转换为 SQLite 值。"""
        return serialized_value

    @staticmethod
    def from_sql(value, dialect):
        """将 SQLite 值转换为 Python 值。"""
        return python_value
```

详细指南请参阅 [自定义类型适配器](../../../../en_US/backend/template/customization/custom_adapters.md)。

## 相关主题

- [类型适配器](../type_adapters/README.md) — 类型转换系统
- [方言表达式](../backend_specific_features/README.md) — 表达式系统架构
- [字段类型](../backend_specific_features/README.md) — DataType 层次结构

💡 *AI 提示*："如何添加对表达式库中没有的 SQLite 特定函数的支持？"
