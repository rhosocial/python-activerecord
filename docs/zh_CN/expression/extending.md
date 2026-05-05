# 扩展指南：实现可序列化表达式

本文档面向后端开发者，介绍如何为自定义表达式实现序列化能力。

## 基本要求

表达式类必须满足以下条件才能被序列化框架正确处理：

1. 继承自 `BaseExpression`
2. `__init__` 参数名与属性名对应（使用 `_` 前缀私有属性或同名属性）
3. 使用 `get_params()` 返回可序列化参数

## get_params() 约定

默认的 `get_params()` 实现基于 `inspect.signature` 自动推断：

- 参数 `foo` → 属性 `self._foo` 或 `self.foo`
- `VAR_POSITIONAL (*args)` → 列表
- `VAR_KEYWORD (**kwargs)` → 跳过（需手动覆盖）

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, name, value):
        super().__init__(dialect)
        self._name = name
        self._value = value
    # 无需手动实现 get_params()，默认实现会自动提取
```

### 自定义 get_params()

当默认推断不适用时，重写该方法：

```python
def get_params(self) -> dict:
    params = super().get_params()
    # 添加或修改参数
    params["custom_key"] = self._custom_value
    return params
```

## 注册机制

### 自动注册

内置表达式通过 `_auto_register_builtins()` 自动注册到 `ExpressionRegistry`。

### 手动注册

自定义表达式需要手动注册：

```python
from rhosocial.activerecord.backend.expression.serialization import ExpressionRegistry

ExpressionRegistry.register(MyExpression)
```

## 四类特殊情况

### 1. 方言专属枚举参数

某些方言有专属枚举值（如 PostgreSQL 的 `IsolationLevel`）：

```python
class MyTransactionExpression(BaseExpression):
    def __init__(self, dialect, isolation_level: str = "READ COMMITTED"):
        super().__init__(dialect)
        self._isolation_level = isolation_level  # 接受字符串而非枚举

# get_params() 返回字符串，对方言无依赖
```

### 2. 通过 fluent API 设置的状态

Fluent API 修改的状态必须同步到 `__init__` 参数：

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, hint: str = None):
        super().__init__(dialect)
        self._hint = hint  # 既是 __init__ 参数，也是 fluent API 目标

    def with_hint(self, hint: str):
        self._hint = hint
        return self
```

### 3. set 类型参数

`set` 类型无法直接 JSON 序列化，在 `get_params()` 中转为 list：

```python
def get_params(self) -> dict:
    params = super().get_params()
    params["columns"] = list(self._columns)  # set -> list
    return params
```

### 4. 循环引用

当前框架不检测循环引用。如有自引用可能，在 `get_params()` 中截断：

```python
def get_params(self) -> dict:
    params = {"id": self._id, "name": self._name}
    if self._parent is not None:
        params["parent_id"] = self._parent._id  # 只存 ID，不存对象
    return params
```

## IntrospectionExpression 约定

`IntrospectionExpression` 子类（如 `TableListExpression`）的 `None` 过滤规则：

- 可选参数为 `None` 时，不应出现在 `params` 中

```python
class TableListExpression(IntrospectionExpression):
    def get_params(self) -> dict:
        params = {}
        if self._schema is not None:
            params["schema"] = self._schema
        # include_views 默认 True，始终包含
        params["include_views"] = self._include_views
        return params
```

## 错误契约

所有经过 `_reconstruct()` 的路径，`TypeError` 都会被包装为 `ExpressionDeserializationError`。这确保调用方只需捕获一种异常类型。

## 相关文档

- [核心文档](./serialization.md)：序列化机制说明
- [格式参考](./format-reference.md)：ExpressionSpec 完整规范