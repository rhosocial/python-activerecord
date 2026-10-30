# 核心表达式 (Core Expressions)

本节详细介绍了表达式系统的基本构建块，包括基类、Mixin、核心表达式和运算符。

## 目录

- [协议与助手函数](#协议与助手函数)
- [基类](#基类)
- [Mixins](#mixins)
  - [AliasableMixin](#aliasablemixin)
  - [ComparisonMixin](#comparisonmixin)
  - [ArithmeticMixin](#arithmeticmixin)
  - [LogicalMixin](#logicalmixin)
  - [StringMixin](#stringmixin)
  - [TypeCastingMixin](#typecastingmixin)
- [核心表达式](#核心表达式)
  - [表源与关系对象 (Table Sources and Relation Objects)](#表源与关系对象-table-sources-and-relation-objects)
  - [Column](#column)
  - [Literal](#literal)
  - [AllColumnsWildcard](#allcolumnswildcard)
  - [Subquery](#subquery)
- [运算符](#运算符)
  - [Identifier](#identifier)
  - [SQLOperation](#sqloperation)
  - [BinaryExpression](#binaryexpression)
  - [ArithmeticOperation](#arithmeticoperation)
  - [UnaryExpression](#unaryexpression)
  - [RawSQL](#rawsqlexpression)
  - [RawSQLPredicate](#rawsqlpredicate)
- [COLLATE 表达式](#collate-表达式)

## 基类 (Base Classes)

表达式系统建立在 `rhosocial.activerecord.backend.expression.bases` 定义的抽象基类层次结构之上。

### ToSQLProtocol

`ToSQLProtocol` 定义了任何可以转换为 SQL 的对象的契约。

```python
from typing import Protocol, Tuple

class ToSQLProtocol(Protocol):
    def to_sql(self) -> Tuple[str, tuple]:
        """
        将对象转换为 SQL 字符串和参数元组。
        
        Returns:
            Tuple[str, tuple]: SQL 字符串和参数元组。
        """
        ...
```

### BaseExpression

`BaseExpression` 是所有表达式组件的根基类。它以结构方式满足 `ToSQLProtocol`，持有**逐节点**的方言引用，并且**只在基类集中实现一次** `to_sql()`——子类绝不复写它，只通过只读的 `format_method` 属性声明渲染自己的方言格式化方法名。

```python
from typing import Optional, Tuple

class BaseExpression:
    def __init__(self, dialect: Optional["SQLDialectBase"] = None):
        # 方言是约定俗成的第一个参数，但可选——
        # 允许推迟绑定（例如模型声明期没有方言；
        # ActiveRecord 的 DDL 推导会逐节点绑定）。
        self.dialect = dialect

    @property
    def dialect(self) -> "SQLDialectBase":
        # 读取时会校验是否已绑定方言；渲染必须有方言，
        # 因此未绑定就访问会抛出 ValueError
        # ("... has no dialect bound ...")。
        ...

    @dialect.setter
    def dialect(self, dialect: Optional["SQLDialectBase"]) -> None:
        # 只影响本节点——不会向子表达式传播。
        # 在构造时逐节点传入方言，或遍历树逐个绑定。
        ...

    @property
    def format_method(self) -> str:
        # 渲染该表达式的方言 format_*() 方法名。
        # 按契约只读；未声明（或方言未提供该方法）则不可渲染。
        ...

    def to_sql(self) -> Tuple[str, tuple]:
        # 只在这里实现一次。无状态、零分配：
        # 在本节点绑定的方言上解析 format_method，
        # 然后调用 formatter(self)。没有重建、没有传播、没有副本。
        ...
```

### SQLPredicate

`SQLPredicate` 表示计算结果为布尔值的表达式（例如 `WHERE` 条件）。它混入了 `LogicalMixin` 以支持 `&` (AND)、`|` (OR) 和 `~` (NOT) 运算符。

```python
from rhosocial.activerecord.backend.expression import bases, mixins

class SQLPredicate(mixins.LogicalMixin, BaseExpression):
    pass
```

### SQLValue

`SQLValue` 表示计算结果为标量值的表达式（例如列、字面量、函数结果）。

```python
class SQLValue(BaseExpression):
    pass
```

## 核心组件 (Core Components)

`rhosocial.activerecord.backend.expression.core` 模块定义了 SQL 查询的基础构建块。

### Literal

表示 SQL 查询中的字面量值。它会自动处理参数绑定。

```python
import inspect
from rhosocial.activerecord.backend.expression import Literal

# 库实际声明的构造函数
print(inspect.signature(Literal.__init__))

# 默认：绑定参数模式
# Literal(dialect, "active")
# -> ('?', ('active',))

# 内联模式：值直接嵌入 SQL（用于 DDL 子句）
# Literal(dialect, "active", inline=True)
# -> ("'active'", ())
```

#### 内联字面量

默认情况下，`Literal` 渲染为**绑定参数**（`?` 或 `%s`，取决于方言），遵循 DB-API 2.0 (PEP 249) 规范。这是 DML 语句（`INSERT`、`SELECT`、`UPDATE`、`DELETE`）的安全首选模式。

然而，**DDL 子句**（`DEFAULT`、`CHECK`、分区边界、部分索引 `WHERE`）**不接受绑定参数**——数据库引擎要求直接使用 SQL 文本字面量。对于这些情况，请在 `Literal` 节点上设置 `inline=True`：

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnCheckConstraint,
    ColumnConstraint,
    ColumnDefaultConstraint,
    ColumnDefinition,
    ComparisonOperator,
    ComparisonPredicate,
    Literal,
)
from rhosocial.activerecord.backend.expression.types import IntegerType

# DDL：DEFAULT 值必须内联
ColumnDefinition(
    dialect,
    name="age",
    data_type=IntegerType(dialect),
    constraints=[
        ColumnConstraint(
            dialect,
            branch=ColumnDefaultConstraint(
                dialect,
                value=Literal(dialect, 0, inline=True),  # -> DEFAULT 0
            ),
        ),
    ],
)

# DDL：CHECK 条件——比较值必须内联
ColumnConstraint(
    dialect,
    branch=ColumnCheckConstraint(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            ComparisonOperator.GTE,
            Column(dialect, "score"),
            Literal(dialect, 0, inline=True),  # -> CHECK ("score" >= 0)
        ),
    ),
)
```

`inline` 开关是**逐节点控制**的——每个 `Literal` 独立决定。单个谓词可以混合内联和绑定参数值：

```python
from rhosocial.activerecord.backend.expression import ComparisonPredicate, Literal

pred = ComparisonPredicate(
    dialect, "=",
    Literal(dialect, "a", inline=True),  # 内联
    Literal(dialect, "b"),               # 绑定参数
)
pred.to_sql()  # -> ("'a' = ?", ("b",))
```

> **安全提示**：当值可能受终端用户影响时，内联字面量存在 SQL 注入风险。仅对开发者声明的常量（DDL 默认值、派生自 Schema 的值）使用 `inline=True`。

### Column

表示列引用，可选地包含表限定符和别名。

```python
import inspect
from rhosocial.activerecord.backend.expression import Column

print(inspect.signature(Column.__init__))

# 示例: users.name
# Column(dialect, "name", table="users")
```

裸 `Column` 只是**引用**。比较、算术与字符串运算符已从它上面移除：`Column(...) == Literal(...)` 现在只是普通的 Python `bool`，而不是谓词。请改用带类型的列——`StringColumn`、`IntegerColumn`、`NumericColumn`、`TimestampColumn` 或 `BooleanColumn`——它们会把普通 Python 值包装成 `Literal`，因此能构造真正的谓词。当两侧都已经是表达式时，可以使用显式节点 `ComparisonPredicate(dialect, ComparisonOperator.EQ, left, right)`。

### 表源与关系对象 (Table Sources and Relation Objects)

`FROM` 子句能命名的对象都是**表源 (table source)**，但并非每个源都是持久化对象。这两个问题由两棵独立的树回答：

- **持久化关系**——`Table`、`View`、`MaterializedView`、`ForeignTable`，以及图表的 `NodeTable` / `EdgeTable`——位于 `rhosocial.activerecord.backend.expression.objects`。它们只承载目录身份（名称，以及可选的 catalog 与 schema）。
- **仅查询期存在的源**——`NamedRelationRef`、`DerivedTableSource`、`ValuesTableSource`、`TableFunctionSource`、`JsonTableSource`、`XmlTableSource` 与 `GraphTableSource`——位于 `rhosocial.activerecord.backend.expression.sources`。它们的行只在一条语句的生命周期内存在；`FROM json_table(...)` 根本没有目录身份。

两棵树通过**组合**而非继承连接：`NamedRelationRef` 持有一个关系对象。别名与时态选项属于源，因为 `FROM users AS u` 只在一条查询内重命名一行，并不改动目录中的任何东西。

```python
import inspect
from rhosocial.activerecord.backend.expression.objects import (
    EdgeTable,
    ForeignTable,
    MaterializedView,
    NodeTable,
    Table,
    View,
)

for relation in (Table, View, MaterializedView, ForeignTable, NodeTable, EdgeTable):
    print(relation.__name__, inspect.signature(relation.__init__))
```

```python
import inspect
from rhosocial.activerecord.backend.expression.sources import (
    DerivedTableSource,
    GraphTableSource,
    JsonTableSource,
    NamedRelationRef,
    TableFunctionSource,
    ValuesTableSource,
    XmlTableSource,
)

for source in (
    NamedRelationRef,
    DerivedTableSource,
    ValuesTableSource,
    TableFunctionSource,
    JsonTableSource,
    XmlTableSource,
    GraphTableSource,
):
    print(source.__name__, inspect.signature(source.__init__))
```

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef

# FROM "users"
NamedRelationRef(dialect, Table(dialect, "users"))
# -> ('"users"', ())

# FROM "users" AS "u" —— 别名位于源上
NamedRelationRef(dialect, Table(dialect, "users"), alias="u")
# -> ('"users" AS "u"', ())
```

### FunctionCall

表示通用的标量函数调用。

当 `niladic=True` 且没有参数时，函数调用生成不含括号的 SQL（如 `CURRENT_TIMESTAMP` 而非 `CURRENT_TIMESTAMP()`）。根据 SQL:2003 标准，某些值函数是零元的（niladic），在无参数调用时不得使用括号。当零元函数有参数时（如 `CURRENT_TIMESTAMP(6)`），括号照常生成。

```python
import inspect
from rhosocial.activerecord.backend.expression import FunctionCall

print(inspect.signature(FunctionCall.__init__))
```

**零元函数用法：**

```python
# SQL:2003 零元函数 — 生成 CURRENT_TIMESTAMP（无括号）
FunctionCall(dialect, 'CURRENT_TIMESTAMP', niladic=True)
# -> ('CURRENT_TIMESTAMP', ())

# 零元函数带参数 — 生成 CURRENT_TIMESTAMP(?)
FunctionCall(dialect, 'CURRENT_TIMESTAMP', Literal(dialect, 6), niladic=True)
# -> ('CURRENT_TIMESTAMP(?)', (6,))

# 普通函数 — 始终带括号
FunctionCall(dialect, 'NOW')
# -> ('NOW()', ())
```

### AllColumnsWildcard

表示 select list 的通配符 (`*`)，可经行源引用限定为 `rel.*`。请优先使用此类而不是 `Literal("*")`。

```python
import inspect
from rhosocial.activerecord.backend.expression import AllColumnsWildcard

print(inspect.signature(AllColumnsWildcard.__init__))
```

裸 `*` 的展开范围由所在子句决定（select list 为 FROM 全体源，RETURNING 为 DML 目标表）。
行计数是另一个契约：`COUNT(*)` 的参数是 `RowCountWildcard`，它不带 relation，只渲染裸 `*`。

### Subquery

表示子查询表达式。它可以包装 SQL 字符串、`(sql, params)` 元组或其他表达式。

```python
import inspect
from rhosocial.activerecord.backend.expression import Subquery

print(inspect.signature(Subquery.__init__))

# 示例: (SELECT id FROM users WHERE age > ?)
# Subquery(dialect, "SELECT id FROM users WHERE age > ?", (25,))
# -> ('(SELECT id FROM users WHERE age > ?)', (25,))
```

## Mixins

Mixin 为表达式类提供运算符重载和通用功能。

### AliasableMixin

提供 `.as_(alias)` 方法为表达式分配别名。

```python
# SELECT name AS user_name
Column(dialect, "name").as_("user_name")
```

### ComparisonMixin

启用标准 Python 比较运算符 (`==`, `!=`, `>`, `<`, `>=`, `<=`) 生成 SQL 谓词。该 Mixin 由带类型的列和表达式包装类承载；裸 `Column` 故意不携带它。

```python
from rhosocial.activerecord.backend.expression import (
    Column, IntegerColumn, StringColumn,
)

# age >= 18 —— 带类型的列会把 18 包装成 Literal
IntegerColumn(dialect, "age") >= 18

# status == 'active'
StringColumn(dialect, "status") == "active"

# IS NULL / IS NOT NULL
Column(dialect, "email").is_null()
Column(dialect, "email").is_not_null()

# IN / NOT IN
StringColumn(dialect, "status").in_(["active", "pending"])
StringColumn(dialect, "status").not_in(["banned", "deleted"])

# BETWEEN
IntegerColumn(dialect, "age").between(18, 65)
```

### ArithmeticMixin

启用标准 Python 算术运算符 (`+`, `-`, `*`, `/`, `%`) 生成 SQL 算术表达式。算术运算需要数值类型的列，它同时为另一操作数提供字面量。

```python
from rhosocial.activerecord.backend.expression import IntegerColumn, NumericColumn

# price * 0.9
NumericColumn(dialect, "price") * 0.9

# (count + 1)
IntegerColumn(dialect, "count") + 1
```

### LogicalMixin

启用标准 Python 位运算符 (`&`, `|`, `~`) 生成 SQL 逻辑谓词 (`AND`, `OR`, `NOT`)。

```python
from rhosocial.activerecord.backend.expression import (
    BooleanColumn, IntegerColumn, StringColumn,
)

# (age >= 18) AND (active = true)
(IntegerColumn(dialect, "age") >= 18) & (BooleanColumn(dialect, "active") == True)

# NOT (status = 'banned')
~(StringColumn(dialect, "status") == "banned")
```

### StringMixin

提供字符串特定的方法，如 `like` 和 `ilike`。

```python
from rhosocial.activerecord.backend.expression import StringColumn

# name LIKE 'John%'
StringColumn(dialect, "name").like("John%")

# email ILIKE '%@gmail.com'
StringColumn(dialect, "email").ilike("%@gmail.com")
```

### TypeCastingMixin

提供类型转换能力，允许表达式转换为不同的 SQL 类型。遵循 Expression-Dialect 分离架构，实际的 SQL 语法由各后端的 `format_cast_expression` 方法生成。

```python
from rhosocial.activerecord.backend.expression import NumericColumn, StringColumn
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType

# 基本类型转换 —— 目标类型是 DataType 对象，绝不是类型名字符串
NumericColumn(dialect, "price").cast(IntegerType(dialect))
# PostgreSQL 生成: "price"::INTEGER
# 其他后端生成: CAST("price" AS INTEGER)

# 类型修饰符属于 DataType 对象
StringColumn(dialect, "name").cast(VarCharType(dialect, length=100))
# PostgreSQL 生成: "name"::VARCHAR(100)

# 链式类型转换
StringColumn(dialect, "amount").cast(VarCharType(dialect, length=20)).cast(IntegerType(dialect))
# -> CAST(CAST("amount" AS VARCHAR(20)) AS INTEGER)

# 类型转换支持链式调用
expr = NumericColumn(dialect, "value").cast(IntegerType(dialect))
result = expr * 1.1       # 算术运算
predicate = expr > 100    # 比较运算
```

**重要说明**：
- `TypeCastingMixin` 不直接拼接 SQL 字符串
- 目标类型始终是 `DataType` 实例（`IntegerType(dialect)`、`VarCharType(dialect, length=100)` 等）；类型名字符串会在构造时被拒绝
- 类型修饰符（如 `VARCHAR(100)`）通过 `DataType` 参数表达，例如 `VarCharType(dialect, length=100)`
- 实际的 SQL 语法由 dialect 的 `format_cast_expression` 方法决定
- PostgreSQL 使用 `::` 语法，其他数据库使用 `CAST()` 函数

## 核心表达式

### FROM 中的表源 (Table Sources in FROM)

关系对象只承载目录身份；源包装它，并携带别名（以及任何时态选项）。

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef

# 持久化关系：只有目录身份，没有别名
relation = Table(dialect, "users")
relation.to_sql()  # -> ('"users"', ())

# 查询源：包装关系并携带别名
source = NamedRelationRef(dialect, relation, alias="u")
source.to_sql()  # -> ('"users" AS "u"', ())
```

### Column

表示列引用。

```python
from rhosocial.activerecord.backend.expression import Column

# users.name
col = Column(dialect, "name", table="users")
```

### Literal

表示参数化的字面量值。

```python
from rhosocial.activerecord.backend.expression import Literal

# ? (param: 100)
lit = Literal(dialect, 100)
```

### AllColumnsWildcard

表示 `*` 或 `table.*`。

```python
from rhosocial.activerecord.backend.expression import AllColumnsWildcard
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef

# SELECT *
wildcard = AllColumnsWildcard(dialect)

# SELECT users.*
wildcard = AllColumnsWildcard(
    dialect, relation=NamedRelationRef(dialect, Table(dialect, "users"))
)
```

### Subquery

表示子查询表达式。

```python
from rhosocial.activerecord.backend.expression import Column, QueryStatement, Subquery
from rhosocial.activerecord.backend.expression.objects import Table

query = QueryStatement(
    dialect, select=[Column(dialect, "id")], from_=Table(dialect, "users")
)

# (SELECT ...) AS sub
sub = Subquery(dialect, query, alias="sub")
```

## 运算符和表达式 (Operators and Expressions)

`rhosocial.activerecord.backend.expression.operators` 模块提供了各种 SQL 操作的类。

### Identifier

表示通用的 SQL 标识符（例如表名、列名）。

```python
import inspect
from rhosocial.activerecord.backend.expression import Identifier

print(inspect.signature(Identifier.__init__))
```

### SQLOperation

表示通用的函数调用风格的操作。

```python
from rhosocial.activerecord.backend.expression import Literal, SQLOperation

# 示例: custom_op(?, ?)
op = SQLOperation(dialect, "custom_op", Literal(dialect, 1), Literal(dialect, 2))
```

### BinaryExpression

表示标准的二元运算符（例如 `=`, `!=`, `LIKE`）。

```python
import inspect
from rhosocial.activerecord.backend.expression import BinaryExpression

print(inspect.signature(BinaryExpression.__init__))
```

### UnaryExpression

表示一元运算符（例如 `NOT`, `-`）。

```python
import inspect
from rhosocial.activerecord.backend.expression import UnaryExpression

print(inspect.signature(UnaryExpression.__init__))
```

### ArithmeticOperation

表示具有运算符优先级处理的二元算术运算。

`op` 是 `ArithmeticOperator` 的成员，其存储值是**运算词**：`add` / `sub` / `mul` / `div` / `mod`。方言格式化函数再把词映射成该后端书写的字符（见 `OPERATOR_SYMBOLS`），因此工件里承载的是语言中立的词，而不是某个词法器写下的符号。词集封闭，未知词在构造处即被拒绝。

```python
import inspect
from rhosocial.activerecord.backend.expression import ArithmeticOperation

print(inspect.signature(ArithmeticOperation.__init__))
```

### 原始表达式 (Raw Expressions)

**警告**：这些类应谨慎使用，因为它们允许原始 SQL 注入。确保所有输入都是受信任的或已正确清理。

#### RawSQL

表示作为值表达式的原始 SQL 字符串。

```python
import inspect
from rhosocial.activerecord.backend.expression import RawSQL

print(inspect.signature(RawSQL.__init__))
```

#### RawSQLPredicate

表示作为谓词（布尔条件）的原始 SQL 字符串。

```python
from rhosocial.activerecord.backend.expression.operators import RawSQLPredicate

# 示例: 原始 SQL 条件
pred = RawSQLPredicate(dialect, "EXISTS (SELECT 1 FROM log WHERE log.user_id = users.id)")
```

## COLLATE 表达式

`CollateFunction`（定义在 `rhosocial.activerecord.backend.expression.collation`）为 SQL 值表达式应用显式排序规则。

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.collation import collate

# 基本用法：为列指定排序规则
expr = collate(Column(dialect, "name"), "Chinese_PRC_CI_AS")
sql, params = expr.to_sql()
# sql: '"name" COLLATE Chinese_PRC_CI_AS'
# params: ()

# 链式操作：排序规则后的表达式仍支持所有 Mixin 操作
expr = collate(Column(dialect, "name"), "NOCASE") == "alice"
sql, params = expr.to_sql()
# sql: '"name" COLLATE NOCASE = ?'
# params: ("alice",)
```

`CollateFunction` 混入了 `AliasableMixin`、`ArithmeticMixin`、`ComparisonMixin`、`StringPatternPredicateMixin` 和 `TypeCastingMixin`，可以像普通 SQL 值表达式一样参与运算、比较、模式匹配和别名。

### 方言集成

各后端方言需要实现 `supports_collation()` 和 `format_collation()` 方法来支持 COLLATE 子句的格式化。SQLite 后端提供了内置的 COLLATE 格式化支持。
