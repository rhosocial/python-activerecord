# Schema 命名空间

PostgreSQL、SQL Server 和 Oracle 把 schema 当作对象名的一部分，`app.users` 里的
`app` 就是 schema。MySQL 和 MariaDB 不这么分层——它们管这层叫 database，
`CREATE SCHEMA` 只是 `CREATE DATABASE` 的另一种写法。BigQuery 叫 dataset，
ClickHouse 也叫 database。Snowflake 又不一样：schema 是 database 里面的
一层。

同一份模型定义换到另一个后端，`schema_name` 的含义可能就变了。本文说明怎么
声明它、它在什么情况下会出现在 SQL 里，以及哪些事情不由你决定。

## 1. 声明 schema

用类属性 `__schema_name__` 声明。不写就是 `None`，也就是不加限定。

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

需要动态决定的话，重写 `schema_name()` 就行。常见几种：

```python
# 1) 固定一个 schema —— 最常见
class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = "app"

# 2) 用基类，让一批模型共用同一个 schema
class AppModel(ActiveRecord):
    __schema_name__ = "app"

class User(AppModel):
    __table_name__ = "users"

class Order(AppModel):
    __table_name__ = "orders"

# 3) 多租户：一个模型类，调用时再定
class Order(ActiveRecord):
    __table_name__ = "orders"

    @classmethod
    def schema_name(cls) -> str:
        return f"tenant_{current_tenant_id()}"

# 4) 从配置读
class User(ActiveRecord):
    __schema_name__ = settings.db_schema
```

`__table_name__` 和 `__schema_name__` 要分开写。写成 `__table_name__ = "app.users"`
不会得到带限定的引用——整串会被当成一个标识符加引号，渲染成 `FROM "app.users"`，
PostgreSQL 随后报 `relation "app.users" does not exist`。要限定就设
`__schema_name__`；在支持三段式的地方，也可以直接传 `(schema, table)` 元组。

## 2. schema 会不会出现在 SQL 里

判定过程只有一条链，中间没有任何配置开关：

```
__schema_name__  ->  schema_name()  ->  TableExpression.schema_name
                                          / Column.schema_name
                                      ->  format_table() / format_column()
```

你只需要提供两个输入：schema 本身，以及表别名。

渲染结果：

| `FROM` 里的范围 | 列引用 | PostgreSQL |
|---|---|---|
| `"users"`（不加限定） | `"users"."id"` | 合法 |
| `"ar_crm"."users"` | `"ar_crm"."users"."id"` | 合法 |
| `"ar_crm"."users"` | `"users"."id"` | 合法 |
| `"ar_crm"."users" AS "u"` | `"u"."id"` | 合法 |
| `"ar_crm"."users" AS "u"` | `"ar_crm"."users"."id"` | **报错** |
| `"ar_crm"."users" AS "u"` | `"users"."id"` | **报错** |

一句话：**没有别名时两种写法都合法，有别名时只能用别名。** 所以"总是写两段式"
这条规则自己就不自洽——恰好在有别名的时候它是错的。

对别名的处理发生在**构造列表达式**的时候，不是在渲染的时候。只要表别名生效，
`FieldProxy` 就把 schema 置成 `None`。手工构造 `Column` 会绕过这道保护，所以
手写的 `Column(dialect, "id", table="u", schema_name="ar_crm")` 会渲染出
PostgreSQL 不接受的三段式。

### 三件你控制不了的事

- **`search_path`** —— 建连时作为 libpq 参数下发，整个连接生命周期内固定，
  没法按查询或按事务切换。不带限定的名字按它解析。
- **连接的 `default_schema` 配置** —— 从来没有影响过生成的 SQL。不设
  `__schema_name__` 的模型按 `search_path` 解析，想改这个行为请用 `search_path`。
- **别名** —— 一旦设了别名，schema 会按设计从列引用里丢掉。

## 3. 别这么写

```python
__table_name__ = "app.users"   # 错误：渲染成 FROM "app.users"
__schema_name__ = ""          # 错误：空串是笔误，"不加限定"请用 None
```

空 schema 要单独说一句：`""` 不是"不加限定"的写法，`None` 才是。空串会被直接
拒绝，非字符串值同样如此。`TableExpression(schema_name=...)` 和所有 DML 的
`*Options` 对象都按这个规则。

## 4. DDL 语句自己带 schema 参数

`__schema_name__` 只管读和写。构造 DDL 时不会读它——迁移里想写哪个 schema，
得自己写出来。

| 语句 | 怎么限定 |
|---|---|
| `SELECT` / `INSERT` / `UPDATE` / `DELETE` | 不用写，模型上的 `__schema_name__` 会自动带上 |
| `CREATE TABLE` / `DROP TABLE` | 传 `TableExpression(dialect, "users", schema_name="app")` |
| `ALTER TABLE` | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` / `REFRESH` VIEW（含物化视图） | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` TYPE | `schema_name="app"` |
| `CREATE INDEX` / `DROP INDEX`（含全文索引） | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` SEQUENCE | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` DOMAIN | `schema_name="app"` |
| `CREATE` / `DROP` FUNCTION | `schema_name="app"` |
| `CREATE` / `DROP` TRIGGER | `schema_name="app"` |
| `TRUNCATE` | 字段叫 `schema`，不是 `schema_name` |

`schema_name` 默认是 `None`，也就是不加限定——和表达式层其他地方一致。

模型指向 `app.users`、迁移却建了 `public.users`，这两边不会自动对齐：迁移得自己
写明要哪个 schema。现在能直接写，不必再手工拼限定名。

后端不支持命名空间时，传入 schema 会抛 `UnsupportedFeatureError`，不会悄悄
丢掉。SQLite 是最常见的一种：它没有 schema 层，限定名发过去服务器会拒。

## 5. 限定符什么时候定下来

`Model.c.field` 在**构造表达式的那一刻**就把 `table_name()` 和 `schema_name()`
快照了，不是执行的时候：

```python
condition = Order.c.total > 100     # 已经绑在当前 schema 上
Order.__schema_name__ = "tenant_b"  # 对上面那个 condition 已经太晚了
condition = Order.c.total > 100     # 重新构造才能拿到新 schema
```

`table_name()` 也一样。切租户的时候，请切完再重建条件表达式；或者每个租户用一个
独立的模型类。

## 6. 各后端的差异

`schema_name` 具体指什么，每个后端自己定义。都接受这个参数，但解释不一样。
下表是各后端的实际情况；本文里的 `"app"."users"` 是 PostgreSQL / SQL Server /
Oracle 的写法。

| 后端 | `supports_schema()` | `schema_name` 指向 | 渲染为 |
|---|---|---|---|
| PostgreSQL | 是 | 当前 database 内的 schema | `"app"."users"` |
| SQL Server | 是 | 当前 database 内的 schema | `[app].[users]` |
| Oracle | 是 | schema，也就是属主用户 | `"APP"."USERS"`（折为大写） |
| Snowflake | 是 | schema，**隶属于** database，是独立的一层 | 要配合 `CURRENT_DATABASE()` 才算完全限定 |
| BigQuery | 是 | dataset；列引用永不带 schema | `` `app.users` `` |
| MariaDB | 是 | **database**：`schema` 是 `database` 的同义词 | `` `app`.`users` `` |
| MySQL | 是 | **database**：和 MariaDB 一样 | `` `app`.`users` `` |
| ClickHouse | 是 | **database**：没有独立的 schema 层，`CREATE SCHEMA` 是语法错误，但 `schema_name` 照样能用 | `` `app`.`users` `` |
| SQLite、Firebird | 否 | 没有命名空间这一层 | 拒绝 |

三点值得注意，也正是同一份模型定义不能想当然认为在哪儿都一样的原因：

- **只有 Snowflake 有自己独立的 schema 层。** 它的完全限定名是
  `<database>.<schema>.<object>`，光给一个 `schema_name` 定不下来是哪个对象。
- **MySQL、MariaDB 和 ClickHouse 都把这个值当 database。** MySQL 和 MariaDB 里
  `schema` 和 `database` 是同一个词，所以 `CREATE SCHEMA`、`SHOW SCHEMAS` 都能用，
  列出来的就是 database。ClickHouse 连这个词都没有——它没有 `CREATE SCHEMA`，
  但 `schema_name` 照样能用，只是解释成 database，所以 `supports_schema()`
  是 `True`。没有独立的 schema 层，不等于这个值不能用。
- **框架不校验这个值。** 不会拿它和连接去对，所以一个和会话当前命名空间不一样的
  `schema_name`，要么指向另一个对象，要么哪儿都指不到。

## 7. 怎么分层比较省事

让 `search_path` 管常规情况，`__schema_name__` 只留给例外：

```python
config = PostgresConnectionConfig(
    ...,
    search_path="app,public",   # 常规表用不带限定的名字解析
)
```

- **只有一个 schema** —— 干脆别设 `__schema_name__`。不带限定的名字配合
  `search_path`，DML、DDL 和内省三者能对得上，也完全不会出现三段式列引用。
- **多个 schema** —— 只给那些不在 `search_path` 里的模型设 `__schema_name__`。
  例外越少，踩上面那些坑的机会就越小。
- **跨 schema JOIN** —— 两边各自限定自己的范围就行，不用额外配置：

  ```python
  Order.query().join(
      Customer, on=Order.c.customer_id == Customer.c.id
  ).select(Order.c.id, Customer.c.name)
  # SELECT ... FROM "shop"."orders" JOIN "crm"."customers" ON ...
  ```