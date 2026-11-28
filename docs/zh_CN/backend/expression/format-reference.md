# 工件格式参考

`serialize()` 写什么、`deserialize()` 读什么的完整规格。这里的每一条都由代码强制，而不只是被描述。

> **可运行**：`docs/examples/expression_artifact.py` 把整份走了一遍。

## 节点结构

工件是**裸节点，无信封**（§4.11.3）：

```python
{
    "kind": str,           # 必需：节点的 kind
    "params": dict         # 必需：构造参数
}
```

| 字段 | 类型 | 约束 |
|------|------|------|
| `kind` | str | 非空；必须在读方的注册表里 |
| `params` | dict | 键名须匹配目标类的 `__init__` 参数名 |

没有版本、生产者、捕获的方言、连接指纹，节点层面也没有 `kind`、`params` 之外的任何字段。节点多带任何东西都会**按名拒绝**，所以残留的信封字段不可能蒙混过关。

## kind 从哪来

`kind` **由类名算出**，从不存储：类名的 snake_case 形式，连续大写算一个词（`JSONValue` → `json_value`）。类身上没有 kind 字段，所以两者不可能走偏。

**参数**同样适用这条规则：它的 kind 就是 `parameter`，params 就是构造参数 `value` 与 `inline`。它承载哪一种值并不是身份——宿主值原样携带，不额外写类型名。存日期与存字符串的两个参数是同一个 kind，读方也无法从工件推断宿主类型。

## 参数

`params` 承载除 **`dialect`** 外的全部构造参数——方言是上下文，永不随行：同一份工件可以交给读方手上的任意方言对象重渲染。

每个构造参数是三种形态之一：

- **语言无关的 JSON 值**（null、布尔、数字、字符串、数组或对象）
- **原样携带的宿主值**——即 `Parameter` 的 `value`
- **表达式**，写成就地嵌套的 `{kind, params}` 节点

**没有第四种形态**，嵌套节点和值外面都**没有标记**——形状与节点自身的 params 就是信号。宿主值能否写成 JSON 是它自己类型的契约，不是序列化器规则。`set`、驱动句柄、闭包、pickle 出来的 blob 都没有语言无关编码；若要让它们走过 JSON 往返，就让值类型可序列化、给 `serialize_json(...)` 传 `default=`（转发给 `json.dumps`），或者把它们建模成表达式。

## 标记类型

**一个也没有。**

工件里只有 JSON：null、布尔、数字、字符串、数组，以及要么是节点、要么是普通映射的对象。嵌套表达式是裸的 `{kind, params}` 节点；`Parameter` 承载的值原样放在 `params.value` 里。它能否写成 JSON 是值类型自己的契约——序列化器不加标记，也不查规则。

这不是简化。标记是一种**派发**——读方必须认出这个键并知道它意味着什么——而派发是每种语言都要重新实现一遍的东西。工件要求跨实现逐字节一致，所以凡是读方需要派发的东西，都必须是各语言天然一致的东西。JSON 标量不需要一致：每种语言本来就能解析它。

## 标量类型规则

| Python 类型 | JSON 形态 | 说明 |
|-------------|-----------|------|
| `str` | string | `str` 基枚举就是其中之一——它**就是**它的值 |
| `int` | number | 任意精度；读不下的一方必须显式失败 |
| `float` | number | 要活下来的是 IEEE 754 位型，不是文本 |
| `bool` | boolean | |
| `None` | null | |
| `list` | array | 元素递归处理 |
| `tuple` | array | 以数组出行。结构性元组由构造函数还原为元组；元组**值**回来也是数组——读方无法推断宿主类型 |
| `dict` | object | 值递归处理 |
| `BaseExpression` | object | 裸嵌套节点 |
| `set` | — | 不支持；转成 list |
| 驱动句柄、闭包、任意对象 | — | 无语言无关编码；建模成表达式 |

本表针对的是**结构性参数**——决定树形状的构造参数。位于值位的值则不同：它是一个 `Parameter` 节点，其 `value` 原样携带。

### 每个参数值都原样出行

**送进数据库**的值由 `Parameter` 承载，并**原样**出行——没有文本形式、没有类型名、没有转换：

```python
# Parameter(dialect, 18)
{"kind": "parameter", "params": {"value": 18, "inline": false}}
```

能否被 `json.dumps` 写出，是**值类型自己的契约**。让值类型本身可 JSON 序列化，或给 `serialize_json(...)` 传 `default=`（转发给 `json.dumps`）。序列化器不转换、不命名、不校验、不拒绝值类型：`json.dumps` 失败是调用方的问题，不查任何序列化器规则。读侧 `deserialize_json(..., object_hook=...)` 把 `object_hook=` 转发给 `json.loads`，供调用方还原自己的值；编解码器本身不用钩子。

`deserialize` 原样交回值——不做类型派发，也不拆包。`None` 仍是 JSON null（SQL NULL）；元组以 JSON 数组出行，回来也是数组，读方无法推断宿主类型。这里要分清三件事：`parameter` **节点**（kind 为 `parameter`）、`SQLValue`／值结果类型（说明表达式产出什么），以及 JSON 原生值契约（`json.dumps` 能否写出）。

### 原始值与内联位置

调用方不必手工构造 `Parameter`。在**值位**——比较操作数、`IN` 列表、`BETWEEN` 边界、`LIKE` 模式、函数实参、`INSERT`/`UPDATE` 的值、DDL 默认值——框架会把普通 Python 值自动包成 `Parameter`。于是 SQL 文本里永远只有占位符，值走 `params`，调用方不会把它拼进 SQL。**名字位**则不做这种包装：表名、列名、`ORDER BY` 项始终是标识符，那里的字符串 `"id"` 不是值 `'id'`。

`inline` 是**内部决策**，既不是调用方声明的类型，也不是第二种 kind。它用于不接受占位符的语法位置——DDL 的 `DEFAULT`、`CHECK` 操作数、部分索引 `WHERE`——此时格式化器向方言的 `format_literal(value)` 取转义后的 SQL 文本，值不再进入**绑定参数列表**（但仍留在工件的 `params.value` 里）。默认值 `inline: false` 表示绑定，这是所有 DQL/DML 数据位想要的。两种情况都用同一个 `parameter` kind 序列化，只有这个标记不同。

## 序列化流程

1. 读 `get_params()`——每个 `__init__` 参数读一个同名属性，`dialect` 除外。
2. 逐个处理取值：`BaseExpression` 变嵌套节点；list、tuple、dict 递归；其余取值（包括 `Parameter` 的 `value`）原样携带。
3. 产出 `{"kind": ..., "params": ...}`。

**不查注册表。** 节点自带 kind，所以只做序列化的调用方永远不必构造查找表。

## 反序列化流程

工件是**不可信输入**（§4.11.4）。

1. 拒绝携带 `kind`、`params` 之外任何字段的节点。
2. 通过注册表白名单解析 `kind`。工件从不指名模块：表里已经为这个 kind 存着全限定类名，解析时 import 的只有这个名字。表里没有的 kind 按名拒绝。
3. 要求 `params` 是对象，并把每个键与解析出的类的 `__init__` 对照——无法识别的参数与缺失的必填参数各自按名失败。
4. 拒绝声明了 `**kwargs` 的类：一个身份取决于「来了多少个额外参数」的参数，在读侧无法按名匹配。
5. 递归解码各取值，**按名字**交给构造函数。解码器自己不做类型判断——校验属于 `__init__`，那里能指名是哪个类、哪个参数。
6. 限制嵌套深度（默认 64）与总长度。

### 失败

每一次拒绝都指名它拒绝了什么，因为一份你并非亲手写出的产物，没法靠猜来调试：

| 情况 | 消息 |
|------|------|
| kind 未被接纳 | `kind 'x' is not in the kind whitelist (N kinds registered)` |
| 残留信封字段 | `artifact node has unexpected field(s) ['dialect']` |
| 缺失 kind | `artifact node has no usable 'kind' (got None)` |
| 无法识别的参数 | `kind 'x' does not accept parameter(s) [...]` |
| 缺失必填参数 | `kind 'x' is missing required parameter(s) [...]` |
| 声明了 `**kwargs` | `kind 'x' accepts **kwargs, so its parameters cannot be matched by name` |
| 嵌套过深 | `artifact nesting depth exceeds 64` |

`json.dumps` 失败不在其中：那是 `json.dumps` 抛出的，不是序列化器的值类型规则。

全部是 `ArtifactError`，而它继承自 `ExpressionDeserializationError`——所以调用方捕获这一种即可。`RegistryError` 不会外泄：解码层把它改述成自己的词汇，因为注册表是更底层的东西，不该知道读方捕获什么。

## 相关文档

- [核心文档](./serialization.md)
- [扩展指南](./extending.md)