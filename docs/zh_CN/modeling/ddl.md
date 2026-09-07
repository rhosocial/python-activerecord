# 推导 DDL

`rhosocial-activerecord` 支持从模型声明**自动推导** DDL：模型即 schema 的事实来源，
调用 `Model.generate_create_table(dialect)` 得到 `CreateTableExpression`，可直接执行、
检视，或参与表达式级 diff 生成迁移。本文专讲这条"模型 → DDL"推导链路——声明层
（Spec）、方言认领协议（`build_spec`）、默认推导规则，以及后端能力差异。

> 本文所有示例以 SQLite（核心内置后端）演示，并附**真实生成结果**。
> 表达式层（`CreateTableExpression` / `ColumnDefinition` 等）本身的用法见
> [后端表达式文档](../backend/expression/statements.md)；各后端特定 Spec 见
> [后端 DDL 特征支持](#后端-ddl-特征支持与文档索引)。

## 为什么要从模型推导

传统模式下同一张表有两套独立描述：模型字段（驱动读写）+ 手写建表 DDL（驱动建表）。
两处会漂移：加字段要改两处，漏改任一处即产生"模型能读写、表里没有该列"的隐性不一致。

推导 DDL 让模型成为**唯一事实来源**：

- 新增/修改字段只改模型一处；
- schema 与读写路径天然一致（同一份声明）；
- 推导产物与手工构造的表达式同型——diff/渲染/执行链路完全复用。

## 快速开始：零声明推导

**最简化定义是默认路径**——不写任何 DDL 声明，模型即可建表：

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

class Account(ActiveRecord):
    __table_name__ = "accounts"

    code: str
    type: str
    amount: float
    is_active: bool = True   # 有默认值 → 可空列

expr = Account.generate_create_table(SQLiteDialect())
sql, params = expr.to_sql()
# sql: 'CREATE TABLE "accounts" ("code" TEXT NOT NULL, "type" TEXT NOT NULL,
#        "amount" REAL NOT NULL, "is_active" NUMERIC)'
# params: ()
```

默认推导规则：

| 规则 | 说明 |
|------|------|
| 列名 = 字段名 | 可用 `UseColumn("col_name")` 覆盖 |
| 列类型 = 方言建议 | Python 类型经 `dialect.suggest_column_type()` 映射（SQLite：`str`→TEXT、`int`→INTEGER、`float`→REAL；MySQL/PG 各有原生映射） |
| 必填字段自动 `NOT NULL` | `Optional[T]` 或有默认值的字段保持可空 |
| 主键 | 按 `primary_key_columns()` 规则；整型自增主键渲染 `AUTOINCREMENT`（SQLite）/ `IDENTITY` 等 |
| 复合主键 | 多列 PK 渲染为表级 `PRIMARY KEY (col1, col2)` |

## DDL 特征声明（Spec）

需要偏离默认行为时，通过 **Spec** 声明特征。Spec 是纯声明对象：
**定义时不需要任何方言/后端**——模型体 import 时即可构造。

### 方言认领机制（build_spec）

生成 DDL 时，方言对每个 Spec 调用 `build_spec(spec)`：

- **接受** → 返回构造好的表达式层实例（`TableConstraint` / `IndexDefinition` /
  `ColumnConstraint` / `PartitionClause` …）；
- **不接受** → 返回 `None`，该 Spec 被**静默忽略**。

三条关键原则：

1. **是否支持由后端自决**。通用 Spec 只是"语义标准 + 核心默认翻译"的起点，
   后端可覆写翻译、也可拒绝；后端不支持的 Spec，测试断言"不支持"即可。
2. **未认领不报错**。声明列表是平权的：各后端只认领自己的。后端若认为忽略会
   静默丢约束，可在 `build_spec` 内自行抛错。用户不设 `required`/`suggested` 标记。
3. **零字符串键控**。后端亲和性 = 真实类身份（`isinstance`），无 `dialect.name`
   字符串匹配——自定义/第三方后端与内置后端平权。

### 两级声明入口

按"声明内容的归属"分两级：字段内容就近在字段上写，表级/复合内容集中到表级槽位。
两条路径底层统一——字段注解被折算为列级 Spec，与表级 Spec 一起交给方言
`build_spec` 认领，方言不需要区分来源。

**字段级注解**（列类型、单列约束、单列索引）：

```python
from typing import Annotated
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import (
    UseSqlType, UseConstraint, UseIndex, ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

class User(ActiveRecord):
    __table_name__ = "users"

    email: Annotated[str, UseSqlType(VarCharType(length=255))]
    age: Annotated[int, UseConstraint(
        ColumnConstraintType.CHECK,
        check_condition=lambda d: Column(d, "age") >= 18,   # 惰性谓词工厂
    )]
    is_active: Annotated[bool, UseIndex(
        "ix_users_active",
        partial_condition=lambda d: Column(d, "is_active") == 1,
    )] = True

expr = User.generate_create_table(SQLiteDialect())
sql, params = expr.to_sql()
# sql: 'CREATE TABLE "users" ("email" TEXT NOT NULL, "age" INTEGER
#        CHECK ("age" >= ?) NOT NULL, "is_active" NUMERIC)'
# params: (18,)
```

单列索引以独立语句执行（见[执行推导产物](#执行推导产物)）：

```python
expr.indexes[0].to_create_index_expression(SQLiteDialect(), expr.table).to_sql()
# ('CREATE INDEX "ix_users_active" ON "users" ("is_active") WHERE "is_active" = ?', (1,))
```

**表级声明列表**（复合约束、跨列 CHECK、分区）：

```python
from rhosocial.activerecord.base import UniqueSpec, CheckSpec

class Order(ActiveRecord):
    __table_name__ = "orders"

    __table_constraints__ = [
        UniqueSpec(columns=["account_id", "period"], name="uq_acc_period"),
        CheckSpec(
            condition=lambda d: Column(d, "debit_total") == Column(d, "credit_total"),
            name="ck_balance",
        ),
    ]

    account_id: int
    period: str
    debit_total: float
    credit_total: float

sql, _ = Order.generate_create_table(SQLiteDialect()).to_sql()
# sql: 'CREATE TABLE "orders" (..., CONSTRAINT "uq_acc_period" UNIQUE ("account_id", "period"),
#        CONSTRAINT "ck_balance" CHECK ("debit_total" = "credit_total"))'
```

### 通用 Spec 一览

| Spec | 说明 | 默认翻译 |
|------|------|----------|
| `CheckSpec(condition, name=?)` | CHECK；`condition` 可为就绪谓词或惰性工厂 `(dialect) -> SQLPredicate` | `TableConstraint(CHECK)` |
| `UniqueSpec(columns, name=?)` | UNIQUE | `TableConstraint(UNIQUE)` |
| `NotNullSpec(column, name=?)` | NOT NULL | `ColumnConstraint(NOT_NULL)` |
| `PrimaryKeySpec(columns, name=?)` | 主键（单列→列级，复合→表级） | PK 约束 |
| `DefaultSpec(column, value)` | 字面量默认值（惰性值 `(dialect) -> Any` 可用）；表达式默认（如 `nextval`）归后端特定 Spec | `ColumnConstraint(DEFAULT)` |
| `ForeignKeySpec(local_columns, ref_table, ref_columns, on_delete=?, on_update=?)` | 外键 | `ForeignKeyConstraint` |
| `IndexSpec(columns, name=?, unique=?, partial_condition=?)` | 索引；部分索引受 `supports_partial_index` 门控 | `IndexDefinition` |
| `PartialIndexSpec(columns, condition, ...)` | 部分索引便捷形态 | `IndexDefinition` |
| `JsonColumnSpec(column)` | JSON 列（便携 `JsonType`：MySQL→JSON、PG→JSON、SQLite→TEXT） | 列类型补丁 |
| `GeneratedColumnSpec(column, expression, stored=?)` | 生成列（受 `supports_generated_columns` 门控） | `ColumnDefinition.generated_*` |

### 惰性谓词工厂

CHECK / 部分索引的条件可以是 `(dialect) -> SQLPredicate` 工厂——**定义时无方言，
生成时由框架注入当前方言**，这是声明与构造解耦的关键：

```python
CheckSpec(condition=lambda d: Column(d, "type").in_(["asset", "liability"]))
#                    ^^^ d 由 generate_create_table(dialect) 注入
```

字段注解同样支持：`UseConstraint(..., check_condition=lambda d: ...)`、
`UseIndex(..., partial_condition=lambda d: ...)`。

### 声明槽位可互换

`__table_constraints__` 与 `__table_indexes__` 对 Spec 是平权槽位——生成器按
**产物类型**路由（索引产物进 `indexes`，约束产物进 `table_constraints`），声明位置
只影响可读性。建议仍按语义选择槽位：索引写 `__table_indexes__`，约束写
`__table_constraints__`。

## SQLite 实例：推导全流程

综合运用字段注解、表级 Spec、能力 Spec 的完整示例：

```python
from typing import Annotated
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import (
    UseSqlType, UseConstraint, UseIndex, ColumnConstraintType,
    UniqueSpec, CheckSpec, PartialIndexSpec, JsonColumnSpec,
)
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

class Article(ActiveRecord):
    __table_name__ = "articles"

    # 字段级：类型与单列约束
    slug: Annotated[str, UseSqlType(VarCharType(length=160))]
    status: Annotated[str, UseConstraint(
        ColumnConstraintType.CHECK,
        check_condition=lambda d: Column(d, "status").in_(["draft", "published"]),
    )]
    is_active: Annotated[int, UseIndex(
        "ix_articles_active",
        partial_condition=lambda d: Column(d, "is_active") == 1,
    )] = 1

    author_id: int
    title: str
    views: int = 0
    likes: int = 0
    meta: object = None
    published_at: str = ""

    # 表级：复合约束、跨列 CHECK、能力 Spec
    __table_constraints__ = [
        UniqueSpec(columns=["author_id", "slug"], name="uq_author_slug"),
        CheckSpec(
            condition=lambda d: Column(d, "views") >= Column(d, "likes"),
            name="ck_views_likes",
        ),
        JsonColumnSpec("meta"),     # SQLite 无原生 JSON → TEXT
        PartialIndexSpec(           # 部分索引（SQLite 3.8+）
            columns=["published_at"],
            condition=lambda d: Column(d, "status") == "published",
            name="ix_articles_published",
        ),
    ]

d = SQLiteDialect()
expr = Article.generate_create_table(d)
sql, params = expr.to_sql()
# sql: 'CREATE TABLE "articles" ("slug" TEXT NOT NULL, "status" TEXT
#        CHECK ("status" IN (?, ?)) NOT NULL, "is_active" INTEGER,
#        "author_id" INTEGER NOT NULL, "title" TEXT NOT NULL, "views" INTEGER,
#        "likes" INTEGER, "meta" TEXT, "published_at" TEXT,
#        CONSTRAINT "uq_author_slug" UNIQUE ("author_id", "slug"),
#        CONSTRAINT "ck_views_likes" CHECK ("views" >= "likes"))'
# params: ('draft', 'published')
```

索引产物在 `expr.indexes`，逐条转 `CreateIndexExpression` 执行：

```python
for ix in expr.indexes:
    ix.to_create_index_expression(d, expr.table).to_sql()
# ('CREATE INDEX "ix_articles_active" ON "articles" ("is_active") WHERE "is_active" = ?', (1,))
# ('CREATE INDEX "ix_articles_published" ON "articles" ("published_at") WHERE "status" = ?', ('published',))
```

观察 SQLite 方言的认领行为：

- `CheckSpec` 惰性工厂在生成时求值，谓词参数化（`IN (?, ?)`，值进 params）；
- `JsonColumnSpec` → `TEXT`（SQLite 无原生 JSON 存储类型，JSON1 函数可用）；
- 两个部分索引正常认领（`supports_partial_index` 版本门控 3.8+）；
- 若声明了任何分区 Spec，SQLite 一律忽略，建普通表。

## 分区声明

分区由各后端定义 `PartitionSpec` 子类，声明在模型级 `__table_partition__` 列表。
**同一模型跨后端，各取所需**：

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.postgres.ddl_spec import PostgresRangePartition
from rhosocial.activerecord.backend.impl.mysql.ddl_spec import (
    MySQLRangePartition, MySQLPartitionDefinitionSpec, MySQLPartitionBound,
)

class Events(ActiveRecord):
    __table_name__ = "events"
    __table_partition__ = [
        PostgresRangePartition(column="created_at"),
        MySQLRangePartition("created_at", [
            MySQLPartitionDefinitionSpec("p2026", less_than=[MySQLPartitionBound(2027)]),
        ]),
    ]
    created_at: str
```

| 后端 | 结果 |
|------|------|
| PostgreSQL | 认领 `PostgresRangePartition` → `PARTITION BY RANGE ("created_at")` |
| MySQL | 认领 `MySQLRangePartition` → `PARTITION BY RANGE (...) (PARTITION ...)` |
| SQLite / 其他 | 两者均不认领 → 建普通表 |

## 执行推导产物

推导产物与手工构造的表达式同型，执行方式一致：

```python
# 方式一：整表 + 索引一起执行
backend.execute(expr)
for ix in expr.indexes:
    backend.execute(ix.to_create_index_expression(dialect, expr.table))

# 方式二：取 SQL 自行执行
sql, params = expr.to_sql()
```

### 与迁移的衔接

两个推导产物可直接 diff，生成 ALTER 集合或 rebuild 计划：

```python
plan = dialect.diff_create_table(old_expr, new_expr)
# plan.alters: list[AlterTableExpression]  或  plan.rebuild: RebuildPlan
```

等价规则与降级策略（如 SQLite 改列类型走 rebuild）由各后端覆写；分区结构变更
一律判 rebuild（无后端可 ALTER 分区键）。收敛不变量
`apply(create_v1) + alters... ≡ generate_create_table()` 可作为 CI 校验。

## 后端 DDL 特征支持与文档索引

各后端为推导 DDL 实现自己的 `build_spec`——认领通用 Spec、提供特定 Spec
（分区、序列默认、原生类型列）。**具体后端支持哪些 Spec、如何处理，以该后端
文档为准**：

| 后端 | 特定 Spec 亮点 | 后端文档 |
|------|----------------|----------|
| SQLite（内置） | 部分/函数索引、生成列、JSON→TEXT、不支持分区（忽略） | `backend/sqlite/ddl/` |
| MySQL | RANGE/LIST/HASH 分区、VECTOR、空间列、SET | python-activerecord-mysql `backend_specific_features/` |
| PostgreSQL | 声明式分区、`PostgresSequenceDefault`、JSONB/HSTORE/数组/网络/TSVECTOR 列 | python-activerecord-postgres `backend_specific_features/` |
| Oracle | RANGE/LIST/HASH/INTERVAL 分区、`OracleSequenceDefault`（`seq.NEXTVAL`） | python-activerecord-oracle `backend_specific_features/` |
| SQL Server | RANGE 分区（分区方案 + LEFT/RIGHT 边界） | python-activerecord-sqlserver `backend_specific_features/` |
| Snowflake | 外部表分区、VARIANT/ARRAY/OBJECT 列 | python-activerecord-snowflake |
| MariaDB / Firebird / ClickHouse | 通用 Spec 全量可用（分区现状见各后端文档） | 各后端仓库 |

## 设计要点回顾

1. **声明时无方言**：Spec 是普通对象，模型 import 时即可构造；
2. **构造时方言注入**：惰性工厂 `(dialect) -> ...` 在 `generate_create_table`
   时求值，谓词参数化安全；
3. **后端自决接受范围**：`build_spec` 一个方法同时承担"认领"与"翻译"，
   未认领返回 `None` 静默忽略；
4. **产物同型**：`build_spec` 只产出既有表达式对象——渲染、执行、diff 链路
   全部复用；
5. **不出现 Raw SQL**：框架 Spec 层绝不构造 `RawSQLExpression`；表达式缺口
   （PG `nextval`、Oracle INTERVAL 函数）通过补充专用表达式类与 formatter 解决。
