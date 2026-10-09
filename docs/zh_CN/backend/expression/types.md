# 数据类型 (Data Types)

数据类型（`DataType`）是表达式系统的重要组成，用于在 DDL、模型字段声明与迁移中描述数据库列的类型。

数据类型遵循与表达式系统相同的**通用 / 特定后端**分层设计，并且二者通过「通用基类 + 后端子类」的方式紧密配合。

## 概述

`DataType` 继承自 `BaseExpression`，并遵循**与其他表达式完全相同的绑定规则**：

> **方言绑定是逐节点的**：方言是约定俗成的**第一个构造参数——可选，默认 `None`**。可以在构造时传入，也可以推迟到之后通过 `dialect` 属性赋值。setter 只影响**被赋值的那个节点**——不会向子节点传播。

因此数据类型具有 **declare → bind → render** 的生命周期：

1. **declare**（声明）：类型可以在不携带方言的情况下构造——用于模型字段声明、迁移、`UseSqlType` 注解。省略方言时，其余参数必须**具名传参**（如 `VarCharType(length=255)`）；位置传参的值会落入方言槽位并被构造校验拒绝
2. **bind**（绑定）：按节点附加方言——或在构造时传入（`VarCharType(dialect, length=255)`），或稍后通过 `dialect` 属性 setter 赋值；方言的 `parse_type()` 工厂（内省）返回的也是已绑定的实例
3. **render**（渲染）：`to_sql()` **无参数**；它读取节点自身绑定的方言，委托给其 `format_data_type()`。对未绑定方言的类型调用渲染会抛出 `ValueError`（"... has no dialect bound ..."）——这是刻意的 fail-fast 护栏

```python
from rhosocial.activerecord.backend.expression.types import VarCharType

# declare：无需方言——其余参数必须具名传参
t = VarCharType(length=255)

# 稍后绑定（仅此节点），再渲染——to_sql() 无参数
t.dialect = dialect
sql, params = t.to_sql()
```

### 为什么方言参数是可选的？

数据类型遵循**与所有表达式相同的构造惯例**：方言是约定俗成的第一个参数，可选、默认 `None`（允许推迟赋值）。区别只在于两类表达式**通常被构建的时机**不同。

普通查询表达式（如 `Column`、`ComparisonPredicate`）在**查询执行时**构建，此时方言上下文必然已经存在，因此几乎总是立即传入方言：

```python
# 普通表达式：第一个参数是方言实例
Column(dialect, "name")          # ✅
Literal(dialect, 18)             # ✅
```

而数据类型经常需要在**方言尚不确定**的时机被创建。最典型的场景是 **`ActiveRecord` 模型字段声明**：

```python
from rhosocial.activerecord.base.fields import UseSqlType

class Product(ActiveRecord):
    size: Annotated[str, UseSqlType(MySQLEnumType(values=['S', 'M', 'L']))]
```

模型类在**导入时**就定义了字段类型注解，而模型此时**尚未配置任何后端**——方言要到之后 `configure(config, backend)` 时才确定。这正是「推迟绑定」的用武之地：先不带方言构造，之后再绑定。

`DDLSourceMixin` 只收集并保留 `UseSqlType` 中的候选，不会复制候选、选择候选或注入方言。后端 DDL 消费者在获得方言后，负责复制/绑定候选并构造可渲染表达式。详见 [DDLSource 声明收集](../../modeling/ddl_source.md)。

## 值对象语义

`DataType` 实例是**值对象**：同一类的两个实例只要逻辑参数相同就**相等且哈希相同**，与是否携带方言引用无关。相等性比较类型**声明过的身份**——即类常量 `PARAMETERS` 里列出的那些属性；哈希覆盖类型的类本身加上同一组属性。绑定的方言对二者都不产生影响——绑定（或重新绑定）方言绝不会改变 `==` 与 `hash` 的结果。

```python
a = IntegerType()
b = IntegerType()
assert a == b          # 值对象：相等（忽略方言）
assert hash(a) == hash(b)
```

数据类型的**类上并不存在**所谓的"后端专属选项字典"。后端在该概念自身参数之外需要的一切，都是类上**声明过的字段**——`CharType.length`、`DecimalType.precision`/`scale`、`EnumType.values`、`ArrayType.element_type`/`dimensions`，以及四个整数类上的 `unsigned: bool`——它们都列在该类的 `PARAMETERS` 里，因而同时参与 `==` 与 `hash`。

## 拼写 (Spellings)

有些概念存在不止一种合法写法。这些是**同一个类的拼写**，不是各自的类：该类带一个封闭的 `SPELLINGS` 元组与 `spelling` 关键字参数，其中**第一项**是默认值。

```python
IntegerType()                          # 拼写 "integer"
IntegerType(spelling="int")            # 同一个类，另一个词
assert IntegerType() != IntegerType(spelling="int")   # 两种不同的声明
```

为什么是一个类而不是两个：`INT` 与 `INTEGER` 是同一个类型，所以需要判断"这是不是整数列"的代码不该去枚举拼写，schema diff 也不该把两者报成差异。

**为什么拼写不参与 `==`。** 看似站得住的说法是：拼写属于当初声明的内容，所以它有差别就该报出来。但 schema diff 比较的**不是两份 DDL 脚本**，而是**数据库现在报什么** 对 **当初声明了什么**；而无论你当初写的是哪个词，数据库都只报它自己那一个词。PostgreSQL 对每一个 `varchar(30)` 列都报 `character varying(30)`，SQL Server 对声明为 `NUMERIC` 的列也报 `DECIMAL`。把拼写算进身份，就会在**唯一必须判对的那次比较**上，为每一个这类列报出一个根本没发生过的变更。

拼写的差异并没有丢：它仍然进渲染 SQL——差别真正存在且看得见的地方就是那里：

```python
IntegerType()                        # 渲染为 INTEGER
IntegerType(spelling="int")          # 渲染为 INT
```

它也仍然通过 `get_params()` 完成序列化往返，因为序列化问的是另一个问题——不是"这个值是什么"，而是"重建这个对象需要什么"——答案是构造签名。`get_params()` 是所有表达式唯一的序列化路径，任何类都不得覆写它。

某个**具体后端**接受哪些拼写是后端自己的事，并在后端的 formatter 里检查：不写 `CLOB` 的方言会抛错，而不是把调用方要求的 `CLOB` 悄悄改写成 `TEXT`。默认拼写始终可渲染——后端可以把它归一化成自己的写法，但绝不拒绝它。

## 通用类型 (Core Types)

通用类型定义在 `rhosocial.activerecord.backend.expression.types`，覆盖绝大多数数据库共有的 SQL 类型。有多种拼写的概念列出拼写；只有一种拼写的概念**根本没有** `spelling` 参数。

| 分类 | 类型类 | 拼写 |
|------|--------|------|
| 整数 | `TinyIntType`、`SmallIntType`、`IntegerType`、`BigIntType` | `tinyint`/`int1`、`smallint`/`int2`、`integer`/`int`、`bigint`/`int8` |
| 数值 | `FloatType`、`RealType`、`DoubleType`、`DecimalType` | `double`/`double precision`、—、—、`decimal`/`numeric`/`dec` |
| 字符串 | `CharType`、`VarCharType`、`TextType` | `char`/`character`、`varchar`/`character varying`、`text`/`clob` |
| 布尔 | `BooleanType` | `boolean`/`bool` |
| 二进制 | `BlobType`、`BinaryType`、`VarBinaryType` | `blob`/`bytea`、—、— |
| 枚举 | `EnumType`（values 必填） | — |
| 日期时间 | `DateType`、`TimeType`、`TimeTzType`、`DateTimeType`、`TimestampType`、`TimestampTzType`、`IntervalType` | — |
| JSON | `JsonType`、`JsonBType`、`XmlType` | — |
| UUID | `UUIDType` | — |
| 数组 | `ArrayType` | — |
| 自定义 | `CustomType` | — |

`TinyIntType`、`SmallIntType`、`IntegerType`、`BigIntType` 各自接受 `unsigned: bool`。有符号与无符号是**同一个类**——范围由参数携带——原因有二：线性的继承链装不下（宽度 × 符号性）这张网格；而且没有无符号整数的后端会选择加宽，而不是凭空造一个类。

`RealType`、`DoubleType`、`FloatType` 刻意是三个类：它们的取值范围与存储都不同，schema diff 必须看出这个差别；`DateTimeType` 与 `TimestampType` 同理。`JsonType` 与 `XmlType` 分开，是因为 SQL/JSON 与 SQL/XML 的操作集不同、标准不同，实现了其中一个的后端并不都实现另一个。

通用类型可以不带方言构造（延迟绑定），但绑定之前无法渲染。
| UUID | `UUIDType` |
| 数组 | `ArrayType` |
| 自定义 | `CustomType` |

通用类型可以在不带方言的情况下实例化（推迟绑定），但在绑定方言之前无法渲染。

## 特定后端类型 (Backend-Specific Types)

每个后端在通用类型之上定义自己的子类型，**命名以后端名为前缀**：

| 后端 | 示例 |
|------|------|
| SQLite | `SQLiteIntegerType(IntegerType)`、`SQLiteTextType(TextType)`、`SQLiteBlobType(BlobType)`、`SQLiteNumericType(DataType)` |
| MySQL | `MySQLIntType(IntegerType)`、`MySQLTinyIntType(TinyIntType)`、`MySQLEnumType(EnumType)`、`MySQLSetType(DataType)`、`MySQLGeometryType(DataType)` |
| PostgreSQL | `PostgresSerialType(IntegerType)`、`PostgresUUIDType(UUIDType)`、`PostgresXMLType(XmlType)`、`PostgresTSVectorType(DataType)`、`PostgresJsonPathType(DataType)` |

只要存在对应的通用概念，后端类型就**继承该概念的核心类型**——正是这一点让 `isinstance(col.data_type, IntegerType)` 对 PostgreSQL 的 `SERIAL` 列为真，而不必让每个调用方都记住各后端的私有类名。只有当概念确实是后端专属时才直接继承 `DataType`，此时 docstring 必须写清**为什么**没有对应的核心概念。

继承表达的是**同一性**——"这个类**就是**那个 SQL 类型"。它不用于把类型归入族系：SQL 的类型*分类*（数值、字符串、日期时间）是归属关系而非子类型关系，本框架没有任何地方会问"这是不是数值类型"。继承链是线性的：没有多继承，没有菱形边。

每个后端定义的类型都声明**带命名空间前缀的通用类型名**——以后端标识作为前缀（如 `SQLiteIntegerType.name == "sqlite_integer"`）。该前缀在类定义时（`__init_subclass__`）被强制校验：定义在核心 types 包之外、名称缺少后端前缀的类型会被直接拒绝，从而保证不同后端的分发键互不冲突。

## 通用与特定后端的配合

### 渲染：命名族分发，无注册表

类型**没有注册表**。方言的受支持类型面**就是**它的命名族方法集合——两个命名族之间存在严格的 1:1 对应关系：

- `format_data_type_<name>(data_type)` —— 渲染通用名为 `<name>` 的类型
- `supports_data_type_<name>() -> bool` —— 如实声明 `<name>` 是否受支持

`format_data_type(data_type)` 是**总分发器**：按实例的通用 `name` 路由到对应的命名族成员。名为 `sqlite_integer` 的后端类型会被分发到 `format_data_type_sqlite_integer`；每个具体（带前缀的）类型都按自己的名称分发，而不是按 Python 子类关系匹配。

```python
class SQLiteIntegerType(IntegerType):
    name = "sqlite_integer"

# 按通用名分发：
# SQLiteIntegerType 实例 -> dialect.format_data_type_sqlite_integer()
```

因此方言只为它支持的名字声明逐类型格式化器；带命名空间前缀的类型不存在「自动继承通用渲染器」的隐式回退。

### 严格忠实渲染：绝不静默替换

方言**只渲染它原生支持的声明**。分发给方言不支持的类型会抛出 `TypeError`——不存在可路由的 `format_data_type_<name>` 成员，这正是如实的「此处不支持」信号（不支持的类型在命名族中就是**缺席**，绝不伪装）。`CustomType` 的原始字符串透传同样要求后端显式实现 `format_data_type_custom`，使原始串渲染始终是后端刻意的、可审计的选择（安全逃生舱）。

通用类型的自增语义是一个典型例子：在 PostgreSQL 上声明通用自增类型会报错，并指引使用 `PostgresSerialType`——框架不会悄悄替换为近似语义。

### 能力检测

方言通过同一命名族加上两个映射查询暴露类型能力面：

```python
# 单类型检测：supports_data_type_<name>() 命名族
if dialect.supports_data_type_text():
    ...

# 完整映射：{通用名: 具体 DataType 类}，覆盖方言支持的所有类型
for name, dt_cls in dialect.supports_data_types().items():
    print(name, dt_cls.__name__)
```

`supports_data_types()` 由方言自身的命名族成员自动发现（后端方言会把带自己前缀的条目合并进继承的映射）。它的键与 `format_data_type_*` 命名族的分发键完全一致。

### 跨后端建议 (suggested_data_types)

`suggested_data_types() -> Dict[str, type]` 是**跨后端类型一致性**的对应机制：对于方言**不**原生支持的通用类型，它可以建议一个替代的 `DataType` 类。

- 键使用相同的通用名命名空间（`"uuid"`、`"enum"`、……），且与 `supports_data_types()` 的键**互不相交**——方言能渲染的类型无需建议
- 值是具体的 `DataType` 类（例如 SQLite 建议 `uuid`/`enum` → `SQLiteTextType`，`binary`/`varbinary` → `SQLiteBlobType`）
- 仅为建议——用户层（ActiveRecord/应用代码）决定是否采纳
- 默认返回空字典；这里同样适用如实原则：绝不伪装建议

### 与模型字段的集成

普通 Python 注解不会由 `DDLSourceMixin` 自动转换为 `DataType`。没有 `UseSqlType` 时，`column_data_type()` 返回 `None`。显式声明使用 `UseSqlType`，它会按声明顺序保留候选：

```python
from typing import Annotated
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import TextType
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLEnumType

class Product(ActiveRecord):
    size: Annotated[str, UseSqlType(MySQLEnumType(values=["S", "M", "L"]), TextType())]
```

`DDLSourceMixin` 不执行候选选择或后端回退；这些工作由后续方言消费者完成。

### 内省与同步 (parse_type)

方言实现 `parse_type(raw)`（`DataTypeSupport` 协议）时，可将数据库返回的原始类型字符串解析回 `DataType` 对象，用于 schema 内省与比对。未实现该接口的方言回退为 `CustomType(raw=raw)`。旧名 `DDLTypeSupport` / `DDLTypeMixin` 仅作为对应新名的 deprecated 兼容别名保留。

`parse_type` 的结果必须是**规范**的，其两半都由 `tests/.../dummy2/test_type_spelling_parse.py` 强制：

- **覆盖** —— 核心 `SPELLINGS` 中的每一个拼写都必须解析成某个类型。`CustomType` 只对框架根本没有概念的名字才是诚实答案；若用在 `INT1`、`CHARACTER`、`DEC`、`BOOL` 上，就会把框架自己声明的类型报成厂商类型，并把原文写回 DDL。
- **一个概念进、一个类出** —— 同一概念的所有拼写解析到同一个类，且 `character varying`（变长）绝不解析到定长的 `CharType`。每个同义词一个类正是 `spelling` 参数要消除的东西，而把两者混为一谈的解析器会报出并不存在的 schema 变更。

解析成哪个类由方言决定，而不是由拼写决定：存储层无法区分两个概念的后端，可以用代表该共享存储的类作答。core 内的例子就是 SQLite —— `TINYINT` 与 `BIGINT` 同属 INTEGER affinity 这一格，把它们区分开来反而会报出数据库本身并不做的区分。

## 比较两个声明

`==` 就是全部。两份声明是同一个类型，当且仅当它们是同一个类且逻辑内容相同 —— 这正是值对象的 `==` 已经表达的含义。

```python
if old_type != new_type:
    ...   # schema 确实变了
```

不存在更宽松的"它们等价吗"这个问题，而且这是刻意的。原来的 `synonyms()` / `is_equivalent()` 一对机制存在的目的，是为**同义词类**兜底；而同义词现在由 `spelling` 参数表达，两个拼写就是同一个类，于是等价表已经没有工作可做了。在 9 个方言 × 11 组同义词（共 99 次比较）上实测，`is_equivalent()` 与 `==` 从未出现分歧 —— 它是一个不再承担任何职责的机制。

`==` 确实回答不了的一个问题是"这个数组列存的东西和那个是不是同一种"，而这个答案**应当**忽略数组有几个维度。那是另一个问题，有它自己的名字：`is_element_type_equivalent`。

```python
two_d.is_element_type_equivalent(one_d)   # True —— 两者存的都是整数
```

## 相关文档

- [表达式系统概览](README.md)：通用 / 特定后端设计哲学与序列化能力
- [自定义后端](../custom_backend.md)：方言协议、连接配置与后端接入