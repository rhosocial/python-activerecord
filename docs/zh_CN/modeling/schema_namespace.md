# docs/zh_CN/modeling/schema_namespace.md
# Schema 命名空间

> 怎么把一个模型绑定到数据库的 schema 上，以及这个绑定在什么条件下才会出现在
> 最终执行的 SQL 里。

多数数据库里，schema 是最接近「命名空间」的概念。PostgreSQL、SQL Server 和
Oracle 把它当作对象名本身的一部分；MySQL/MariaDB 叫同一层东西 database；BigQuery
叫 dataset；Snowflake 则把它嵌在 database 内部。本文讲三件事：在模型上怎么声明
schema；DDL 里每个对象的 schema 怎么分别指定；以及哪些环节不由这个声明覆盖。

文中每段 SQL 都跑过一遍才写下来，代码取自 `fix/schema-name-propagation-gaps` 分支。
限定名的渲染用的是核心包自带的 `rhosocial.activerecord.backend.impl.dummy.backend.DummyDialect`，
它的 `supports_schema()` 为 `True`。标识符的引号风格是 PostgreSQL 的；为什么把
PostgreSQL 当作参照方言，以及内置的 SQLite 后端是什么行为，见 [§11](#11-sqlite以及本文为什么用-postgresql-的写法)。

## 1. 声明 schema

schema 用类属性 `__schema_name__` 声明。这个属性可以不写，默认值是 `None`，含义是
「按连接默认解析」。

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

这个属性只有 `schema_name()` 一个读取点，需要动态决定命名空间时重写它即可。按常见程度，
下面四种写法：

```python
# 1) 固定值 —— 最常见，这个模型的每条语句都带限定
class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = "app"

# 2) 用基类，让一批模型共用同一个命名空间
class AppModel(ActiveRecord):
    __schema_name__ = "app"

class User(AppModel):
    __table_name__ = "users"

class Order(AppModel):
    __table_name__ = "orders"

# 3) 多租户：每个命名空间一个模型类，调用时再选
class Order(ActiveRecord):
    __table_name__ = "orders"

    @classmethod
    def schema_name(cls) -> str:
        return f"tenant_{current_tenant_id()}"

# 4) 从配置读
class User(ActiveRecord):
    __schema_name__ = settings.db_schema
```

`__table_name__` 和 `__schema_name__` 是分开的两个属性，不要合并：

```python
__table_name__ = "app.users"   # 错误
```

整串会被当成一个标识符加引号，渲染出来是 `FROM "app.users"` —— 一个内部含点的
标识符，不是带限定的引用。PostgreSQL 随后报 `relation "app.users" does not exist`。
要限定就设 `__schema_name__`。

## 2. 命名空间怎么进入 SQL

判定只有一条链，中间没有任何配置开关：

```
__schema_name__  ->  schema_name()  ->  TableExpression.schema_name
                                          / Column.schema_name
                                      ->  format_table() / format_column()
```

你提供两个输入，其余都是推论：schema 本身，以及有没有表别名生效。

渲染结果：

| `FROM` 里的范围 | 列引用 | PostgreSQL |
|---|---|---|
| `"users"`（不加限定） | `"users"."id"` | 合法 |
| `"ar_crm"."users"` | `"ar_crm"."users"."id"` | 合法 |
| `"ar_crm"."users"` | `"users"."id"` | 合法 |
| `"ar_crm"."users" AS "u"` | `"u"."id"` | 合法 |
| `"ar_crm"."users" AS "u"` | `"ar_crm"."users"."id"` | **报错** |
| `"ar_crm"."users" AS "u"` | `"users"."id"` | **报错** |

也就是说，**没有别名时两种写法都合法；有别名时只能用别名**。「一律写成两段式」
这条规则自己就不自洽 —— 恰好在有别名的地方它是错的。

对别名的处理发生在**构造列表达式**的那一刻，不是渲染的时候。表别名一生效，
`FieldProxy` 就把 `schema_name` 置成 `None`，所以：

```python
Order.query().select(Order.c.with_table_alias("o").id).to_sql()[0]
# SELECT "o"."id" FROM "shop"."orders"
```

列上的 schema 去掉了，范围上的还在。绕开 `FieldProxy` 手工构造 `Column` 就得不到这道
保护，`Column(dialect, "id", table="u", schema_name="ar_crm")` 会渲染成
`"ar_crm"."u"."id"`，也就是 PostgreSQL 不接受的三段式。

### 三件不由你决定的事

- **`search_path`** —— `PostgresConnectionConfig.search_path` 在建连时追加进交给
  psycopg 的连接参数（`python-activerecord-postgres` 的
  `backend/impl/postgres/config.py`），整个连接生命周期内固定，没法按查询或按事务
  切换。不带限定的名字按它解析。
- **连接的 `default_schema` 配置** —— 它不会发到服务端：`PostgresConnectionConfig`
  下发的参数里没有这一项，它也从来没有影响过生成的 SQL。它只被读到一个地方，
  即 PostgreSQL 内省器在调用方没给 schema 时去哪一层找；优先级排在 `search_path`
  的第一项和 `"public"` 前面。
- **别名** —— 一旦设了别名，schema 就按设计从列引用里去掉。

## 3. 校验发生在什么时候

表达式在构造期只收参数，不做检查。命名空间是在渲染阶段判定的，判定入口是
`SchemaMixin.validate_schema_name()`；所有要渲染限定名的格式化方法都经由
`format_table()` 或 `format_column()` 走到那里（`backend/dialect/mixins/ddl_schema.py`）。

那里按「一旦漏掉就会长期无人察觉」的程度，依次拒绝三类取值：

- 既不是 `None` 也不是字符串的值；
- 空串或纯空白串 —— `format_table()` 会把它当成「没有 schema」，于是要求
  `app.users` 的调用方拿到的其实是 `users`；
- 方言 `supports_schema()` 为 `False` 时传入的任何值 —— 它会渲染成服务端拒绝的 SQL。

```python
TableExpression(dialect, "users", schema_name="")     # 构造成功
expr.to_sql()
# ValueError: TableExpression.schema_name must be a non-empty string;
#             use None for an unqualified reference
```

模型层是同一个检查，只是入口不同：

```python
class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = ""            # 这是笔误，不是「用空串表示 public」的写法

User.build_table_reference(dialect).to_sql()
# ValueError: TableExpression.schema_name must be a non-empty string;
#             use None for an unqualified reference
```

还有第四种情况在校验之前就分掉了：没有实现 `SchemaSupport` 协议的方言，本来就没有
命名空间可谈，`format_table()` 既不校验也不加限定 —— 它携带的 schema 不归它管，
直接忽略。只有实现了 `SchemaSupport` 的方言才会被要求对这个值负责。
[§10](#10-各后端支持矩阵) 列出的后端都实现了这个协议。

为什么不把空串当成「没传」，而要拒绝？渲染层确实是这么退化的，问题恰恰出在这里。
要求 `app.users` 的调用方会拿到 `users`，不报错也不告警，语句照常执行 —— 只要连接的
`search_path` 里含有 `app`，它就落在另一张表上。而空串几乎总是命名空间丢失的入口：
某个 f-string 拼出来是空的、`config.get(...) or ""`、环境变量没设。这些场景里，调用方
恰恰最不容易察觉命名空间没了。

## 4. `TableExpression` 承载全部限定名

「一个具名对象，可以带命名空间」在整个表达式层只有一种表达方式，就是
`TableExpression`。它承担两个角色：

- `FROM` 子句里的**范围**，也就是表或视图；
- DDL **指名的对象**，也就是索引、序列、类型、函数。

```python
TableExpression(
    dialect,
    name: str,
    schema_name: Optional[str] = None,
    alias: Optional[str] = None,
    temporal_options: Optional[Dict[str, Any]] = None,
    name_need_quote: bool = True,
    alias_need_quote: bool = True,
    schema_need_quote: bool = True,
)
```

`alias` 和 `temporal_options` 只在 `FROM` 范围这个角色上有意义；用在别处就保持默认
值。同一个表达式能兼两个角色，原因就在这里。

渲染时通往这个载体的路径有两条，语句走哪一条，取决于它要指名的对象有几个：

| 语句类别 | 命名空间从哪里来 |
|---|---|
| `ALTER TABLE`、`TRUNCATE`、`UPDATE`、`MERGE` | `table` 传 `TableExpression` |
| `CREATE` / `DROP` INDEX、全文索引 | `table` 传 `TableExpression`；`schema_name` 指索引 |
| `CREATE` / `DROP` TRIGGER | `table` 和 `function_name` 传 `TableExpression`；`schema_name` 指触发器 |
| `CREATE` / `DROP` TABLE | `table` 传 `TableExpression` |
| VIEW、TYPE、SEQUENCE、FUNCTION、DOMAIN | 一个普通字符串 `schema_name`，由格式化方法把对象名包成 `TableExpression` |

### 裸字符串：一律拒绝

凡是给表命名的参数都要求 `TableExpression`。已经不存在任何一条会照收字符串、然后
悄悄把它变成无限定引用的语句：

| 参数 | 传裸 `str` 的结果 |
|---|---|
| `CreateTableExpression.table` | 构造期抛 `TypeError` |
| `DropTableExpression.table` | 构造期抛 `TypeError` |
| `TruncateExpression.table` | 构造期抛 `TypeError` |
| `AlterTableExpression.table` | 构造期抛 `TypeError` |
| `CreateIndexExpression.table`、`DropIndexExpression.table` | 构造期抛 `TypeError` |
| `CreateFulltextIndexExpression.table`、`DropFulltextIndexExpression.table` | 构造期抛 `TypeError` |
| `CreateTriggerExpression.table`、`CreateTriggerExpression.function_name` | 构造期抛 `TypeError` |
| `DropTriggerExpression.table` | 构造期抛 `TypeError` |
| `InsertExpression.into` | 构造期抛 `TypeError` |
| `DeleteExpression.tables` | 构造期抛 `TypeError`，逐个元素检查 |
| `UpdateExpression.table` | 构造期抛 `TypeError` |
| `MergeExpression.target_table` | 构造期抛 `TypeError` |

报错信息里带着参数名，所以从消息就能知道该怎么改：

```
TypeError: table must be a TableExpression, got str
TypeError: into must be a TableExpression, got str
TypeError: tables must be a TableExpression, got str
TypeError: target_table must be a TableExpression, got str
```

这份统一正是重点所在。早期版本会把裸字符串包成一个无名的 `TableExpression`，于是本想
限定作用域的调用方拿到未限定的 SQL，而且没有任何报错：

```python
CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table="users",             # 照收，然后命名空间就丢了
    columns=["email"],
    schema_name="app",
).to_sql()[0]
# CREATE INDEX "app"."idx_users_email" ON "users" ("email")
```

`schema_name` 限定的是索引，表仍落在连接的默认命名空间里。输出里没有任何地方说明这
不是你想要的。写成 `table=TableExpression(dialect, "users", schema_name="app")`，
两边才会都被限定。

### 两个例外，以及它们为什么不算表

仍有两个字段接受普通字符串，而它们都不给表命名：

- `Column.table` 是**用来限定列的名字**，不是要读取的表。它是 `str`，与同一个表达式上的
  `schema_name` 配对使用。
- PostgreSQL 分区的 `parent_table` 同样是为 `INHERITS` / `PARTITION BY` 子句指明一张
  已存在的表，并不是该语句的目标。

除此之外，如果某个后端的服务器命名空间层级比 core 建模的更多，它会新增自己的表达式，
而不是把共享的那个拓宽。Snowflake 有三层，于是声明了带 `database_name` 的
`SnowflakeTableExpression`；`TableExpression` 本身只到 `schema_name` 为止。

## 5. DDL：每个对象各自选择命名空间

> **`__schema_name__` 决定读写的命名空间。** 手工拼装的表达式不读它 —— 会替你读的
> 是 [§6](#6-模型层的-ddl-工厂方法) 那组工厂方法。

| 语句 | 怎么限定 |
|---|---|
| `SELECT` / `INSERT` / `UPDATE` / `DELETE` | 自动，来自模型上的 `__schema_name__` |
| `CREATE TABLE` / `DROP TABLE` | `table=TableExpression(dialect, "users", schema_name="app")` |
| `ALTER TABLE` | `table=TableExpression(dialect, "users", schema_name="app")` |
| `TRUNCATE` | `table=TableExpression(dialect, "users", schema_name="app")` |
| `CREATE` / `ALTER` / `DROP` / `REFRESH` VIEW（含物化视图） | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` TYPE | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` SEQUENCE | `schema_name="app"` |
| `CREATE` / `ALTER` / `DROP` DOMAIN | `schema_name="app"` |
| `CREATE` / `DROP` FUNCTION | `schema_name="app"` |
| `CREATE INDEX` / `DROP INDEX`（含全文索引） | 索引用 `schema_name="app"`，表用 `table=TableExpression(...)` |
| `CREATE` / `DROP` TRIGGER | 触发器用 `schema_name="app"`，另加 `table=` 与 `function_name=` |

所有 `schema_name` 的默认值都是 `None`，即不加限定 —— 和表达式层别处一致。

### 索引：索引与表分别放置

一条索引语句要指名两个对象，也就带两个命名空间。`schema_name` 限定**索引名**，
`table` 限定**表**。

```python
# 索引和表都在 "app"
CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table=TableExpression(dialect, "users", schema_name="app"),
    columns=["email"],
    schema_name="app",
).to_sql()[0]
# CREATE INDEX "app"."idx_users_email" ON "app"."users" ("email")

# 索引在 "app"，表在 "sales"
CreateIndexExpression(
    dialect,
    index_name="idx_shared",
    table=TableExpression(dialect, "orders", schema_name="sales"),
    columns=["user_id"],
    schema_name="app",
).to_sql()[0]
# CREATE INDEX "app"."idx_shared" ON "sales"."orders" ("user_id")

# 索引名留裸，表带限定
CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table=TableExpression(dialect, "users", schema_name="app"),
    columns=["email"],
).to_sql()[0]
# CREATE INDEX "idx_users_email" ON "app"."users" ("email")
```

`DropIndexExpression` 的拆分方式相同：

```python
DropIndexExpression(
    dialect,
    index_name="idx_users_email",
    table=TableExpression(dialect, "users", schema_name="app"),
    schema_name="app",
).to_sql()[0]
# DROP INDEX "app"."idx_users_email" ON "app"."users"
```

### 触发器：三个命名空间各自指定

触发器要指名三个对象：触发器本身、它挂着的表、它调用的函数。三者各自带命名空间。

```python
CreateTriggerExpression(
    dialect,
    trigger_name="trg_users_audit",
    table=TableExpression(dialect, "users", schema_name="app"),
    timing=TriggerTiming.AFTER,
    events=[TriggerEvent.UPDATE],
    function_name=TableExpression(dialect, "audit_row", schema_name="util"),
    schema_name="monitor",
).to_sql()[0]
# CREATE TRIGGER "monitor"."trg_users_audit" AFTER UPDATE ON "app"."users"
#   FOR EACH ROW EXECUTE "util"."audit_row"
```

`DropTriggerExpression` 收触发器的 `schema_name`，表的限定由 `table` 自己带：

```python
DropTriggerExpression(
    dialect,
    trigger_name="trg_users_audit",
    table=TableExpression(dialect, "users", schema_name="app"),
    schema_name="app",
).to_sql()[0]
# DROP TRIGGER "app"."trg_users_audit" ON "app"."users"
```

### 仍然只接收一个 `schema_name` 的语句

视图、类型、序列、函数、域各自只指名一个对象，所以收一个字符串 `schema_name`，
由格式化方法把名字包起来：

```python
CreateSequenceExpression(dialect, sequence_name="order_seq", schema_name="app").to_sql()[0]
# CREATE SEQUENCE "app"."order_seq" NO CYCLE

CreateFunctionExpression(dialect, function_name="audit_row", schema_name="util").to_sql()[0]
# CREATE FUNCTION "util"."audit_row" () LANGUAGE plpgsql
```

### MySQL 与 MariaDB：索引名不能带限定

在这两个后端上，索引归属于拥有它的表所在的命名空间，文法也拒绝带限定的索引名。两个
方言的 `supports_index_schema_qualification()` 都返回 `False`，渲染时直接拒绝，而不是
生成服务端会拒绝的 SQL：

```python
CreateIndexExpression(
    mariadb_dialect,
    index_name="idx_users_email",
    table=TableExpression(mariadb_dialect, "users", schema_name="app"),
    columns=["email"],
    schema_name="app",
).to_sql()
# UnsupportedFeatureError: 'MariaDB' dialect does not support a
# namespace-qualified index name. … Qualify the table instead by passing it as
# a TableExpression with schema_name set.
```

在这两个后端上，把命名空间放在表上才是正确写法，也正是渲染出来的结果：

```python
CreateIndexExpression(
    mariadb_dialect,
    index_name="idx_users_email",
    table=TableExpression(mariadb_dialect, "users", schema_name="app"),
    columns=["email"],
).to_sql()[0]
# CREATE INDEX `idx_users_email` ON `app`.`users` (`email`)
```

这项检查覆盖 `CREATE INDEX`、`DROP INDEX`、`CREATE FULLTEXT INDEX` 和
`DROP FULLTEXT INDEX`。其余后端都取默认值 `True`。

## 6. 模型层的 DDL 工厂方法

`__schema_name__` 原本只覆盖查询层，迁移里的 DDL 只能在每个调用点自己写命名空间。现在
模型上有七个类方法，直接为这个模型构造处于它自己命名空间里的 DDL：

```python
Model.build_table_reference(dialect, alias=None)
Model.build_create_table_statement(dialect, columns, *, indexes=None,
                                   table_constraints=None, temporary=False,
                                   if_not_exists=False)
Model.build_drop_table_statement(dialect, if_exists=False)
Model.build_truncate_statement(dialect, restart_identity=False, cascade=False)
Model.build_alter_table_statement(dialect, actions)
Model.build_create_index_statement(dialect, index_name, columns, *,
                                    index_schema_name=None, **options)
Model.build_drop_index_statement(dialect, index_name, *,
                                  index_schema_name=None, if_exists=False, **options)
```

七个方法全部经过 `build_table_reference()`，所以迁移不会把这条语句限定在模型的命名
空间里、下一条又限定到别处：

```python
class User(ActiveRecord):
    __table_name__ = "users"
    __schema_name__ = "app"

User.build_table_reference(dialect).to_sql()[0]
# "app"."users"
User.build_table_reference(dialect, alias="u").to_sql()[0]
# "app"."users" AS "u"

User.build_create_table_statement(dialect, [
    ColumnDefinition(dialect, "id", IntegerType(dialect)),
    ColumnDefinition(dialect, "name", TextType(dialect)),
]).to_sql()[0]
# CREATE TABLE "app"."users" ("id" INTEGER, "name" TEXT)

User.build_drop_table_statement(dialect, if_exists=True).to_sql()[0]
# DROP TABLE IF EXISTS "app"."users"

User.build_truncate_statement(dialect, restart_identity=True).to_sql()[0]
# TRUNCATE TABLE "app"."users" RESTART IDENTITY

User.build_alter_table_statement(dialect, [
    AddColumn(dialect, ColumnDefinition(dialect, "email", TextType(dialect))),
]).to_sql()[0]
# ALTER TABLE "app"."users" ADD COLUMN "email" TEXT
```

两个索引工厂方法的 `index_schema_name` 默认取模型的命名空间；索引要放到别处时显式传入：

```python
User.build_create_index_statement(dialect, "idx_users_email", ["email"]).to_sql()[0]
# CREATE INDEX "app"."idx_users_email" ON "app"."users" ("email")

User.build_create_index_statement(
    dialect, "idx_users_email", ["email"], index_schema_name="ops",
).to_sql()[0]
# CREATE INDEX "ops"."idx_users_email" ON "app"."users" ("email")

User.build_drop_index_statement(
    dialect, "idx_users_email", index_schema_name="ops", if_exists=True,
).to_sql()[0]
# DROP INDEX IF EXISTS "ops"."idx_users_email" ON "app"."users"
```

没有 `__schema_name__` 的模型，构造出来的是同样的一批语句，只是不带限定；索引仍然可以
单独移动：

```python
Plain.__schema_name__ is None
# True

Plain.build_table_reference(dialect).to_sql()[0]
# "plain"

Plain.build_create_index_statement(
    dialect, "idx_plain_id", ["id"], index_schema_name="ops",
).to_sql()[0]
# CREATE INDEX "ops"."idx_plain_id" ON "plain" ("id")
```

**手工拼装的语句不会带上 `__schema_name__`。** 要么自己传
`TableExpression(dialect, name, schema_name=...)`，要么用上面这组工厂方法。两种写法的
区别仅此一处：工厂方法替你读 `schema_name()`，别的都不会。

## 7. 各类查询如何使用命名空间

`__schema_name__` 只被 `schema_name()` 读到，而模型构造出的每个查询都会把它带下去，
所以命名空间天然跟着模型走，不需要每种查询类型各自处理。真正有差别的是生成出来的
SQL 长什么样。

下面的例子用 `DummyDialect`，两个模型：`Order` 在 `"shop"`，`Customer` 在 `"crm"`。

### ActiveQuery —— DML 自带命名空间

模型的 `query()` 会限定它构造的每一个范围，`SELECT`、`INSERT`、`UPDATE`、`DELETE`
一视同仁：

```python
Order.query().select(Order.c.id).to_sql()[0]
# SELECT "shop"."orders"."id" FROM "shop"."orders"

Order.query().where(Order.c.total > 100).to_sql()
# SELECT * FROM "shop"."orders"
#   WHERE "shop"."orders"."total" > ?        -- 参数 (100,)
```

列是三段的：范围没有别名，命名空间一路限定到列。别名一旦生效，列上的命名空间就去掉
了 —— 别名本身已经足以标识这个范围：

```python
Order.query().select(Order.c.with_table_alias("o").id).to_sql()[0]
# SELECT "o"."id" FROM "shop"."orders"
```

这不是简化。给已取别名的范围再加命名空间限定，在 PostgreSQL 和 SQL Server 上都是
语法错误。

`update_all()` 与 `delete_all()` 走的是 `UpdateOptions` 和 `DeleteOptions`，把模型的
`table_name()` 和 `schema_name()` 传进去（`query/active_query.py`）。DML 的 options
对象 —— `InsertOptions`、`UpdateOptions`、`DeleteOptions` —— 是表名仍以字符串给出的
地方：`UpdateOptions(table="orders", schema_name="shop", …)`，由后端转成
`UpdateExpression` 并附上命名空间（`backend/base/operations.py`）。

### join —— 两侧各自限定

不需要额外配置。两侧模型各带各的命名空间，一条语句里可以跨两个：

```python
Order.query().join(Customer, on=Order.c.id == Customer.c.id).to_sql()[0]
# SELECT * FROM "shop"."orders" JOIN "crm"."customers"
#   ON "shop"."orders"."id" = "crm"."customers"."id"
```

### SetOperationQuery —— 自己不带命名空间

`UNION` / `INTERSECT` / `EXCEPT` 是把两个查询合起来，并不指名某个对象，没有东西需要
限定。各分支保留自己的：

```python
Order.query().union(Customer.query()).to_sql()[0]
# SELECT * FROM "shop"."orders" UNION SELECT * FROM "crm"."customers"
```

一条语句里出现两个命名空间在 PostgreSQL 上是合法的，所以两个绑定 schema 的模型做
`UNION` 不需要特殊处理。

### CTEQuery —— CTE 的名字不在命名空间里

CTE 是给本条查询用的名字，不是数据库里的对象，所以永远不加限定 —— 加了等于去某个
命名空间里找一张同名的表：

```python
(CTEQuery(backend)
    .with_cte("recent_orders", Order.query().select(Order.c.id))
    .from_cte("recent_orders")
    .to_sql()[0])
# WITH "recent_orders" AS (SELECT "shop"."orders"."id" FROM "shop"."orders")
# SELECT * FROM "recent_orders"
```

里面的 `SELECT` 仍然带着模型的命名空间，只有 CTE 自身的名字是裸的。

### 软删除 —— restore() 同样带

`restore()` 用模型的 `table_name()` 和 `schema_name()` 构造 `UpdateOptions`
（`field/soft_delete.py`），所以它的限定方式和 `delete()` 一致。如果 restore 漏掉
命名空间，就会把默认命名空间里那张同名表的 `deleted_at` 清掉，而本该恢复的那一行仍然
是软删除状态 —— 这是一个跨命名空间的写操作，任何只读的断言都发现不了。

## 8. 限定符什么时候定下来

`Model.c.field` 在**构造表达式的那一刻**就把 `table_name()` 和 `schema_name()` 快照了，
不是执行的时候：

```python
condition = Order.c.total > 100     # 已经绑在 tenant_a 上
Order.__schema_name__ = "tenant_b"
condition.to_sql()[0]
# "tenant_a"."orders"."total" > ?        -- 没变
condition = Order.c.total > 100     # 重新构造才能拿到新的命名空间
condition.to_sql()[0]
# "tenant_b"."orders"."total" > ?
```

`table_name()` 也一样。切租户时，请切完再重建条件表达式；或者每个租户用一个独立的
模型类。

## 9. 守卫子句被拒绝，而不是被丢弃

后端没有的守卫子句，在渲染阶段被拒绝，而不是丢掉标志让语句照发：

| 语句 | 后端 | 守卫 |
|---|---|---|
| `DROP TABLE IF EXISTS` | Oracle | `supports_if_exists_table()` 为 `False`，传标志抛 `UnsupportedFeatureError` |
| `CREATE SCHEMA IF NOT EXISTS` | SQL Server | `supports_schema_if_not_exists()` 为 `False`，传标志抛 `UnsupportedFeatureError` |
| `DROP SCHEMA IF EXISTS` | SQL Server | `supports_schema_if_exists()` 为 `False`，传标志抛 `UnsupportedFeatureError` |
| `DROP SCHEMA CASCADE` | SQL Server | `supports_schema_cascade()` 为 `False`，传标志抛 `UnsupportedFeatureError` |

```python
DropTableExpression(
    oracle_dialect, TableExpression(oracle_dialect, "users", schema_name="app"),
    if_exists=True,
).to_sql()
# UnsupportedFeatureError: 'Oracle' dialect does not support DROP TABLE IF
# EXISTS. … Drop the flag, or guard the call yourself.

DropTableExpression(
    oracle_dialect, TableExpression(oracle_dialect, "users", schema_name="app"),
).to_sql()[0]
# DROP TABLE "APP"."USERS"
```

去掉标志是语义上的取舍，不是 SQL 上的取舍：不带 `IF EXISTS` 时，去 drop 一张已经不
存在的表就是错误。要在所有后端上都保持正确，就在应用代码里判断，或者先查系统目录。

## 10. 各后端支持矩阵

`schema_name` 具体指什么由各后端自己定义，大家并不一致。本文里的 `"app"."users"` 是
PostgreSQL / SQL Server / Oracle 的写法。

| 后端 | `supports_schema()` | `supports_index_schema_qualification()` | `schema_name` 指向 | 渲染为 |
|---|---|---|---|---|
| PostgreSQL | 是 | 是 | 当前 database 内的 schema | `"app"."users"` |
| SQL Server | 是 | 是 | 当前 database 内的 schema | `[app].[users]` |
| Oracle | 是 | 是 | schema，也就是属主用户 | `"APP"."USERS"`（折为大写） |
| Snowflake | 是 | 是 | schema，**隶属于** database，是独立的一层 | `"app"."orders"`，缺 database 一级并不完整 |
| BigQuery | 是 | 是 | dataset；列引用永不带 dataset | `` `app`.`orders` `` |
| MariaDB | 是 | **否** | **database**：`schema` 是 `database` 的同义词 | `` `app`.`users` `` |
| MySQL | 是 | **否** | **database**：和 MariaDB 一样 | `` `app`.`users` `` |
| ClickHouse | 是 | 是 | **database**：没有独立的 schema 层 | `` `app`.`users` `` |
| SQLite(内置)、Firebird | 否 | 是 | 没有命名空间这一层 | 拒绝，见 [§11](#11-sqlite以及本文为什么用-postgresql-的写法) |

三点结论，也正是同一份模型定义不能想当然认为在哪儿都一样的原因：

- **只有 Snowflake 有自己独立的 schema 层。** 它的完全限定名是
  `<database>.<schema>.<object>`，光给一个 `schema_name` 定不下来是哪个对象。
- **MySQL、MariaDB 和 ClickHouse 都把这个值当 database。** MySQL 和 MariaDB 里
  `schema` 和 `database` 是同一个词。ClickHouse 连这个词都没有 —— 它没有
  `CREATE SCHEMA`，但 `schema_name` 照样能用，只是解释成 database，所以
  `supports_schema()` 是 `True`。没有独立的 schema 层，不等于这个值不能用。
- **索引名不能带限定的只有 MySQL 和 MariaDB**，理由见
  [§5](#mysql-与-mariadb索引名不能带限定)。其余后端给了命名空间，就按给的放。

哪里都不检查的是：这个命名空间是否存在，以及会话当前用的是不是它。指向别的命名空间的
`schema_name`，要么落到另一个对象上，要么哪儿都落不到。

## 11. SQLite，以及本文为什么用 PostgreSQL 的写法

本包内置的后端是 SQLite，而 **SQLite 没有 schema 层** —— 不是弱，是没有。不带限定的
名字解析到数据库文件本身；带限定的名字指的是一个**附加数据库**，完全是另一套机制。

所以在内置后端上，`__schema_name__` 是个错误：

```python
class User(ActiveRecord):
    __schema_name__ = "app"      # 在 SQLite 上会报错
```

它报错而不是被忽略，原因正在这里。一个丢了命名空间的模型，会在每一条查询上去读写
默认命名空间，而生成的 SQL 里没有任何迹象能看出这一点。SQLite 实现了 `SchemaSupport`，
`supports_schema()` 返回 `False`，所以命名空间会被校验并拒绝：

```
TableExpression(sqlite_dialect, "users", schema_name="app").to_sql()
# UnsupportedFeatureError: 'SQLite' dialect does not support a schema-qualified
# reference. … SQLite has no namespace to qualify into, so schema_name='app'
# cannot be used.

TableExpression(sqlite_dialect, "users").to_sql()[0]
# "users"
```

在没有命名空间的后端上，**根本不要传命名空间**：让 `__schema_name__` 留空，由连接去决定。

那么这份文档还有个问题：既然内置后端一个都用不上，为什么通篇是 `"app"."users"`？

因为这里其余的 SQL 表面是照着 PostgreSQL 长出来的。通用表达式层以 PostgreSQL 方言
为基准 —— 通用 `TRUNCATE` 带着 `RESTART IDENTITY` 和 `CASCADE`，因为 PostgreSQL 有
这两个选项；没有的方言会明确拒绝，而不是默默忽略。schema 限定也是同一回事：参考写法、
关于三段引用与别名的规则，以及模型与 DDL 不一致时的行为，都来自 PostgreSQL。

文中的例子用 `DummyDialect` 渲染，也就是核心包自带的那个方言。它实现了 `SchemaSupport`，
`supports_schema()` 和 `supports_index_schema_qualification()` 都是 `True`；标识符按
PostgreSQL 的方式加引号，其余部分是通用层，所以不接服务器也能把限定渲染走通。你的后端
对同一个模型是什么行为，查 [§10](#10-各后端支持矩阵)。与方言无关的那些部分 —— 命名
空间从哪来、什么时候被读取、DDL 为什么得自己带 —— 在哪儿都成立。

## 12. 怎么分层

让 `search_path` 管常规情况，`__schema_name__` 只留给例外：

```python
config = PostgresConnectionConfig(
    ...,
    search_path="app,public",   # 常规表用不带限定的名字解析
)
```

- **只有一个 schema** —— 干脆别设 `__schema_name__`。不带限定的名字配合
  `search_path`，DML、DDL 和内省三者能对得上，也完全不会出现三段式列引用。
- **多个 schema** —— 只给那些不在 `search_path` 里的模型设 `__schema_name__`，并用
  [§6](#6-模型层的-ddl-工厂方法) 那组工厂方法为这个模型构造 DDL，两层就不会漂移。
  例外越少，撞上 [§3](#3-校验发生在什么时候) 那个空串、或
  [§4](#裸字符串一律拒绝) 那个不带限定的表的机会就越小。
- **跨 schema JOIN** —— 两侧各自限定自己的范围就行，不用额外配置：

  ```python
  Order.query().join(
      Customer, on=Order.c.id == Customer.c.id
  ).select(Order.c.id, Customer.c.name)
  # SELECT "shop"."orders"."id", "crm"."customers"."name"
  #   FROM "shop"."orders" JOIN "crm"."customers"
  #   ON "shop"."orders"."id" = "crm"."customers"."id"
  ```