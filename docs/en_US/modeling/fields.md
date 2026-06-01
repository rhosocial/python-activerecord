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

## Derived Fields

Derived fields are read-only computed fields whose values are dynamically calculated by the database at query time. They are not stored in the database but generated via SQL expressions in the SELECT clause. Derived fields are not tracked by Pydantic and are excluded from dirty field detection.

### Declaration Methods

There are two ways to declare derived fields:

#### Form A: ClassVar Assignment

```python
from typing import ClassVar
from rhosocial.activerecord.base import DerivedField
from rhosocial.activerecord.backend.expression import Column, Literal

class Product(ActiveRecord):
    __table_name__ = "product"
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    # Using ClassVar assignment
    discounted_price: ClassVar[DerivedField] = DerivedField(
        lambda d: Column(d, "price") * Literal(d, 0.9)
    )
    total_value: ClassVar[DerivedField] = DerivedField(
        lambda d: Column(d, "price") * Column(d, "quantity")
    )
```

#### Form B: ClassVar + Annotated

```python
from typing import Annotated, ClassVar
from rhosocial.activerecord.base import DerivedField
from rhosocial.activerecord.backend.expression import Column, Literal

class Product(ActiveRecord):
    __table_name__ = "product"
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    # Using Annotated declaration, can attach type information
    discounted_price: ClassVar[Annotated[float, DerivedField(
        lambda d: Column(d, "price") * Literal(d, 0.9)
    )]]
    total_value: ClassVar[Annotated[float, DerivedField(
        lambda d: Column(d, "price") * Column(d, "quantity")
    )]]
```

### Using FieldProxy for Expressions (Recommended)

Combining with `FieldProxy` provides type-safe column references, avoiding manual column name spelling:

```python
from typing import ClassVar
from rhosocial.activerecord.base import DerivedField, FieldProxy
from rhosocial.activerecord.backend.expression import Literal

class Product(ActiveRecord):
    __table_name__ = "product"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    discounted_price: ClassVar[Annotated[float, DerivedField(
        lambda d: Product.c.price * Literal(d, 0.9)
    )]]
    total_value: ClassVar[Annotated[float, DerivedField(
        lambda d: Product.c.price * Product.c.quantity
    )]]
```

### Using UseColumn for Custom Column Aliases

With `UseColumn`, you can specify SQL aliases for derived fields without affecting Python property names:

```python
from typing import Annotated, ClassVar
from rhosocial.activerecord.base import DerivedField, UseColumn
from rhosocial.activerecord.backend.expression import Column, Literal

class Product(ActiveRecord):
    __table_name__ = "product"
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    # SQL alias is "disc", Python property name is "discounted_price"
    discounted_price: ClassVar[Annotated[float, DerivedField(
        lambda d: Column(d, "price") * Literal(d, 0.9)
    ), UseColumn("disc")]]
```

### Using UseAdapter for Type Adaptation

`UseAdapter` can convert database-returned values to Python types:

```python
from typing import Annotated, Any, ClassVar, Dict, Optional, Set, Type
from rhosocial.activerecord.base import DerivedField, UseAdapter
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.expression import Column, Literal

class PriceToIntAdapter:
    """Rounds float price to integer"""
    def to_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        return float(value)
    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        return int(round(value))
    @property
    def supported_types(self) -> Dict[Type, Set[Type]]:
        return {int: {float}}

class Product(ActiveRecord):
    __table_name__ = "product"
    id: Optional[int] = None
    name: str
    price: float
    quantity: int

    # Result will be rounded to integer
    total_int: ClassVar[Annotated[int, DerivedField(
        lambda d: Column(d, "price") * Column(d, "quantity")
    ), UseAdapter(PriceToIntAdapter(), int)]]
```

### Using Derived Fields in Queries

Derived fields are optional and must be explicitly requested via the `derived` parameter:

```python
# Get all products with derived fields included
products = Product.find_all(derived=True)  # Include all derived fields

# Include only specific derived fields
products = Product.find_all(derived=["discounted_price", "total_value"])

# Use dictionary for custom aliases
products = Product.find_all(derived={"discount": Product.c.price * Literal(0.9)})

# Single record
product = Product.find_one(1, derived=True)

# Combine with other query conditions
products = Product.find_all(
    Product.c.price > 10,
    derived=["discounted_price"]
)
```

### Important Notes

1. **Read-Only**: Derived field values can only be read, not modified.
2. **No Validation**: Derived fields are not validated by Pydantic as they are ClassVars.
3. **No Change Tracking**: Derived fields are not included in dirty field tracking.
4. **Column Name Conflicts**: The `UseColumn` alias of a derived field cannot conflict with regular field column names.
5. **Performance**: Derived fields are calculated at query time; complex expressions may impact query performance.
