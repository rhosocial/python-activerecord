# 扩展指南：实现可序列化表达式

本文档面向后端开发者，介绍如何让自定义表达式可序列化。

## 基本要求

表达式类必须满足以下条件才能被序列化框架正确处理：

1. 继承自 `BaseExpression`
2. `__init__` 参数名与属性名对应（使用 `_` 前缀私有属性或同名属性）
3. 不要实现 `get_params()`——通用实现是唯一的序列化路径，`__init__` 必须以构造参数收到的名字保存状态

## get_params() 约定

通用 `get_params()` 实现基于 `inspect.signature` 自动推断：

- 参数 `foo` → 属性 `self._foo` 或 `self.foo`
- `VAR_POSITIONAL (*args)` → 列表
- `VAR_KEYWORD (**kwargs)` → 收集到的额外参数存入与该参数同名的属性上的 dict（如 `self.collation_options`），并合并进 `params` 的顶层，这样重建时会重新展开成关键字参数

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, name, value):
        super().__init__(dialect)
        self._name = name
        self._value = value
    # 无需手动实现 get_params()，默认实现会自动提取
```

核心中的 `CollateExpression` 就是 `**kwargs` 的例子：它把 `**collation_options` 收集进 `self.collation_options: dict`，于是 `get_params()` 会把 `binary`、`pad` 等作为顶层参数返回，重建时再把它们当关键字参数传回。

若某个参数按约定无法解析，会跳过并发出警告。这条警告就是诊断信号——它意味着 `__init__` 把状态存在了 `get_params()` 看不到的名字上，而修复永远在 `__init__` 里。

### 为什么没有"自定义 get_params()"

`get_params()` 不是扩展点：重写它是缺陷，不是定制。核心在 `tests/.../dummy2/test_expression_contract.py::test_no_get_params_override` 里无例外地强制这一点——每个已注册的表达式类都必须沿用通用实现。（该测试允许的唯一例外，是做真正的"原始值 ↔ 归一化值"往返改写的 `VAR_POSITIONAL` 类，而核心注册表里没有任何一个属于这种情况。）

原因是结构性的，不是风格问题。往返是靠"用 `get_params()` 返回的内容去调用构造函数"重建的，所以这两半必须彼此吻合。而重写恰恰是它们开始走偏的地方：这个类发出的键会被构造函数改名、合并或拒绝，`_reconstruct()` 再把由此产生的 `TypeError` 包装成 `ExpressionDeserializationError`，状态就悄悄丢了。各后端包曾各自积累过重写实现，而它们存在的理由全都是同一个：`__init__` 把调用方传进来的东西改了名或合并了——而一旦按收到的名字原样保存，这些重写就全都不再必要。

当通用实现的结果不是你想要的时，修复始终在 `__init__` 里，且只有三种形态：

| 问题 | 修复 |
|---|---|
| 你把调用方传进来的值改了名或合并了 | 按参数本来的名字保存 |
| 构造函数的两种写法含义相同 | 两个槽位都留着；值放在调用方用的那个槽位，另一个留 `None` |
| 该值按原样无法序列化 | 在 `__init__` 里转换，保存转换后的值 |

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

下面这四种情况，就是开发者会去写自定义 `get_params()` 的常见理由。它们没有一个需要重写：每一种都在 `__init__` 里解决。

### 1. 方言专属枚举参数

某些方言有专属枚举值（如 PostgreSQL 的 `IsolationLevel`）。调用方给哪种写法都可以，保存 spec 能承载的那个值：

```python
class MyTransactionExpression(BaseExpression):
    def __init__(self, dialect, isolation_level="READ COMMITTED"):
        super().__init__(dialect)
        # 接受方言的枚举或其字符串；保存归一化后的字符串
        self._isolation_level = (
            isolation_level.value
            if isinstance(isolation_level, Enum)
            else str(isolation_level)
        )

# get_params() 返回 {"isolation_level": "SERIALIZABLE"}——字符串，与方言无关
# 重建时把这个字符串传回同一个接受字符串的构造函数
```

### 2. 通过 fluent API 设置的状态

Fluent API 修改的状态必须同步到 `__init__` 参数——setter 与参数必须读写**同一个**属性，因为 `get_params()` 能看到的只有那个属性：

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, hint: str = None):
        super().__init__(dialect)
        self._hint = hint  # 既是 __init__ 参数，也是 fluent API 目标

    def with_hint(self, hint: str):
        self._hint = hint
        return self
```

如果 setter 在参数自己的属性之外另写一份，那份状态往返时就丢了。

### 3. set 类型参数

`set` 不适合承载表达式状态：它没有顺序，而且 codec 会把它编码成一个扁平列表，其中的成员拿不到本应属于它们的嵌套表达式标记，因此装着表达式的 `set` 过不了 JSON 往返。在 `__init__` 里转换、保存转换后的值——通用路径于是发出的正是构造函数能接受的东西：

```python
class ColumnSetExpression(BaseExpression):
    def __init__(self, dialect, columns):
        super().__init__(dialect)
        self._columns = list(columns)  # 传进来可以是 set 或任意可迭代对象，保存为 list

# get_params() 返回 {"columns": [...]}；重建时把这个 list 传回同一个构造函数，
# 它接受 list 和接受 set 一样自然
```

### 4. 循环引用

框架不检测环，自引用也无法序列化——序列化器会一路递归到 Python 的递归上限。要按**标识**而不是按对象来保存这条链接：参数是 id，对象（如果确实需要）放在构造函数不接收的属性上，`get_params()` 根本不会读它。

```python
class TreeNodeExpression(BaseExpression):
    def __init__(self, dialect, name, parent_id=None):
        super().__init__(dialect)
        self._name = name
        self._parent_id = parent_id  # 标识，而非对象
        # 由树遍历器解析；没有同名参数，因此永不进入序列化
        self._parent = None
```

如果父节点确实必须随节点一起传递，就把它做成普通的嵌套表达式参数——`{"__expr__": ...}` 正是为此存在的。这样一来，树自然就是有限的。

## IntrospectionExpression 约定

`IntrospectionExpression` 子类（如 `TableListExpression`）把构造函数与同名 fluent setter 结合在一起。通用路径的两处机制已经考虑到了这一点：

```python
class TableListExpression(IntrospectionExpression):
    def __init__(self, dialect, schema=None, include_views=True, include_system=False, table_type=None):
        super().__init__(dialect, schema)
        self._include_views = include_views
        self._include_system = include_system
        self._table_type = table_type

    def include_views(self, value: bool = True):
        self._include_views = value  # 与读取参数同一个属性
        return self
```

- **两种写法都存在时，可调用的那个不是状态。** 若某参数同时存在 `self.foo` 与 `self._foo`，且公开属性是个 fluent 方法，则取私有属性的值。
- **未赋值的可选参数会输出为 `null`，而不是被省略。** 这是安全的：反序列化会把它传回去，构造函数的默认值随之生效。真正不安全的是丢掉一个取值与其默认值不同的参数——那才是往返丢掉的状态。

## 错误契约

所有经过 `_reconstruct()` 的路径，`TypeError` 都会被包装为 `ExpressionDeserializationError`。这确保调用方只需捕获一种异常类型。

## 序列化格式约定（键名保留）

`get_params()` 返回的**值**在任何深度上都不得包含以下保留键名，否则反序列化行为未定义——反序列化会把它们当作框架标记来读：

- `__expr__`：用于标记嵌套表达式
- `__tuple__`：用于标记元组
- `__value__` / `__vdc__`：用于标记 codec 编码的标量值与 dataclass 值

你自己的顶层键来自 `__init__` 的参数名（以及合并进来的 `**kwargs` 额外参数），所以绝不要把参数命名为保留键。对于键不由你控制的不透明载荷，危险在载荷内部：那些键会被原样复制进 spec，给参数换个名字对此毫无帮助。要么在构造时校验，要么把载荷存成文本。

```python
_RESERVED = ("__expr__", "__tuple__", "__value__", "__vdc__")

# 错误示例 - 含有 "__expr__" 的载荷会被当成嵌套表达式读回来
class RawJsonStorageExpr(BaseExpression):
    def __init__(self, dialect, data: dict):
        super().__init__(dialect)
        self._data = data

# 正确示例 - 载荷在进入 spec 之前就被拒绝
class SafeJsonStorageExpr(BaseExpression):
    def __init__(self, dialect, json_data: dict):
        super().__init__(dialect)
        for key in json_data:
            if key in _RESERVED:
                raise ValueError(f"{key!r} is a reserved serialization key")
        self._json_data = json_data
```

## 相关文档

- [核心文档](./serialization.md)：序列化机制说明
- [格式参考](./format-reference.md)：ExpressionSpec 完整规范