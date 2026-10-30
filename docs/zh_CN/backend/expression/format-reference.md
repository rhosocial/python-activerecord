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

没有 `type`、没有 `module`、没有版本、生产者、捕获的方言、连接指纹。节点携带 `kind` 与 `params` 之外的任何东西都会**按名拒绝**，所以残留的信封字段不可能蒙混过关。

## kind 从哪来

`kind` **由类名算出**，从不存储：类名的 snake_case 形式，连续大写算一个词（`JSONValue` → `json_value`）。类身上没有 kind 字段，所以两者不可能走偏。

**字面量**是唯一一个 kind 不等于类名的节点。一个节点承载全部值，而线上仍把它们分开命名——`null_value`、`integer_value`、`date_value`……因为日期与字符串的字节形态相同，只有 kind 能区分。值 kind 才是节点在线上的身份；`Literal` 只是它们全部解析到的那个类。

## 参数

`params` 承载除 **`dialect`** 外的全部构造参数——方言是上下文，永不随行：同一份工件可以交给读方手上的任意方言对象重渲染。

每个参数恰好是两种形态之一：

- **语言无关标量**（JSON 原生，或下列标记之一）
- **表达式**，写成就地嵌套的 `{kind, params}` 节点

**没有第三种形态**，嵌套节点外面也**没有标记**——形状本身就是信号。`set`、驱动句柄、闭包、pickle 出来的 blob 都没有语言无关编码，因此不可序列化；要把它们建模成表达式。

## 标记类型

**一个也没有。**

工件里只有 JSON：null、布尔、数字、字符串、数组，以及要么是节点、要么是普通映射的对象。嵌套表达式是裸的 `{kind, params}` 节点；JSON 说不出的值则以它的 kind 所命名的文本形式出行。

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
| `tuple` | array | 是「对」还是「列表」由参数声明的类型说明，构造函数负责还原 |
| `dict` | object | 值递归处理 |
| `BaseExpression` | object | 裸嵌套节点 |
| `set` | — | 不支持；转成 list |
| 驱动句柄、闭包、任意对象 | — | 无语言无关编码；建模成表达式 |

### 绑定值是唯一的例外

**送进数据库**的参数可以持有 JSON 无从拼写的类型。它由 `Literal` 包裹，其 kind 指明那种文本：

| kind | 承载 | 线上形态 |
|------|------|---------|
| `binary_value` | `bytes` | base64 字符串 |
| `interval_value` | `timedelta` | ISO 8601 字符串——天/时/分/秒，因为年月长度不固定 |
| `decimal_value` | `Decimal` | 精确十进制文本，绝不降级成浮点 |
| `timestamp_value` / `date_value` / `time_value` | 日期与时间 | ISO 文本 |
| `uuid_value` | `UUID` | 规范文本 |

kind 在这里存在的全部理由就在于此：日期与字符串的字节形态相同，只有 `date_value` 能区分。构造函数收下标量并转换。

## 序列化流程

1. 读 `get_params()`——每个 `__init__` 参数读一个同名属性，`dialect` 除外。
2. 逐个处理取值：`BaseExpression` 变嵌套节点；list、tuple、dict 递归；其余必须已经是 JSON 标量。
3. 产出 `{"kind": ..., "params": ...}`。

**不查注册表。** 节点自带 kind，所以只做序列化的调用方永远不必构造查找表。

## 反序列化流程

工件是**不可信输入**（§4.11.4）。

1. 拒绝携带 `kind`、`params` 之外任何字段的节点。
2. 通过注册表白名单解析 `kind`。没有 import 路径，也没有反射：一个名字要么已登记，要么按名拒绝。
3. 要求 `params` 是对象，并把每个键与解析出的类的 `__init__` 对照——无法识别的参数与缺失的必填参数各自按名失败。
4. 拒绝声明了 `**kwargs` 的类：一个身份取决于「来了多少个额外参数」的参数，在读侧无法按名匹配。
5. 递归解码各取值，**按名字**交给构造函数。解码器自己不做类型判断——校验属于 `__init__`，那里能指名是哪个类、哪个参数。
6. 限制嵌套深度（默认 64）与总长度。

### 失败

每一次拒绝都指名它拒绝了什么，因为一份你并非亲手写出的产物，没法靠猜来调试：

| 情况 | 消息 |
|------|------|
| kind 未被接纳 | `kind 'x' is not in the kind whitelist (N kinds registered)` |
| 残留信封字段 | `artifact node has unexpected field(s) ['type']` |
| 缺失 kind | `artifact node has no usable 'kind' (got None)` |
| 无法识别的参数 | `kind 'x' does not accept parameter(s) [...]` |
| 缺失必填参数 | `kind 'x' is missing required parameter(s) [...]` |
| 声明了 `**kwargs` | `kind 'x' accepts **kwargs, so its parameters cannot be matched by name` |
| 嵌套过深 | `artifact nesting depth exceeds 64` |

全部是 `ArtifactError`，而它继承自 `ExpressionDeserializationError`——所以调用方捕获这一种即可。`RegistryError` 不会外泄：解码层把它改述成自己的词汇，因为注册表是更底层的东西，不该知道读方捕获什么。

## 相关文档

- [核心文档](./serialization.md)
- [扩展指南](./extending.md)