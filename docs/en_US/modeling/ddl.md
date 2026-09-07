# Deriving DDL

`rhosocial-activerecord` can **derive** DDL from model declarations: the model is
the single source of truth for the schema, and
`Model.generate_create_table(dialect)` produces a `CreateTableExpression` that
can be executed, inspected, or fed into expression-level diff for migrations.
This chapter covers the derivation pipeline — the declaration layer (Specs),
the dialect-claiming protocol (`build_spec`), default derivation rules, and
backend capability differences.

> All examples below use SQLite (the core built-in backend) and show **real
> generated output**. For the expression layer itself
> (`CreateTableExpression` / `ColumnDefinition` etc.), see the
> [backend expression docs](../backend/expression/statements.md). For
> backend-specific Specs, see [Backend DDL feature support](#backend-ddl-feature-support-and-doc-index).

## Why derive DDL from the model

Traditionally a table has two independent descriptions: model fields (driving
reads/writes) and a hand-written CREATE TABLE (driving DDL). They drift: adding
a field means editing both, and missing either silently produces a model that
reads/writes a column the table does not have.

Deriving DDL makes the model the **single source of truth**:

- Adding or changing a field is a single edit;
- The schema and the read/write path stay consistent by construction;
- Derived products are the same expression types as hand-built ones — render,
  execute, and diff pipelines are fully reused.

## Quick start: zero-declaration derivation

**The simplest definition is the default path** — a model needs no DDL
declaration at all:

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

class Account(ActiveRecord):
    __table_name__ = "accounts"

    code: str
    type: str
    amount: float
    is_active: bool = True   # has a default -> nullable column

expr = Account.generate_create_table(SQLiteDialect())
sql, params = expr.to_sql()
# sql: 'CREATE TABLE "accounts" ("code" TEXT NOT NULL, "type" TEXT NOT NULL,
#        "amount" REAL NOT NULL, "is_active" NUMERIC)'
# params: ()
```

Default derivation rules:

| Rule | Description |
|------|-------------|
| Column name = field name | Override with `UseColumn("col_name")` |
| Column type = dialect suggestion | Python type mapped via `dialect.suggest_column_type()` (SQLite: `str`→TEXT, `int`→INTEGER, `float`→REAL) |
| Required fields get `NOT NULL` | `Optional[T]` or defaulted fields stay nullable |
| Primary key | Per `primary_key_columns()`; integer auto PK renders `AUTOINCREMENT` (SQLite) / `IDENTITY` etc. |
| Composite primary key | Multi-column PK renders as table-level `PRIMARY KEY (col1, col2)` |

## Declaring DDL features (Specs)

When you need to deviate from the defaults, declare features as **Specs**.
A Spec is a pure declaration object: **no dialect/backend is needed** at
definition time — it is constructed when the model body executes.

### Dialect claiming (build_spec)

At generation time the dialect calls `build_spec(spec)` for each Spec:

- **Accepted** → returns a built expression-layer instance (`TableConstraint` /
  `IndexDefinition` / `ColumnConstraint` / `PartitionClause` …);
- **Not accepted** → returns `None`, and the Spec is **silently ignored**.

Three key principles:

1. **Support is the backend's decision.** A generic Spec is only a "standard
   semantics + core default translation" starting point; backends may override
   the translation or reject it. For unsupported Specs, tests simply assert
   "not supported".
2. **Unclaimed never raises.** Declaration lists are flat and equal: each
   backend claims its own. A backend that considers ignoring unsafe may raise
   inside `build_spec`. Users do not set `required`/`suggested` flags.
3. **Zero string keying.** Backend affinity = real class identity
   (`isinstance`); no `dialect.name` string matching — custom/third-party
   backends are first-class.

### Declarations are everything; assembly happens at build time

The declared constants on the model (`__table_constraints__` /
`__table_indexes__` / `__table_partition__` / `__table_options__` plus field
annotations) are the **single source of truth**:

- Class creation only **validates** them (duplicate index names, partition
  Spec types) and derives no stored state;
- Field annotations are read directly from Pydantic's preserved
  `model_fields[name].metadata`;
- `generate_create_table(dialect)` **assembles** the declarations into
  expressions on the fly — there is no second collected copy, hence no
  possibility of "stash drifts from declaration".

Removing an intermediate representation buys a single source of truth and a
smaller namespace.

### Two-level entry points

Declarations split by ownership: field-owned content is written on the field,
table-level/composite content goes to table-level slots. Both paths unify
underneath — field annotations are folded into column-level Specs and claimed
by the same `build_spec` call; the dialect never distinguishes the source.

**Field-level annotations** (column type, single-column constraint/index):

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
        check_condition=lambda d: Column(d, "age") >= 18,   # lazy predicate factory
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

Single-column indexes execute as separate statements (see
[Executing derived products](#executing-derived-products)):

```python
expr.indexes[0].to_create_index_expression(SQLiteDialect(), expr.table).to_sql()
# ('CREATE INDEX "ix_users_active" ON "users" ("is_active") WHERE "is_active" = ?', (1,))
```

**Table-level declaration lists** (composite constraints, cross-column CHECK,
partitions):

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

### Generic Specs

| Spec | Purpose | Default translation |
|------|---------|---------------------|
| `CheckSpec(condition, name=?)` | CHECK; `condition` may be a ready predicate or a lazy `(dialect) -> SQLPredicate` factory | `TableConstraint(CHECK)` |
| `UniqueSpec(columns, name=?)` | UNIQUE | `TableConstraint(UNIQUE)` |
| `NotNullSpec(column, name=?)` | NOT NULL | `ColumnConstraint(NOT_NULL)` |
| `PrimaryKeySpec(columns, name=?)` | Primary key (single → column-level, composite → table-level) | PK constraint |
| `DefaultSpec(column, value)` | Literal default (lazy `(dialect) -> Any` accepted); expression defaults (e.g. `nextval`) belong to backend-specific Specs | `ColumnConstraint(DEFAULT)` |
| `ForeignKeySpec(local_columns, ref_table, ref_columns, on_delete=?, on_update=?)` | Foreign key | `ForeignKeyConstraint` |
| `IndexSpec(columns, name=?, unique=?, partial_condition=?)` | Index; partial gated by `supports_partial_index` | `IndexDefinition` |
| `PartialIndexSpec(columns, condition, ...)` | Partial-index shorthand | `IndexDefinition` |
| `JsonColumnSpec(column)` | JSON column (portable `JsonType`, rendered as TEXT on SQLite) | column type patch |
| `GeneratedColumnSpec(column, expression, stored=?)` | Generated column (gated by `supports_generated_columns`) | `ColumnDefinition.generated_*` |

### Lazy predicate factories

CHECK / partial-index conditions may be `(dialect) -> SQLPredicate` factories —
**no dialect at definition time; the framework injects the current dialect at
generation time**. This is the decoupling point between declaration and
construction:

```python
CheckSpec(condition=lambda d: Column(d, "type").in_(["asset", "liability"]))
#                    ^^^ d is injected by generate_create_table(dialect)
```

Field annotations support factories too: `UseConstraint(..., check_condition=lambda d: ...)`,
`UseIndex(..., partial_condition=lambda d: ...)`.

### Declaration slots are interchangeable

`__table_constraints__` and `__table_indexes__` are equal slots for Specs —
the generator routes **by product kind** (index products go to `indexes`,
constraint products to `table_constraints`); declaration position only affects
readability. Still, choose semantically: indexes in `__table_indexes__`,
constraints in `__table_constraints__`.

## A full SQLite derivation

A complete example combining field annotations, table-level Specs, and
capability Specs:

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

    # Field-level: type and single-column constraint
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

    # Table-level: composite constraint, cross-column CHECK, capability Specs
    __table_constraints__ = [
        UniqueSpec(columns=["author_id", "slug"], name="uq_author_slug"),
        CheckSpec(
            condition=lambda d: Column(d, "views") >= Column(d, "likes"),
            name="ck_views_likes",
        ),
        JsonColumnSpec("meta"),     # SQLite has no native JSON -> TEXT
        PartialIndexSpec(           # partial index (SQLite 3.8+)
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

Index products live in `expr.indexes`, converted per-item to
`CreateIndexExpression` for execution:

```python
for ix in expr.indexes:
    ix.to_create_index_expression(d, expr.table).to_sql()
# ('CREATE INDEX "ix_articles_active" ON "articles" ("is_active") WHERE "is_active" = ?', (1,))
# ('CREATE INDEX "ix_articles_published" ON "articles" ("published_at") WHERE "status" = ?', ('published',))
```

Observed SQLite dialect behavior:

- `CheckSpec` lazy factories evaluate at generation time; predicates are
  parameterized (`IN (?, ?)`, values in params);
- `JsonColumnSpec` → `TEXT` (SQLite has no native JSON storage type; JSON1
  functions are available);
- Both partial indexes are claimed (`supports_partial_index`, version-gated 3.8+);
- Any partition Spec would be ignored — SQLite builds a plain table.

## Declaring partitions

Partitions are declared through `PartitionSpec` subclasses defined by specific
backends, in the model-level `__table_partition__` list. Partitioning is a
dialect capability: **SQLite does not support partitions — any partition Spec
is ignored and a plain table is built**; partition-capable backends (and their
Spec classes / declaration forms) are documented by those backends.

```python
from rhosocial.activerecord.model import ActiveRecord

class Events(ActiveRecord):
    __table_name__ = "events"
    __table_partition__ = [
        # Backend partition Specs (e.g. PostgresRangePartition /
        # MySQLRangePartition) are declared here; SQLite ignores them all
    ]
    created_at: str

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

sql, _ = Events.generate_create_table(SQLiteDialect()).to_sql()
# sql: 'CREATE TABLE "events" ("created_at" TEXT NOT NULL)'   <- no partition clause
```

The declaration form is always safe for SQLite: derivation neither fails nor
behaves unpredictably, and the same model can be reused directly on
partition-capable backends.

## Executing derived products

Derived products are the same expression types as hand-built ones:

```python
# Option A: execute the table, then each index
backend.execute(expr)
for ix in expr.indexes:
    backend.execute(ix.to_create_index_expression(dialect, expr.table))

# Option B: take the SQL and execute it yourself
sql, params = expr.to_sql()
```

### Connection to migrations

Two derived products can be diffed directly to produce an ALTER set or a
rebuild plan:

```python
plan = dialect.diff_create_table(old_expr, new_expr)
# plan.alters: list[AlterTableExpression]  or  plan.rebuild: RebuildPlan
```

Equivalence rules and downgrade strategies (e.g. SQLite column-type change →
rebuild) are per-backend overrides; partition structure changes always rebuild
(no backend can ALTER a partition key). The convergence invariant
`apply(create_v1) + alters... ≡ generate_create_table()` works as a CI check.

Each backend implements its own `build_spec` — claiming generic Specs and
providing backend-specific ones (partitions, sequence defaults, native-type
columns). **Which Specs a backend supports, and how it handles them, is
documented by that backend.**
