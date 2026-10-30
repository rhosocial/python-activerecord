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

核心中的 `CollateFunction` 就是 `**kwargs` 的例子：它把 `**collation_options` 收集进 `self.collation_options: dict`，于是 `get_params()` 会把 `binary`、`pad` 等作为顶层参数返回，重建时再把它们当关键字参数传回。

若某个参数按约定无法解析，会跳过并发出警告。这条警告就是诊断信号——它意味着 `__init__` 把状态存在了 `get_params()` 看不到的名字上，而修复永远在 `__init__` 里。

### 为什么没有"自定义 get_params()"

`get_params()` 不是扩展点：重写它是缺陷，不是定制。核心在 `tests/.../dummy2/test_expression_artifact_contract.py::test_no_get_params_override` 里无例外地强制这一点——每个已注册的表达式类都必须沿用通用实现。（该测试允许的唯一例外，是做真正的"原始值 ↔ 归一化值"往返改写的 `VAR_POSITIONAL` 类，而核心注册表里没有任何一个属于这种情况。）

原因是结构性的，不是风格问题。往返是靠"用 `get_params()` 返回的内容去调用构造函数"重建的，所以这两半必须彼此吻合。而重写恰恰是它们开始走偏的地方：这个类发出的键会被构造函数改名、合并或拒绝，状态就悄悄丢了——解码器只按名字把值交出去，并不替结果把关。各后端包曾各自积累过重写实现，而它们存在的理由全都是同一个：`__init__` 把调用方传进来的东西改了名或合并了——而一旦按收到的名字原样保存，这些重写就全都不再必要。

当通用实现的结果不是你想要的时，修复始终在 `__init__` 里，且只有三种形态：

| 问题 | 修复 |
|---|---|
| 你把调用方传进来的值改了名或合并了 | 按参数本来的名字保存 |
| 构造函数的两种写法含义相同 | 两个槽位都留着；值放在调用方用的那个槽位，另一个留 `None` |
| 该值按原样无法序列化 | 在 `__init__` 里转换，保存转换后的值 |

## 注册机制

### 自动注册

内置表达式不需要你做任何事。框架**一次性**装配默认注册表——遍历表达式包，遇到的每个节点都按 kind 登记。**没有**任何函数需要调用，也**没有**任何清单需要维护。

### 注册你自己的

`ExpressionRegistry` 构造出来是空的——这正是它能被交给调用方、只放行你选定内容的前提。`register_node` 是**实例方法**，kind 由类派生：

```python
from rhosocial.activerecord.backend.expression.registry import ExpressionRegistry

allowed = ExpressionRegistry()
allowed.register_node(MyExpression)          # kind 为 "my_expression"
```

枚举**根本不需要登记**。`(str, Enum)` 的成员就是一个 JSON 字符串，没有东西需要解析——封闭集合声明在类里，各语言也各自声明自己的。

有两个 kind 不在默认表里：`RawSQL` 与 `RawSQLPredicate`，因为 `to_sql()` 原样输出调用方担保过的文本，而工件不该能选择它。它们设了 `REGISTER_BY_DEFAULT = False`；登记其中任何一个与登记其它 kind 是同一个调用，交给信任自己工件的调用方。

然后把它传给读侧：

```python
deserialize(artifact, dialect, registry=allowed)
```

注册表只管**读方**能产出什么。写侧不查表，所以这里的一切都不影响 `serialize`。

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
        self.name = name
        self.parent_id = parent_id  # 标识，而非对象
        # 由树遍历器解析；没有同名参数，因此永不进入序列化
        self._parent = None
```

如果父节点确实必须随节点一起传递，就把它做成普通的嵌套表达式参数——一个普通的 `parent`，持有另一个表达式，序列化时就是一个嵌套的 `{kind, params}` 节点。这样一来，树自然就是有限的。

## IntrospectionExpression 约定

内省节点把构造函数与 fluent setter 结合在一起，而这两者过去想要同一个名字。现在不想要了——因为参数必须能按自己的名字被读到，工件才谈得上可重建：

```python
class TableListQueryStatement(IntrospectionExpression):
    def __init__(self, dialect, schema=None, include_views=True, include_system=False, table_type=None):
        super().__init__(dialect, schema)
        self.include_views = include_views   # 参数自己的名字
        self.include_system = include_system
        self.table_type = table_type

    def with_include_views(self, value: bool = True):   # 绝不叫 include_views
        self.include_views = value
        return self
```

- **只有一种写法，就是参数自己的名字。** `get_params()` 读的是 `getattr(self, name)`：没有 `_{name}` 探测，也没有「可调用的那个不是状态」这条规则要套用。类没存下来的参数会抛 `AttributeError`，并指明是哪个类、哪个参数——这才是值得听见的缺陷，而不是一条没人读的警告。
- **fluent setter 叫 `with_*`。** 叫 `include_views` 的 setter 会占掉值本身需要的名字，于是类只能在「写 `self.include_views`（把方法遮住）」与「把值藏到 `get_params()` 得四处去找的地方」之间二选一。
- **未赋值的可选参数会输出为 `null`，而不是被省略。** 这是安全的：反序列化会把它传回去，构造函数的默认值随之生效。真正不安全的是丢掉一个取值与其默认值不同的参数——那才是往返丢掉的状态。

## 错误契约

读侧能拒绝的一切都以 `ExpressionDeserializationError` 浮现，所以调用方只捕获这一种类型：

```
ExpressionDeserializationError
├── ArtifactError                    —— 工件本身不合法
└── 注册表拒绝，被改述               —— 该 kind 在此不被接纳
```

`ArtifactError` 是**子类**，所以 `except ExpressionDeserializationError` 两者皆覆盖。`RegistryError` 不会到达调用方：解码层把它改述成自己的词汇，因为注册表是更底层的东西，不该知道读方捕获什么。

你自己构造函数抛出的 `TypeError` **不会**被替你捕获。携带 `{"name": 123}` 的工件，在构造函数不做检查时会毫无怨言地重建。要紧的话就在 `__init__` 里校验——反序列化的职责是按名字把值交出去，而不是判断它们可不可接受。

## 参数约定（JSON 标量）

**保留键已经一个都没有了。** 工件是普通 JSON，所以参数的取值必须本来就是 JSON
说得出来的东西：null、布尔、数字、字符串、数组，或对象。

这给自定义表达式两项义务、一个选项。

- **封闭取值集合取字符串枚举。** 声明成 `(str, Enum)`，并设 `__str__ = str.__str__`，
  让成员**就是**它渲染出来的那个词——单靠 `(str, Enum)` 做不到，`Enum.__str__` 会赢。
  这样线上形态就是成员的值，即一个 JSON 字符串，而封闭集合声明在代码里，各语言也都能
  各自声明。不继承 `str` 的枚举根本写不出去。
- **送进数据库的值放进 `Literal`。** 这是唯一允许出现 JSON 拼不出的类型的位置；
  由 `LiteralKind` 的成员指明那种文本。
- **不透明载荷是危险所在。** 键不由你控制的 `dict` 会被原样复制进工件，而给参数换个名字
  对它的**内容**毫无帮助。一个恰好读起来像节点（`kind` 加 `params`）的键会被当成节点读回来。
  要么在构造时校验，要么把载荷存成文本。

```python
# 错误示例 - 键不由你控制的 dict 参数
class RawJsonStorageExpr(BaseExpression):
    def __init__(self, dialect, data: dict):
        super().__init__(dialect)
        self.data = data  # 里面若有 {"kind": ..., "params": ...} 会被当成节点读回来

# 正确示例 - 在进入工件之前就拒绝这种形状
class SafeJsonStorageExpr(BaseExpression):
    def __init__(self, dialect, json_data: dict):
        super().__init__(dialect)
        if set(json_data) & {"kind", "params"}:
            raise ValueError("载荷不得携带形似节点的键")
        self.json_data = json_data
```

## 相关文档

- [核心文档](./serialization.md)：序列化机制说明
- [格式参考](./format-reference.md)：工件完整规范