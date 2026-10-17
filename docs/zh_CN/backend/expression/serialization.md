# 表达式序列化

> **可运行示例**：`docs/examples/expression_artifact.py`。下文每一条都在那里端到端跑过。

## 设计动机

表达式是**值对象**：同一个查询构造两次必须相等；它还必须能被写下来、在别处（缓存、队列、另一个进程）读回来。

工件就是为此存在的。它刻意做得很小，而形状只由一个决定推导出来：**工件里不带 import 路径**。载荷里出现点分路径，正是会迫使读方去 import 那个字符串所指模块的东西，而工件是不可信输入。所以节点用 **kind** 指认——类名的 snake_case 形式——无论在内存还是在链路上，这个 kind 就是节点的身份。

由此有两条值得先说清的推论：

- **写不需要注册表。** 节点自己会报告 kind，由类名派生。只做序列化的调用方**永远不必构造查找表**。
- **读需要一张。** 把 kind 变回某个类，只有表能回答；而**用哪张表由调用方决定**。

## 核心 API

### serialize(expr)

```python
from rhosocial.activerecord.backend.expression.serialization import serialize

artifact = serialize(query)
```

工件是 JSON 原生的，因此直接走普通 `json.dumps`，不需要自定义 encoder：

```python
text = json.dumps(artifact)
```

### deserialize(artifact, dialect, registry=None)

```python
from rhosocial.activerecord.backend.expression.serialization import deserialize

expr = deserialize(json.loads(text), dialect)
```

`json.loads` **不需要 `object_hook`**。格式使用的标记
（`__expr__`、`__value__`、`__enum__`、`__tuple__`、`__dataclass__`）本身就是普通 JSON 值；解码是编解码器的职责，发生在 `deserialize` 内部，而不是 JSON 钩子里。

`registry=None` 表示框架默认实例——本发行版自带的全部节点。传自己的表，就精确控制这次读允许产出哪些 kind。

### deserialize_json(text, dialect, registry=None) / deserialize_xml(bytes, ...)

同一份工件的三种渲染：字典、JSON 文本、XML 文档。三者往返到同一个实例；**参数与渲染出的 SQL 都必须原样回来**。

## 工件格式

**裸节点，无信封。**

| 字段 | 类型 | 说明 |
|------|------|------|
| `kind` | str | 节点的 kind（如 `column`、`comparison_predicate`） |
| `params` | dict | 构造参数，键名与 `__init__` 参数名一致 |

就这些——**没有**版本、生产者、捕获的方言、连接指纹。

```python
# Column("users", "id")
{
    "kind": "column",
    "params": {
        "name": "id",
        "table": {"__expr__": {"kind": "table", "params": {"name": "users"}}},
        "alias": None,
    }
}
```

参数要么是**语言无关标量**，要么是**表达式**。第二种形态（`__expr__` 包裹的嵌套节点）是同一件事的不同层面：内存里是活实例，链路上是编码节点。**没有第三种形态**——这正是工件可读的原因。

注意**没有什么**。工件不带方言，所以同一份载荷可以交给任意方言对象重渲染：

```python
deserialize(artifact, SQLiteDialect(version=(3, 53, 0))).to_sql()
```

## 绑定参数

`to_sql()` 返回一对——语句与待绑定的值：

```python
sql, params = expr.to_sql()
# ("SELECT ... WHERE age > ?", (18,))
```

那个 `18` **哪儿都没被单独存过**。它是从载荷里的 `literal` 节点读出来的，所以没有第二处携带它，也就没有第二处可能与它不一致。表达式从不把值拼进 SQL 文本；数据库永远看不到字符串拼接出来的引号。

## 选择性注册

注册表是**读侧边界**：它过滤的是工件**实际携带**的 kind，不是类**声明过**的参数类型。参数保持默认值就不产生节点，因而也不需要登记。

```python
from rhosocial.activerecord.backend.expression.registry import ExpressionRegistry

read_only = ExpressionRegistry()
for kind in ("query_statement", "where_clause", "comparison_predicate",
             "column", "literal", "table"):
    read_only.register_node(default_registry().resolve_node(kind))

deserialize(artifact, dialect, registry=read_only)
```

不带分组的查询在这张表下读得通；带 `GROUP BY` 的会被按名拒绝。这就是权限形态：**这个通道不接受的东西，发给它也变不出来。**

要讲清注册表**不**做什么。`serialize` 不查注册表，所以窄表**阻止不了写出**，也**决定不了执行**。它管的是：读者从一份自己没写过的产物里能还原出什么。**一个必须在写侧成立的边界需要另一套机制**——因为写方与执行方同进程。

## 错误处理

每一次拒绝都指名它拒绝了什么，因为一份你并非亲手写出的产物，没法靠猜来调试。

| 情况 | 错误 |
|------|------|
| 无人登记的 kind | `kind 'x' is not in the kind whitelist` |
| 残留的信封字段 | `a bare node carries exactly 'kind' and 'params'` |
| 无法识别的参数 | `kind 'x' does not accept parameter 'y'` |
| 缺失 kind | `the kind is the node's identity and is mandatory` |
| 嵌套超过深度上限 | `artifact nesting depth exceeds N` |

## 使用场景

### 缓存查询计划

```python
stored = json.dumps(serialize(query))
# ……之后，在另一个进程
query = deserialize(json.loads(stored), dialect)
```

缓存里存的是 JSON 文本，因此任何存字符串的缓存都能放；而方言在**读时**选定——一份缓存服务所有后端。

### 分布式任务调度

worker 收到文本，用它自己的方言重建树。**载荷里没有任何东西**绑在产出它的那台机器上。

## 安全考虑

### 工件里的名字永远到不了 import

解析只走白名单，永不走 import 路径。载荷里写 `os.system` 得到的答复是「不在 kind 白名单」——它被查了、查不到、读取失败。**不存在**任何可能 import 它的代码路径。

注册表模块**根本不 import** 表达式包；装配默认实例的机制属于框架，不属于注册表。**注册表无法发现任何东西。**

### 工件是不可信输入

- 未知 kind、残留字段、无法识别的参数，一律按名失败。
- 嵌套深度与长度有上限。
- **这里不做方言层校验**——那属于 `to_sql()`，支持性问题归它管。

### 不要手工编辑工件

```python
# 正确：构造树，交给编解码器写
text = json.dumps(serialize(query))

# 错误：手工拼装载荷等于把自己绑在一个库不承诺保持的格式上，
# 而一份你并非亲手写出的产物，恰恰是读方设计上就不信任的输入。
```

## 相关文档

- `docs/examples/expression_artifact.py` —— 可运行的端到端示例
- `.claude/plan/2026-10-12/表达式-方言架构规则.md` §7、§10 —— 注册表与工件规则