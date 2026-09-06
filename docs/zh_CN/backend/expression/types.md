# 数据类型 (Data Types)

数据类型（`DataType`）是表达式系统的重要组成，用于在 DDL、模型字段声明与迁移中描述数据库列的类型。

数据类型遵循与表达式系统相同的**通用 / 特定后端**分层设计，并且二者通过「通用基类 + 后端子类」的方式紧密配合。

## 概述

`DataType` 继承自 `BaseExpression`，但与其他表达式有一个关键区别：

> **表达式是查询时对象**（构造时通常需要方言）；**类型是 schema 时对象**（可以在连接存在之前声明，方言可选）。

因此 `DataType` 采用 **declare → bind → render** 三阶段生命周期：

1. **declare**（声明）：类型可以在不携带方言的情况下构造——用于模型字段声明、迁移、`UseSqlType` 注解
2. **bind**（绑定）：通过构造函数（`dialect=...`）、`bind()` 方法，或方言的 `parse_type()` 工厂（内省）附加方言
3. **render**（渲染）：`to_sql()` 委托给所绑定方言的 `format_data_type()`；也可在调用时临时传入方言

```python
from rhosocial.activerecord.backend.expression.types import IntegerType

# declare：无需方言
t = IntegerType()

# bind：绑定方言后可渲染
sql, params = t.bind(dialect).to_sql()
# 或
sql, params = t.to_sql(dialect=dialect)
```

未绑定方言的通用类型直接调用 `to_sql()` 会抛出 `ValueError`——类型必须附着于某个方言才能生成具体的 SQL 类型名。

### 为什么数据类型不直接指定方言类实例？

数据类型的构造签名与其他表达式**刻意不同**。普通表达式（如 `Column`、`ComparisonPredicate`）构造时的第一个位置参数**必须**是方言实例，因为它们是在**查询执行时**构建的，此时方言上下文必然已经存在：

```python
# 普通表达式：第一个参数必须是方言实例
Column(dialect, "name")          # ✅
Literal(dialect, 18)             # ✅
```

但数据类型不同——它经常需要在**方言尚不确定**的时机被创建。最典型的场景是 **`ActiveRecord` 模型字段声明**：

```python
from rhosocial.activerecord.base.fields import UseSqlType

class Product(ActiveRecord):
    size: Annotated[str, UseSqlType(MySQLEnumType(values=['S', 'M', 'L']))]
```

模型类在**导入时**就定义了字段类型注解，而模型此时**尚未配置任何后端**——方言要到之后 `configure(config, backend)` 时才确定。如果类型构造必须携带方言，那么字段声明就必须等待配置，这会：

- 破坏声明的**声明性**：字段类型应与配置解耦，允许在任何环境（测试、生产、不同后端）复用同一个模型类
- 造成**循环依赖**：`ActiveRecord` 需要类型来生成 DDL，而类型又需要方言才能存在

因此，字段声明中写入的是**未绑定的类型实例**。当 `ActiveRecord` 构造 DDL 时，框架自动注入**当前已配置的方言**——这正是 `format_column_definition()` 中的 `col_def.data_type.to_sql(dialect)` 调用：

```
模型字段声明（未绑定类型）                      DDL 构造时（注入方言）
Annotated[str, UseSqlType(MySQLEnumType(...))]  ──►  col_def.data_type.to_sql(dialect)
int（自动推断 IntegerType）                    ──►  绑定当前方言后渲染
```

这种「类型延后绑定方言、DDL 构造时自动注入」的设计，使得：
- 同一模型类可在不同后端复用，字段声明无需改动
- 方言在 DDL 生成的那一刻自然注入，用户无需手动绑定
- 类型与方言解耦，符合 schema 时对象与查询时对象的角色划分

这是数据类型类被**特殊处理**的原因——它虽然继承 `BaseExpression`，但通过可选的方言参数、`bind()` 方法、`to_sql(dialect=...)` 支持延后绑定，与始终携带方言的查询表达式区分开来。

## 值对象语义

`DataType` 实例是**值对象**：两个逻辑参数相同的实例**相等且哈希相同**，无论是否携带方言引用。`bind()` 返回原实例的副本，不修改原对象，因此绑定不会影响 `==` 与 `hash`。

```python
a = IntegerType()
b = IntegerType()
assert a == b          # 值对象：相等
assert hash(a) == hash(b)
```

## 通用类型 (Core Types)

通用类型定义在 `rhosocial.activerecord.backend.expression.types`，覆盖绝大多数数据库共有的 SQL 类型：

| 分类 | 类型类 |
|------|--------|
| 整数 | `TinyIntType`、`SmallIntType`、`IntType`、`IntegerType`、`BigIntType` |
| 数值 | `FloatType`、`RealType`、`DoubleType`、`DecimalType` |
| 字符串 | `CharType`、`VarCharType`、`TextType` |
| 布尔 | `BooleanType` |
| 二进制 | `BlobType`、`BinaryType`、`VarBinaryType` |
| 日期时间 | `DateType`、`TimeType`、`TimeTzType`、`DateTimeType`、`TimestampType`、`TimestampTzType`、`IntervalType` |
| JSON | `JsonType`、`JsonBType` |
| 网络 | `InetType`、`CidrType`、`MacAddrType` |
| UUID | `UUIDType` |
| 数组 | `ArrayType` |
| 自定义 | `CustomType` |

通用类型可以被实例化，但在未绑定方言时无法渲染。

## 特定后端类型 (Backend-Specific Types)

每个后端在通用类型之上定义自己的子类型，**命名以后端名为前缀**：

| 后端 | 示例 |
|------|------|
| SQLite | `SQLiteIntegerType(IntegerType)`、`SQLiteTextType(TextType)`、`SQLiteBlobType(BlobType)` |
| MySQL | `MySQLIntType(IntegerType)`、`MySQLTinyIntType(TinyIntType)`、`MySQLEnumType(DataType)`、`MySQLSetType(DataType)`、`MySQLGeometryType(DataType)` |
| PostgreSQL | `PostgresSerialType(DataType)`、`PostgresUUIDType(DataType)`、`PostgresTSVectorType(DataType)`、`PostgresJsonPathType(DataType)` |

后端特定类型通常继承对应的通用类型，仅当该类型是后端独有时（如 MySQL `ENUM`、PostgreSQL `SERIAL`）才直接继承 `DataType`。

## 通用与特定后端的配合

### 渲染继承：后端子类型自动获得通用渲染

方言的类型渲染器通过 `@handles()` 装饰器注册（`DDLTypeMixin`）。对于核心通用类型，渲染器按**子类关系**匹配：

```python
class SQLiteIntegerType(IntegerType):
    ...

# 方言注册了 IntegerType 的渲染器
# 则 SQLiteIntegerType 自动使用该渲染器，除非后端显式注册了更具体的渲染器
```

这意味着：后端只需为**有差异**的类型注册渲染器，其余类型继承通用渲染，大幅节省后端工作量。

### 严格忠实渲染：绝不静默替换

方言**只渲染它原生支持的声明**。`format_data_type()` 遇到未注册的类型会抛出 `TypeError` 并提示如何注册；`CustomType` 更要求后端显式 `@handles(CustomType)` 才允许透传原始字符串（安全逃生舱）。

通用类型的自增语义是一个典型例子：在 PostgreSQL 上声明通用自增类型会报错，并指引使用 `PostgresSerialType`——框架不会悄悄替换为近似语义。

### 能力检测

方言提供类型能力查询方法：

```python
if dialect.supports_data_type(MyType):
    # 方言能渲染 MyType
    ...

# 列出方言注册的所有 (类型类, SQL 名)
for dt_cls, sql_name in dialect.supports_data_types():
    print(dt_cls.__name__, sql_name)
```

### 与模型字段的集成

#### 自动推断 (suggest_column_type)

声明模型字段时，方言通过 `suggest_column_type(python_type)` 将 Python 类型自动映射为通用 `DataType`：

| Python 类型 | 推断的通用类型 |
|-------------|---------------|
| `str` | `TextType` |
| `int` | `IntegerType` |
| `bool` | `BooleanType` |
| `float` | `DoubleType` |
| `bytes` | `BlobType` |
| `datetime` | `DateTimeType` |
| `date` | `DateType` |
| `Decimal` | `DecimalType` |
| `uuid.UUID` | `UUIDType` |
| `Enum` | `VarCharType(length=64)` |
| `ipaddress` 地址/网络 | `InetType` / `CidrType` |

该映射是**后端中立的**「合理最低公共分母」——刻意回避 `UUID`/`JSONB`/`ENUM` 等后端独有类型。想要更丰富推断的后端会覆写 `suggest_column_type`。

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

类型解析优先级：`UseSqlType` 注解 → `dialect.suggest_column_type()` → 后端中立默认。

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