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
from rhosocial.activerecord.backend.expression_registry import serialize

artifact = serialize(query)
```

宿主值都是 JSON 原生类型时，普通 `json.dumps` 就够了——`serialize_json` 就是替你调它的简写：

```python
text = json.dumps(artifact)          # 或：text = serialize_json(query)
```

JSON 拼不出的值是**调用方**的责任：让值类型本身可 JSON 序列化，或给
`serialize_json(...)` 传 `default=`（会转发给 `json.dumps`）。没有钩子时，`json.dumps`
写不出的值就是调用方自己的问题。`serialize` 原样携带宿主值，不转换、不命名、不校验、不拒绝任何值类型。

### deserialize(artifact, *, registry=None)

```python
from rhosocial.activerecord.backend.expression_registry import deserialize

expr = deserialize(json.loads(text))
```

编解码器**不需要 `object_hook`**——也没有钩子可做的事。工件通篇是普通 JSON：节点是 `{kind, params}`，`params` 里的取值是标量、数组、对象或嵌套节点。**没有任何标记**，所以节点凭形状被认出，在 `deserialize` 看到它之前没有东西需要解码。`deserialize_json(text, *, registry=None, object_hook=None)` 仍接受一个可选的 `object_hook=`，并把它转发给 `json.loads`，供调用方还原自己的值；编解码器本身从不使用它。送进数据库的值由 `parameter` 节点**原样**携带：`deserialize` 直接交回，不做类型派发，也不拆包。`None` 仍是 JSON null（SQL NULL）；元组以 JSON 数组出行，回来也是数组——读方无法推断宿主类型。

`registry=None` 意味**核心的表**，不是一张框架级默认表。要读某个后端自己的 kind，传它发布的表（例如 `SQLITE_EXPRESSION_REGISTRY`）；见下文「注册表归属」。

### serialize_json(expr, *, default=None) / deserialize_json(text, *, registry=None, object_hook=None) / deserialize_xml(payload, *, registry=None)

同一份工件的三种渲染：字典、JSON 文本、XML 文档。三者都重建同一个实例；**参数、以及事后由它渲染出的 SQL，都必须原样回来**。在 JSON 这一种渲染上，`default=` 转发给 `json.dumps`，`object_hook=` 转发给 `json.loads`；两者都是调用方为自己持有的值准备的钩子，编解码器两个都不用。

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
        "table": {"kind": "table", "params": {"name": "users"}},
        "alias": None,
    }
}
```

构造参数的取值可以是**语言无关标量**、原样携带的宿主值（`Parameter` 的 `value`），或**表达式**。最后一种形态（嵌套的 `{kind, params}` 节点）是同一件事的不同层面：内存里是活实例，链路上是编码节点。不加包裹，也不加类型标记——这正是工件可读的原因。

注意嵌套表达式**外面没有任何包裹**。形状本身就是全部信号，因此没有东西需要拆开，也不存在「这是节点」的第二个、更弱的说法。
`__expr__` 信封会让同一件事有两种写法，读方就得猜载荷用的是哪一种。

注意**没有什么**：**序列化和反序列化都不处理方言**。序列化时忽略方言——`get_params()` 排除构造函数的 `dialect` 参数，所以工件里不会写入任何方言实例。反序列化时同样忽略——工件没有方言字段可读，重建出来的树是**未绑定的**：此时读 `node.dialect` 会报错，必须先绑定方言。

如果你需要一棵已绑定的树，就由自己递归地把方言注入到重建树的每个节点：

```python
from rhosocial.activerecord.backend.expression import BaseExpression

def bind_dialect(node, dialect):
    for value in node.get_params().values():
        if isinstance(value, BaseExpression):
            bind_dialect(value, dialect)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, BaseExpression):
                    bind_dialect(item, dialect)
        elif isinstance(value, dict):
            for item in value.values():
                if isinstance(item, BaseExpression):
                    bind_dialect(item, dialect)
    node.dialect = dialect
    return node

tree = bind_dialect(deserialize(artifact), SQLiteDialect(version=(3, 53, 0)))
```

如果只是渲染一次，可以跳过注入，把方言交给 `to_sql(dialect)`——它只在渲染时绑定，不改变树本身：

```python
deserialize(artifact).to_sql(SQLiteDialect(version=(3, 53, 0)))
```

## 绑定参数

`to_sql()` 返回一对——语句与待绑定的值：

```python
sql, params = expr.to_sql()
# ("SELECT ... WHERE age > ?", (18,))
```

那个 `18` **哪儿都没被单独存过**。它是从载荷里的 `parameter` 节点读出来的——宿主值原样携带：

```python
{"kind": "parameter", "params": {"value": 18, "inline": false}}
```

送进 SQL 的每个值都是一个 `parameter` 节点。**值位置**（比较操作数、`IN` 列表、`BETWEEN` 边界、`LIKE` 模式、函数实参）上的裸 Python 值，框架在构造时自动包成 `Parameter`，所以 SQL 文本里永远只有占位符，值走 `params`。同一个类也服务于内联位置：`inline` 是**不接受占位符的语法位置**（如 DDL 的 `DEFAULT`、`CHECK` 操作数）的内部决策，此时格式化器向方言的 `format_literal(value)` 取转义后的 SQL 文本。

**名字位**则不做这种包装：表名、列名、`ORDER BY` 项始终是标识符，那里的 `"id"` 不是值 `'id'`。

`parameter` 是普通的 `BaseExpression` 节点：kind 由类名派生（`parameter`），params 就是构造参数 `value` 与 `inline`。没有类型名，也没有转换或校验。能否被 `json.dumps` 写出，是**值类型自己的契约**——让值类型本身可 JSON 序列化，或给 `serialize_json(...)` 传 `default=`（转发给 `json.dumps`）。`json.dumps` 失败是调用方的问题，不是序列化器规则。

## 注册表归属

注册表不是框架的一张总表，而是**每个所有者自己的一张**，所有者就是声明这些 kind 的表达式包。每张表都是普通数据——一个 `kind -> 全限定类名` 的映射：

| 所有者 | 入口 | 内容 |
|--------|------|------|
| 核心 | `CORE_EXPRESSIONS` → `CORE_EXPRESSION_REGISTRY` | 只有核心的 kind，不含任何后端 |
| 后端 | `SQLITE_EXPRESSIONS` / `SQLITE_EXPRESSION_REGISTRY`、`DUMMY_EXPRESSIONS` / `DUMMY_EXPRESSION_REGISTRY` | 核心的 kind ∪ 本后端自己的 kind，绝不含兄弟后端 |

- **核心收集自己的包。** `CORE_EXPRESSIONS` 是对核心自己的各个包运行 `collect_expressions`、再合并这些映射的结果——**只有节点 kind**，`parameter` 也在其中；`CORE_EXPRESSION_REGISTRY` 是 `ExpressionRegistry(CORE_EXPRESSIONS).freeze()`，在模块导入时**一次性**构造。核心不知道有哪些后端存在，也没有后端清单。
- **后端通过字典合并加入自己的 kind**：`merge_expressions(CORE_EXPRESSIONS, SQLITE_EXPRESSIONS)`——即并集 `{**CORE_EXPRESSIONS, **SQLITE_EXPRESSIONS}`，若两张映射用不同的类声明同一个 kind 则直接报错。两个后端从不互相合并，因此一个后端的 kind 不会因为另一个后端被安装而变得可读。
- **方言完全不参与。** 方言只是渲染器，既不拥有表，也不选表。
- 工件本身仍然是**不带方言的数据**：`deserialize(artifact)` 返回的树不绑定方言，用 `to_sql(dialect)` 渲染。

`deserialize` 用的表是：

1. 调用方显式传入的 `registry`；
2. 否则 `CORE_EXPRESSION_REGISTRY`。

已发布的注册表是**冻结的**。要放宽或收窄，可以从 `twin()`（可变副本）或 `merged()`（并集，冻结）出发，也可以用你自己合成的映射构造一张新的 `ExpressionRegistry(kinds)`。别人的装配或修改不会改变一张已发布的表。

## 有哪些表达式

回答“有哪些表达式”不必翻源码树——注册表就是答案，而且它是可以打印的普通数据：

```python
from rhosocial.activerecord.backend.expression_registry import CORE_EXPRESSIONS
from rhosocial.activerecord.backend.impl.sqlite.expression_registry import (
    SQLITE_EXPRESSIONS, SQLITE_EXPRESSION_REGISTRY,
)

for kind, fqn in sorted(CORE_EXPRESSIONS.items()):
    print(kind, "->", fqn)

core_kinds = sorted(CORE_EXPRESSIONS)                       # 核心声明的
own_kinds = sorted(SQLITE_EXPRESSIONS)                      # sqlite 后端自己的
readable = sorted(SQLITE_EXPRESSION_REGISTRY.node_kinds())  # 核心 + sqlite
```

`<NAME>_EXPRESSIONS` 是某个所有者的 `kind -> 全限定类名` 映射；`<NAME>_EXPRESSION_REGISTRY.node_kinds()` 才是读者真正会用的表——核心与那个后端的并集。两者都由所有者在导入时发布，并且是从节点类本身推导出来的，所以今天打印出来的清单不会悄悄地与代码脱节。

**这份清单同时也是序列化契约。** 表里的 kind 就是编解码器能写出、也能读回的节点；不在表里的 kind，读取时会按名字被拒绝。`serialize` 不需要表，因为节点自己报告 kind；`deserialize` 则只接受所选注册表认可的东西。因此，打印出来的映射恰好就是本库承诺可以往返的表达式集合：**写入不受限制，读取才是注册表的承诺。**

**合并并不等于“支持”。** 后端表只是 `{**CORE_EXPRESSIONS, **<NAME>_EXPRESSIONS}` 的字典并集。它说明读者能从工件重建这些节点类，**并不意味着**该后端的方言能渲染其中每一个节点。格式化是方言的职责，由它的 `format_*` 方法决定，注册表完全不查这些。一个核心节点即使该方言从未实现它的 formatter，依然能顺利反序列化，然后在 `to_sql()` 处失败。**读侧接纳**与**渲染侧支持**是两份不同的契约，这里发布的只是前者。

**支持还会随方言版本变化。** 登记表不带版本信息：无论用哪个 SQLite 版本渲染，`sqlite_returning_clause` 这个 kind 都在 SQLite 的表里。`SQLiteDialect(version=(3, 34, 0))` 会拒绝 `(3, 35, 0)` 能渲染的 RETURNING 子句，因为 `supports_returning_*()` 做了版本门控。表回答的是“这是个合法的表达式身份吗”，方言版本回答的是“这个具体版本能渲染它吗”。要问能力，问方言，别问注册表。

有两点让它足以依赖：

- kind 是类名的 snake_case 形式，不是文件路径。把节点在命名空间目录之间移动，会改变它的全限定类名，但**不改变 kind**，所以工件里的身份能扛住代码组织的调整。
- 宿主值没有自己的 kind。所有值都走同一个 `parameter` 节点，因此接纳 `"parameter"` 就接纳了任意类型的值；值能否被 `json.dumps` 写出，仍是调用方的责任。

## 选择性注册

注册表是**读侧边界**：它过滤的是工件**实际携带**的 kind，不是类**声明过**的参数类型。参数保持默认值就不产生节点，因而也不需要登记。

```python
from rhosocial.activerecord.backend.expression_registry import (
    CORE_EXPRESSION_REGISTRY,
    ExpressionRegistry,
)

read_only = ExpressionRegistry()
for kind in ("query_statement", "where_clause", "comparison_predicate",
             "column", "table", "parameter"):
    read_only.register_node(CORE_EXPRESSION_REGISTRY.resolve_node(kind))

deserialize(artifact, registry=read_only)
```

选择性表要放行值，只需放行 `"parameter"`：不论它携带什么值，每个参数都是这一个节点，所以没有按值区分的 kind 需要登记。`CORE_EXPRESSIONS` 只有节点 kind，`parameter` 也在其中。

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

值无法被 `json.dumps` 写出不属于这些拒绝：那是 `json.dumps` 抛出的错误，序列化器不查任何值类型规则。

## 使用场景

### 缓存查询计划

```python
stored = json.dumps(serialize(query))
# ……之后，在另一个进程
query = deserialize(json.loads(stored))          # 核心的表
query.to_sql(SQLiteDialect(version=(3, 53, 0)))  # 在渲染时选用方言，而不是在读时
```

缓存里存的是 JSON 文本，因此任何存字符串的缓存都能放。读侧只重建一棵树，仅此而已；**方言在渲染时选定**，所以一份缓存服务所有后端。由后端自有 kind 构造的载荷，用该后端发布的表读取（`registry=SQLITE_EXPRESSION_REGISTRY`）；方言在读侧仍然完全不参与。

### 分布式任务调度

worker 收到文本，重建树，再用它自己的方言渲染。**载荷里没有任何东西**绑在产出它的那台机器上。

## 安全考虑

### 工件里的名字永远到不了 import

解析只走白名单，永不走 import 路径。载荷里写 `os.system` 得到的答复是「不在 kind 白名单」——它被查了、查不到、读取失败。唯一能到达 import 的名字，是表里**已经**为某个 kind 存着的那个全限定类名：登记内容是可信数据，而工件只提供 kind，别的一概提供不了。

注册表里的任何东西都不会自作主张 import 表达式包。`collect_expressions` 只 import 交给它的那**一个**包名：核心交的是自己的那些包，后端交的是自己的包，然后把返回的映射发布出去。这里**没有**通用包遍历器，所以没有任何东西被发现；一张表之所以存在，是因为某个所有者收集了一个包并明确发布了它。

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