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

当 `ActiveRecord` 构造 DDL 时，框架遍历收集到的定义，**在构建期复制声明期实例并逐节点注入方言**——产出一棵每个节点都已绑定的自足的树。随后每个节点通过各自无参的 `to_sql()` 渲染：

```
模型字段声明（未绑定类型）                        DDL 构建期
Annotated[str, UseSqlType(MySQLEnumType(...))]  ──►  复制 + 逐节点注入方言 ──► node.to_sql()
int（自动推断 IntegerType）                    ──►  复制 + 逐节点注入方言 ──► node.to_sql()
```

这种「类型推迟绑定方言、DDL 构建期逐节点绑定」的设计，使得：
- 同一模型类可在不同后端复用，字段声明无需改动
- 方言在 DDL 生成的那一刻注入，用户无需手动绑定
- 类型与方言解耦，符合 schema 时对象与查询时对象的角色划分
- 渲染保持无状态：`to_sql()` 只读取节点自身绑定的方言——渲染期没有重建、没有传播、没有副本

## 值对象语义

`DataType` 实例是**值对象**：同一类的两个实例只要逻辑参数相同就**相等且哈希相同**，与是否携带方言引用无关。相等性比较类型的逻辑参数（`_type_params()`）加上 `dialect_options`；哈希只覆盖类型标识与类型参数。绑定的方言对二者都不产生影响——绑定（或重新绑定）方言绝不会改变 `==` 与 `hash` 的结果。

```python
a = IntegerType()
b = IntegerType()
assert a == b          # 值对象：相等（忽略方言）
assert hash(a) == hash(b)
```

`dialect_options` 是随类型实例携带、由后端格式化器消费的**后端专属特殊参数**字典（如 `{'unsigned': True}`、字符集、长度语义等）。它参与**相等性**比较，但刻意**不参与**哈希——可变的选项映射因此不会破坏哈希。

## 通用类型 (Core Types)

通用类型定义在 `rhosocial.activerecord.backend.expression.types`，覆盖绝大多数数据库共有的 SQL 类型：

| 分类 | 类型类 |
|------|--------|
| 整数 | `TinyIntType`、`SmallIntType`、`IntType`、`IntegerType`、`BigIntType` |
| 数值 | `FloatType`、`RealType`、`DoubleType`、`DecimalType` |
| 字符串 | `CharType`、`VarCharType`、`TextType` |
| 布尔 | `BooleanType` |
| 二进制 | `BlobType`、`BinaryType`、`VarBinaryType` |
| 枚举 | `EnumType`（values 必填） |
| 日期时间 | `DateType`、`TimeType`、`TimeTzType`、`DateTimeType`、`TimestampType`、`TimestampTzType`、`IntervalType` |
| JSON | `JsonType`、`JsonBType` |
| 网络 | `InetType`、`CidrType`、`MacAddrType` |
| UUID | `UUIDType` |
| 数组 | `ArrayType` |
| 自定义 | `CustomType` |

通用类型可以在不带方言的情况下实例化（推迟绑定），但在绑定方言之前无法渲染。

## 特定后端类型 (Backend-Specific Types)

每个后端在通用类型之上定义自己的子类型，**命名以后端名为前缀**：

| 后端 | 示例 |
|------|------|
| SQLite | `SQLiteIntegerType(IntegerType)`、`SQLiteTextType(TextType)`、`SQLiteBlobType(BlobType)` |
| MySQL | `MySQLIntType(IntegerType)`、`MySQLTinyIntType(TinyIntType)`、`MySQLEnumType(DataType)`、`MySQLSetType(DataType)`、`MySQLGeometryType(DataType)` |
| PostgreSQL | `PostgresSerialType(DataType)`、`PostgresUUIDType(DataType)`、`PostgresTSVectorType(DataType)`、`PostgresJsonPathType(DataType)` |

后端特定类型通常继承对应的通用类型，仅当该类型是后端独有时（如 MySQL `ENUM`、PostgreSQL `SERIAL`）才直接继承 `DataType`。

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

#### 自动推断

以普通 Python 注解声明的字段由 ActiveRecord 字段层解析为通用 `DataType` 实例，采用**后端中立的**「合理最低公共分母」映射（如 `str` → 文本类型、`int` → 整数类型），刻意回避 `UUID`/`JSONB`/`ENUM` 等后端独有类型。方言不提供逐次调用的推断钩子；而是通过 `supports_data_types()`（类型面）与 `suggested_data_types()`（跨后端建议）声明自身能力，供 DDL 生成器在解析可移植字段声明时参考。

#### 显式指定 (UseSqlType)

字段级注解 `UseSqlType` 优先于自动推断，是使用后端特定类型的标准方式：

```python
from typing import Annotated
from rhosocial.activerecord.base.fields import UseSqlType
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLEnumType

class Product(ActiveRecord):
    # 显式指定 MySQL 特定类型
    size: Annotated[str, UseSqlType(MySQLEnumType(values=['S', 'M', 'L']))]
```

类型解析优先级：`UseSqlType` 注解 → 后端中立默认推断。

### 内省与同步 (parse_type)

方言实现 `parse_type(raw)`（`DDLTypeSupport` 协议）时，可将数据库返回的原始类型字符串解析回 `DataType` 对象，用于 schema 内省与比对。未实现该接口的方言回退为 `CustomType(raw=raw)`。

## 等价性与同义词

`synonyms()` 与 `is_equivalent()` 仅用于**方言内**的 schema 比较归一化（例如 SQLite 的亲和性折叠），**绝不**注册跨方言等价关系——渲染保持严格忠实，方言差异必须显式存在。

```python
# 仅在同一后端的 schema 比对场景使用
if type_a.is_equivalent(type_b):
    ...
```

## 相关文档

- [表达式系统概览](README.md)：通用 / 特定后端设计哲学与序列化能力
- [自定义后端](../custom_backend.md)：方言协议、连接配置与后端接入