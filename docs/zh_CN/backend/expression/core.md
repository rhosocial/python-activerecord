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
- [核心表达式](#核心表达式)
  - [TableExpression](#tableexpression)
  - [Column](#column)
  - [Literal](#literal)
  - [WildcardExpression](#wildcardexpression)
  - [Subquery](#subquery)
- [运算符](#运算符)
  - [Identifier](#identifier)
  - [SQLOperation](#sqloperation)
  - [BinaryExpression](#binaryexpression)
  - [BinaryArithmeticExpression](#binaryarithmeticexpression)
  - [UnaryExpression](#unaryexpression)
  - [RawSQLExpression](#rawsqlexpression)
  - [RawSQLPredicate](#rawsqlpredicate)

## 基类 (Base Classes)

表达式系统建立在 `rhosocial.activerecord.backend.expression.bases` 定义的抽象基类层次结构之上。

### ToSQLProtocol

`ToSQLProtocol` 定义了任何可以转换为 SQL 的对象的契约。

```python
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

`BaseExpression` 是所有表达式组件的根抽象基类。它实现了 `ToSQLProtocol` 并持有 `SQLDialect` 的引用。

```python
class BaseExpression(abc.ABC, ToSQLProtocol):
    def __init__(self, dialect: "SQLDialectBase"):
        self._dialect = dialect

    @property
    def dialect(self) -> "SQLDialectBase":
        return self._dialect

    @abc.abstractmethod
    def to_sql(self) -> Tuple[str, tuple]:
        raise NotImplementedError
```

### SQLPredicate

`SQLPredicate` 表示计算结果为布尔值的表达式（例如 `WHERE` 条件）。它混入了 `LogicalMixin` 以支持 `&` (AND)、`|` (OR) 和 `~` (NOT) 运算符。

```python
class SQLPredicate(mixins.LogicalMixin, BaseExpression):
    pass
```

### SQLValueExpression

`SQLValueExpression` 表示计算结果为标量值的表达式（例如列、字面量、函数结果）。

```python
class SQLValueExpression(BaseExpression):
    pass
```

## 核心组件 (Core Components)

`rhosocial.activerecord.backend.expression.core` 模块定义了 SQL 查询的基础构建块。

### Literal

表示 SQL 查询中的字面量值。它会自动处理参数绑定。

```python
class Literal(mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", value: Any): ...
    
    # 示例: WHERE status = ?
    # Literal(dialect, "active")
    # -> ('?', ('active',))
```

### Column

表示列引用，可选地包含表限定符和别名。

```python
class Column(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", name: str, table: Optional[str] = None, alias: Optional[str] = None): ...

    # 示例: users.name
    # Column(dialect, "name", table="users")
    # -> ('"users"."name"', ())
```

### TableExpression

表示表或视图，可选地包含别名和时态选项（例如 FOR SYSTEM_TIME）。

```python
class TableExpression(mixins.AliasableMixin, bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", name: str, alias: Optional[str] = None, temporal_options: Optional[Dict[str, Any]] = None): ...

    # 示例: FROM users AS u
    # TableExpression(dialect, "users", alias="u")
    # -> ('"users" AS "u"', ())
```

### FunctionCall

表示通用的标量函数调用。

```python
class FunctionCall(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", func_name: str, *args: "bases.BaseExpression", is_distinct: bool = False, alias: Optional[str] = None): ...
```

### WildcardExpression

表示通配符 (`*`) 或表通配符 (`table.*`)。请优先使用此类而不是 `Literal("*")`。

```python
class WildcardExpression(bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", table: Optional[str] = None): ...
```

### Subquery

表示子查询表达式。它可以包装 SQL 字符串、`(sql, params)` 元组或其他表达式。

```python
class Subquery(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", query_input: Union[str, tuple, "BaseExpression"], query_params: Optional[tuple] = None, alias: Optional[str] = None): ...

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

启用标准 Python 比较运算符 (`==`, `!=`, `>`, `<`, `>=`, `<=`) 生成 SQL 谓词。

```python
# age >= 18
Column(dialect, "age") >= 18

# status == 'active'
Column(dialect, "status") == "active"

# IS NULL / IS NOT NULL
Column(dialect, "email").is_null()
Column(dialect, "email").is_not_null()

# IN / NOT IN
Column(dialect, "status").in_(["active", "pending"])
Column(dialect, "status").not_in(["banned", "deleted"])

# BETWEEN
Column(dialect, "age").between(18, 65)
```

### ArithmeticMixin

启用标准 Python 算术运算符 (`+`, `-`, `*`, `/`, `%`) 生成 SQL 算术表达式。

```python
# price * 0.9
Column(dialect, "price") * 0.9

# (count + 1)
Column(dialect, "count") + 1
```

### LogicalMixin

启用标准 Python 位运算符 (`&`, `|`, `~`) 生成 SQL 逻辑谓词 (`AND`, `OR`, `NOT`)。

```python
# (age >= 18) AND (active = true)
(Column(dialect, "age") >= 18) & (Column(dialect, "active") == True)

# NOT (status = 'banned')
~(Column(dialect, "status") == "banned")
```

### StringMixin

提供字符串特定的方法，如 `like` 和 `ilike`。

```python
# name LIKE 'John%'
Column(dialect, "name").like("John%")

# email ILIKE '%@gmail.com'
Column(dialect, "email").ilike("%@gmail.com")
```

## 核心表达式

### TableExpression

表示 SQL 查询中的表或视图。

```python
from rhosocial.activerecord.backend.expression import TableExpression

# FROM users AS u
table = TableExpression(dialect, "users", alias="u")
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

### WildcardExpression

表示 `*` 或 `table.*`。

```python
from rhosocial.activerecord.backend.expression import WildcardExpression

# SELECT *
wildcard = WildcardExpression(dialect)

# SELECT users.*
wildcard = WildcardExpression(dialect, table="users")
```

### Subquery

表示子查询表达式。

```python
from rhosocial.activerecord.backend.expression import Subquery, QueryExpression

# (SELECT ...) AS sub
sub = Subquery(dialect, query_expr, alias="sub")
```

## 运算符和表达式 (Operators and Expressions)

`rhosocial.activerecord.backend.expression.operators` 模块提供了各种 SQL 操作的类。

### Identifier

表示通用的 SQL 标识符（例如表名、列名）。

```python
class Identifier(mixins.ComparisonMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", name: str): ...
```

### SQLOperation

表示通用的函数调用风格的操作。

```python
from rhosocial.activerecord.backend.expression import SQLOperation

# 示例: custom_op(arg1, arg2)
op = SQLOperation(dialect, "custom_op", arg1, arg2)
```

### BinaryExpression

表示标准的二元运算符（例如 `=`, `!=`, `LIKE`）。

```python
class BinaryExpression(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "bases.BaseExpression", right: "bases.BaseExpression"): ...
```

### UnaryExpression

表示一元运算符（例如 `NOT`, `-`）。

```python
class UnaryExpression(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", op: str, operand: "bases.BaseExpression", pos: str = 'before'): ...
```

### BinaryArithmeticExpression

表示具有运算符优先级处理的二元算术运算。

```python
class BinaryArithmeticExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "bases.SQLValueExpression", right: "bases.SQLValueExpression"): ...
```

### 原始表达式 (Raw Expressions)

**警告**：这些类应谨慎使用，因为它们允许原始 SQL 注入。确保所有输入都是受信任的或已正确清理。

#### RawSQLExpression

表示作为值表达式的原始 SQL 字符串。

```python
class RawSQLExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", expression: str, params: tuple = ()): ...
```

#### RawSQLPredicate

表示作为谓词（布尔条件）的原始 SQL 字符串。

```python
from rhosocial.activerecord.backend.expression.operators import RawSQLPredicate

# 示例: 原始 SQL 条件
pred = RawSQLPredicate(dialect, "EXISTS (SELECT 1 FROM log WHERE log.user_id = users.id)")
```
