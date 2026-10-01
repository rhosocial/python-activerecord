# Schema 命名空间

> 如何把模型绑定到数据库的 schema，以及究竟由什么决定 schema 是否出现在
> 最终执行的 SQL 里。

schema 是多数数据库里最接近"命名空间"的概念。PostgreSQL、SQL Server 与 Oracle
把它当作对象名的一等组成部分；MySQL/MariaDB 称之为 database；BigQuery 称之为
dataset；Snowflake 则把它嵌在 database 之内。本页说明如何在模型上声明 schema，
以及同样重要的——这个声明**不覆盖**哪些场景。

## 1. 声明 schema

模型通过 `__schema_name__` 类属性声明 schema。该属性可选，默认值为 `None`，
表示"通过连接的默认命名空间解析"。

```python
from typing import ClassVar, Optional
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = "app"          # -> "app"."users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    name: str
```

`schema_name()` 是读取该属性的唯一入口，可以覆写以支持动态命名空间。
按适用频率排列的四种写法：

```python
# 1) 静态声明 —— 最常见的情形。该模型的每条语句都会带限定。
class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = "app"

# 2) 模板基类 —— 让多个模型共享同一命名空间。
class AppModel(ActiveRecord):
    __schema_name__ = "app"

class User(AppModel):
    __table_name__ = "users"

class Order(AppModel):
    __table_name__ = "orders"

# 3) 动态 —— 多租户。每个租户一个模型类，调用时选定。
class Order(ActiveRecord):
    __table_name__ = "orders"

    @classmethod
    def schema_name(cls) -> str:
        return f"tenant_{current_tenant_id()}"

# 4) 由配置驱动。
class User(ActiveRecord):
    __schema_name__ = settings.db_schema
```

`__table_name__` 与 `__schema_name__` 是**分开**的，请不要合并：

```python
__table_name__ = "app.users"   # 错误
```

标识符会被整体当作一个单位加引号，于是渲染成 `FROM "app.users"` —— 一个内部
含点号的标识符，而不是带限定的引用。PostgreSQL 随后会报
`relation "app.users" does not exist`。请使用 `__schema_name__`；在支持元组的
地方，也可以传 `(schema, table)` 元组。

## 2. 由什么决定 schema 是否出现在 SQL 中

只有一条决策链，其中没有任何配置开关：

```
__schema_name__  ->  schema_name()  ->  TableExpression.schema_name
                                          / Column.schema_name
                                      ->  format_table() / format_column()
```

你只提供两个输入，其余全部自动决定：

1. `schema_name()` 返回字符串还是 `None`；
2. 是否存在生效的表别名。

渲染形式如下：

| `FROM` 中的范围 | 列引用 | PostgreSQL |
|---|---|---|
| `"users"`（无 schema） | `"users"."id"` | 合法 |
| `"ar_crm"."users"` | `"ar_crm"."users"."id"` | 合法 |
| `"ar_crm"."users"` | `"users"."id"` | 合法 |
| `"ar_crm"."users" AS "u"` | `"u"."id"` | 合法 |
| `"ar_crm"."users" AS "u"` | `"ar_crm"."users"."id"` | **报错** |
| `"ar_crm"."users" AS "u"` | `"users"."id"` | **报错** |

也就是说：**无别名**的范围两种写法都合法，而**有别名**的范围只能用别名本身引用。
因此"永远使用两段式"并非一条自洽的规则 —— 它恰恰在存在别名时是错的。

对别名范围的抑制发生在列表达式**构造**时，而非渲染时：只要表别名生效，
`FieldProxy` 就会把 `schema_name` 置为 `None`。手工构造 `Column` 会绕过这道
保护，于是手工构造的
`Column(dialect, "id", table="u", schema_name="ar_crm")` 会渲染出 PostgreSQL
拒绝的三段式。

### 三件不由你决定的事

* **`search_path`。** 它在建连时作为 libpq 参数下发，因此在整个连接生命周期内
  固定，**无法**按查询或按事务切换。不带限定的名字通过它解析。
* **连接的 `default_schema` 配置。** 它从未影响过生成的 SQL。未设置
  `__schema_name__` 的模型通过 `search_path` 解析；请改用后者。
* **别名。** 一旦设置，schema 会按设计从列引用中丢弃。

## 3. 反模式

```python
__table_name__ = "app.users"   # 错误：渲染为 FROM "app.users"
__schema_name__ = ""          # 错误：被当作"无 schema"，或直接报错
```

关于 `__schema_name__ = ""` 需要强调：空 schema 是笔误，而不是"不带限定"的
写法 —— 后者用 `None` 表示。空字符串现已被显式拒绝，非字符串值同样如此。
`TableExpression(schema_name=...)` 以及所有 DML 的 `*Options` 对象都遵循此规则。

## 4. DDL 有自己的 schema 参数

> **`__schema_name__` 决定的是读写命名空间，DDL 语句不读取它** —— 但凡是
> 指向命名空间内对象的语句，都接受自己的 `schema_name`，迁移 DDL 不必再手工拼接。

| 语句 | 是否采用模型的 schema | 如何限定 |
|---|---|---|
| `CREATE TABLE` / `DROP TABLE` | 否 | 传 `TableExpression(dialect, "users", schema_name="app")` |
| `CREATE` / `ALTER` / `DROP` / `REFRESH` VIEW（含物化视图） | 否 | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` TYPE | 否 | `schema_name="app"` |
| `CREATE` / `DROP` INDEX（含全文索引） | 否 | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` SEQUENCE | 否 | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` DOMAIN | 否 | `schema_name="app"` |
| `CREATE` / `DROP` FUNCTION | 否 | `schema_name="app"` |
| `CREATE` / `DROP` TRIGGER | 否 | `schema_name="app"` |
| `TRUNCATE` | 否 | 有独立的 `schema=` 字段 |
| `SELECT` / `INSERT` / `UPDATE` / `DELETE` | **是** | 自动 |

`schema_name` 默认为 `None`，含义是"不限定"—— 与表达式层其他地方一致。
传 `""` 会被拒绝：空串是笔误，而不是表示"不限定"的方式。

指向 `app.users` 的模型与创建 `public.users` 的迁移仍不会自动一致：
构造 DDL 时不会读取 `__schema_name__`，所以迁移必须自己写明它要的 schema。
现在可以直接写，而不必手工拼接限定名。

在不支持命名空间的后端上，传入 schema 会抛 `UnsupportedFeatureError`，
而不是被悄悄丢弃。实际遇到的典型是 SQLite：它没有 schema 层，
限定名会变成服务器拒绝的形式。

## 5. 限定符的绑定时机

`Model.c.field` 在**表达式构造时**就快照了 `table_name()` 与 `schema_name()`，
而不是在执行时：

```python
condition = Order.c.total > 100     # 已绑定到当前 schema
Order.__schema_name__ = "tenant_b"  # 对 `condition` 而言已经太晚
condition = Order.c.total > 100     # 需重建才能取到新 schema
```

`table_name()` 同理。做租户切换时，请切换后重建条件表达式，
或者每个命名空间使用一个独立的模型类。

## 6. 后端支持矩阵

`schema_name` 具体指向什么，由各后端自己定义。**它们都接受这个参数，但对它的解释
并不一致。** 下表记录的是各后端的实际做法。本指南中出现的 `"app"."users"`
一律是 PostgreSQL / SQL Server / Oracle 的写法。

| 后端 | `supports_schema()` | `schema_name` 指向 | 渲染为 |
|---|---|---|---|
| PostgreSQL | 是 | 当前 database 内的 schema | `"app"."users"` |
| SQL Server | 是 | 当前 database 内的 schema | `[app].[users]` |
| Oracle | 是 | schema，即属主用户 | `"APP"."USERS"`（折为大写） |
| Snowflake | 是 | schema，**隶属于** database —— 是独立一层，不是 database 本身 | 需配合 `CURRENT_DATABASE()` 才能完全限定 |
| BigQuery | 是 | dataset；列引用永不带 schema | `` `app.users` `` |
| MariaDB | 是 | **database** —— `schema` 是 `database` 的同义词，`CREATE SCHEMA` / `SHOW SCHEMAS` 可用且列的就是 database | `` `app`.`users` `` |
| MySQL | 是 | **database** —— 同 MariaDB 的同义关系 | `` `app`.`users` `` |
| ClickHouse | 是 | **database** —— 没有独立的 schema 层，`CREATE SCHEMA` 是语法错误，但 `schema_name` 仍被接受并当作 database 使用 | `` `app`.`users` `` |
| SQLite、Firebird | 否 | 无命名空间层 | 拒绝 |

由此得出三点，也正是同一份模型定义不能被假定在任何后端上含义相同的原因：

- **只有 Snowflake 有自己独立的 schema 层。** 它的完全限定名是
  `<database>.<schema>.<object>`，所以在它上面单给一个 `schema_name`
  并不能定位对象。
- **MySQL、MariaDB 与 ClickHouse 都把该值视为 database。** 对 MySQL 与 MariaDB，
  `schema` 与 `database` 是同一个词，因此 `CREATE SCHEMA` 与 `SHOW SCHEMAS`
  都能用，列出来的就是 database。ClickHouse 是同样的概念去掉了这个词：它根本
  没有 `CREATE SCHEMA`，但 `schema_name` 仍被接受并被当作 database 使用，因此
  `supports_schema()` 为 `True` —— 没有独立的 schema 层，但这个值可用。
- **该值原样透传。** 这里不会拿它和连接做校验，所以一个与会话当前命名空间
  不同的 `schema_name`，会指向另一个对象，或者什么都不指向。

## 7. 推荐的分层方式

让 `search_path` 承担常规场景，把 `__schema_name__` 留给例外：

```python
config = PostgresConnectionConfig(
    ...,
    search_path="app,public",   # 常规表以不带限定的名字解析
)
```

* **单 schema 场景** —— 干脆不要设置 `__schema_name__`。不带限定的名字配合
  `search_path`，可以让 DML、DDL 与内省三者保持一致，也完全避免三段式列引用。
* **多 schema 场景** —— 只给偏离 `search_path` 的模型设置 `__schema_name__`。
  例外面越小，踩中上述反模式的机会越低。
* **跨 schema JOIN** —— 两侧各自限定自己的范围，无需额外配置：

  ```python
  Order.query().join(
      Customer, on=Order.c.customer_id == Customer.c.id
  ).select(Order.c.id, Customer.c.name)
  # SELECT ... FROM "shop"."orders" JOIN "crm"."customers" ON ...
  ```
