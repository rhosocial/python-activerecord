# Fields & Proxies

In `rhosocial-activerecord`, field definitions reuse Pydantic syntax while introducing `FieldProxy` to bridge the gap between Python objects and SQL queries.

## Basic Field Definition

Model fields are standard Python type annotations, and you can use `pydantic.Field` to add metadata and validation rules.

> **Note**: By default, class attribute names correspond directly to database table column names and are **case-sensitive**. If they do not match, please refer to the next section "Mapping Legacy Columns".

```python
from typing import Optional
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord

class Product(ActiveRecord):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    is_active: bool = True
    
    @classmethod
    def table_name(cls) -> str:
        return "products"
```

## Mapping Legacy Columns

**What if the database column name is not a valid Python attribute name?**

Sometimes database column names don't follow Python naming conventions (e.g., spaces, special characters, or CamelCase), or you simply want to use a different property name in Python.
Use `UseColumn` to handle this easily.

```python
from typing import Annotated, Optional
from rhosocial.activerecord.base import UseColumn

class LegacyUser(ActiveRecord):
    # DB column is "USER-NAME", Python property is "username"
    username: Annotated[str, UseColumn("USER-NAME")]
    
    # DB column is "db_id", Python property is "id"
    id: Annotated[str, UseColumn("db_id")]
```

`rhosocial-activerecord` automatically handles the conversion between property names and column names during query generation and result mapping.

## Specifying SQL Column Types (UseSqlType)

By default, `ActiveRecord` **auto-infers** the database column type from the Python field type (`str` → text, `int` → integer, `bool` → boolean, etc.). When auto-inference is not sufficient — e.g. you need an exact `VARCHAR(100)`, `DECIMAL(10,2)`, `JSONB`, or you want explicit control over the column type — use the `UseSqlType` annotation to **explicitly specify the SQL data type**.

`UseSqlType` accepts one or more `DataType` instances:

```python
from typing import Annotated, Optional
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import (
    VarCharType, DecimalType, JsonType, DateTimeType, IntegerType,
)

class User(ActiveRecord):
    __table_name__ = "users"

    # Explicitly VARCHAR(100), instead of the default TEXT
    username: Annotated[str, UseSqlType(VarCharType(length=100))]

    # Explicit exact decimal DECIMAL(10,2)
    balance: Annotated[Optional[float], UseSqlType(DecimalType(precision=10, scale=2))]

    # Structured JSON
    metadata: Annotated[Optional[dict], UseSqlType(JsonType())]

    # Date and time
    created_at: Annotated[str, UseSqlType(DateTimeType())]

    # 32-bit auto-increment primary key
    id: Annotated[int, UseSqlType(IntegerType())]
```

### Generic Types vs. Backend-Specific Types

`DataType` comes in two flavors, both accepted by `UseSqlType`:

- **Generic types** (e.g. `VarCharType`, `IntegerType`, `TextType`, `JsonType`): portable across backends — every backend renders them as its own native SQL (e.g. SQLite renders `VARCHAR(100)` as `TEXT`, MySQL as `VARCHAR(100)`).
- **Backend-specific types** (e.g. `PostgresJsonBType`, `MySQLEnumType`, named with the backend name as prefix): render only on the backend that registers them; other backends **skip** that type (rather than silently substituting a lossy form).

### Declaration Order = Backend Priority

`UseSqlType` can declare **multiple** types at once. At DDL generation time, the framework picks the **first** type the current dialect can render; if none matches, it falls back to the backend-neutral auto-inference, and raises if that yields nothing either.

```python
from typing import Annotated
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import JsonType
# Backend-specific types below (from the corresponding backend packages)
from rhosocial.activerecord.backend.impl.postgres.expression.types import PostgresJsonBType
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLLongTextType

# Priority: JSONB on PostgreSQL, LONGTEXT on MySQL < 5.7 (where JSON is unavailable), generic JSON elsewhere
payload: Annotated[dict, UseSqlType(
    PostgresJsonBType(), JsonType(), MySQLLongTextType(),
)]
```

This lets **one model** deploy across multiple backends, each automatically choosing the most appropriate column type.

> **Relationship with `UseColumn`**: `UseColumn` controls the **column name** (Python attribute ↔ database column); `UseSqlType` controls the **column type** (SQL data type). They do not conflict and can be used together.
>
> For the full data-type system (lifecycle, value-object semantics, generic/backend-specific cooperation), see [Data Types](../backend/expression/types.md).

## FieldProxy: Type-Safe Querying

Traditional ORMs often rely on strings to reference fields (e.g., `filter(name="Alice")`), which leads to typos and makes refactoring difficult.
`FieldProxy` allows you to build queries using Python expressions.

### Enabling FieldProxy

Define a `ClassVar` in your model:

```python
from typing import ClassVar
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    username: str
    age: int
    
    # Conventionally named 'c' (column) or 'f' (field)
    c: ClassVar[FieldProxy] = FieldProxy()
```

### Using FieldProxy

Now you can use `User.c.field_name` to build expressions:

```python
# Equality
User.find_one(User.c.username == "alice")

# Comparison
Product.find_all(Product.c.price > 100)

# Combination (AND/OR)
User.find_all((User.c.age >= 18) & (User.c.is_active == True))

# IN Query
User.find_all(User.c.status.in_(['active', 'pending']))

# LIKE Query
User.find_all(User.c.username.like("admin%"))
```

> **Tip**: IDEs will autocomplete field names after `User.c` (although it's a dynamic proxy, type hints can support this). Currently dynamic, future versions may provide static generation tools for better IDE support.

> **FieldProxy Benefits**: When a field has a custom database column name defined (using `UseColumn`), FieldProxy automatically uses the custom column name. For example, if you define `username: Annotated[str, UseColumn("USER-NAME")]`, then `User.c.username` will automatically reference the `"USER-NAME"` column in the database, without requiring you to manually handle this mapping.

### Design Philosophy: Why Manual Definition?

You may notice that `FieldProxy` is not present by default and requires users to manually define it as a `ClassVar`. This is a deliberate design choice based on two main reasons:

1.  **Avoid Naming Conflicts**
    ActiveRecord models contain numerous methods and attributes (e.g., `save`, `delete`, `query`, `table_name`). If the ORM automatically injected an attribute like `c` or `fields` into the model, it would very likely conflict with user-defined database column names (e.g., if your table happens to have a column named `c` or `fields`).
    By forcing manual definition, you have full control over the proxy object's name (conventionally `c`, but you can name it `f` or `columns` if conflicts arise), ensuring a clean and safe model namespace.

2.  **Support Table Aliases**
    Another important role of `FieldProxy` is to support complex SQL queries, especially Self-Joins. In a self-join, we need to reference the same table multiple times with different aliases. By instantiating `FieldProxy` with an alias, we can easily build such queries.

    **Example: Employees and Managers (Self-Join)**

    Suppose we have a `User` model where `manager_id` points to the `id` of the same table.

    ```python
    class User(ActiveRecord):
        id: int
        name: str
        manager_id: Optional[int]
        
        # Default proxy (points to 'users' table)
        c: ClassVar[FieldProxy] = FieldProxy()

    # Create a proxy with 'managers' alias
    ManagerAlias = User.c.with_table_alias("managers")

    # Query all users and their manager's name
    # SELECT users.name, managers.name as manager_name 
    # FROM users 
    # JOIN users AS managers ON users.manager_id = managers.id
    query = User.query() \
        .join(User, on=(User.c.manager_id == ManagerAlias.id), alias="managers") \
        .select(User.c.name, ManagerAlias.name.as_("manager_name")) \
        .all()
    ```

### Multiple FieldProxies: Independent Proxies for Different Table Aliases

`FieldProxy` itself is a **field** (`ClassVar`), so like any field, **you can define as many as you want** — `c`, `c1`, `c2`, `c_mgr`, `c_sub`... You can give each proxy a **different table alias**, so they point to different instances of the same table.

This is especially useful in **joins, and above all Self-Joins**: instead of calling `with_table_alias()` dynamically on every query, you declare the aliased proxies as part of the model definition and reuse them.

#### Pre-binding a Table Alias via the Constructor

The `FieldProxy` constructor accepts a `table_alias` argument, binding the alias at definition time:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord.base import FieldProxy

class Employee(ActiveRecord):
    __table_name__ = "employees"
    id: int
    name: str
    manager_id: Optional[int]  # points to the same table's id

    # Default proxy: points to the 'employees' table itself
    c: ClassVar[FieldProxy] = FieldProxy()

    # Second proxy: pre-bound to the 'managers' table alias
    c_mgr: ClassVar[FieldProxy] = FieldProxy(table_alias="managers")

    # Third proxy: pre-bound to the 'subordinates' table alias
    c_sub: ClassVar[FieldProxy] = FieldProxy(table_alias="subordinates")
```

#### Self-Join: Query Employees and Their Managers

```python
# Self-join on the employees table: JOIN employees AS managers
# c_mgr automatically generates "managers"."name" and similar references
query = Employee.query() \
    .join(Employee, on=(Employee.c.manager_id == Employee.c_mgr.id), alias="managers") \
    .select(Employee.c.name.as_("emp"), Employee.c_mgr.name.as_("manager"))

sql, params = query.to_sql()
# SELECT "employees"."name" AS "emp", "managers"."name" AS "manager"
# FROM "employees"
# JOIN "employees" AS "managers" ON "employees"."manager_id" = "managers"."id"

rows = query.all()  # emp + manager name for each employee
```

#### Deeper Self-Join: Employee → Manager → Grand Manager

With multiple aliased proxies, you can cascade multi-level self-joins easily:

```python
query = Employee.query() \
    .join(Employee, on=(Employee.c.manager_id == Employee.c_mgr.id), alias="managers") \
    .join(Employee, on=(Employee.c_mgr.manager_id == Employee.c_sub.id), alias="subordinates") \
    .select(
        Employee.c.name.as_("emp"),
        Employee.c_mgr.name.as_("manager"),
        Employee.c_sub.name.as_("grand_manager"),
    )

# SELECT "employees"."name" AS "emp", "managers"."name" AS "manager",
#        "subordinates"."name" AS "grand_manager"
# FROM ("employees" JOIN "employees" AS "managers" ON "employees"."manager_id" = "managers"."id")
# JOIN "employees" AS "subordinates" ON "managers"."manager_id" = "subordinates"."id"
```

#### Using Aliased Proxies in WHERE Conditions

Aliased proxies work anywhere a column reference is needed — not only in `select`, but also in `join`'s `on` and `where`:

```python
# Find all direct subordinates whose manager is named Alice
query = Employee.query() \
    .join(Employee, on=(Employee.c.manager_id == Employee.c_mgr.id), alias="managers") \
    .where(Employee.c_mgr.name == "Alice") \
    .select(Employee.c.name)
```

#### Comparison with `with_table_alias()`

| Approach | Usage | Use case |
|----------|-------|----------|
| `FieldProxy(table_alias="...")` | Pre-bound at definition | Fixed alias, reused often; declared as part of the model |
| `c.with_table_alias("...")` | Created dynamically at use | Temporary, one-off alias |

Both approaches generate **identical SQL**; the pre-bound approach declares "which alias instances this table has" centrally in the model, making self-join semantics obvious at a glance.

## Derived Fields

Derived fields are **read-only computed fields** whose values are dynamically calculated by the database at query time. They are not stored in the database, are not validated by Pydantic, and are excluded from dirty field tracking.

Typical uses: price calculations (discount, tax-inclusive), full-name concatenation, JSON extraction, referencing aggregate results, etc.

For the complete declaration and usage guide, see: [**Derived Fields**](./derived_fields.md).

At query time, derived fields are optional and must be explicitly requested via the `derived` argument:

```python
# Get all products with derived fields included
products = Product.find_all(derived=True)  # includes all derived fields

# Include only specific derived fields
products = Product.find_all(derived=["discounted_price", "total_value"])

# Single record
product = Product.find_one(1, derived=True)

# Combine with other query conditions
products = Product.find_all(
    Product.c.price > 10,
    derived=["discounted_price"]
)
```
