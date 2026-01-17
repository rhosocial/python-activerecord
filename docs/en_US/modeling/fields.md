# Fields & Proxies

In `rhosocial-activerecord`, field definitions reuse Pydantic syntax while introducing `FieldProxy` to bridge the gap between Python objects and SQL queries.

## Basic Field Definition

Model fields are standard Python type annotations, and you can use `pydantic.Field` to add metadata and validation rules.

```python
from typing import Optional
from pydantic import Field
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    name: str = Field(..., max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = None
    is_active: bool = True
    
    @classmethod
    def table_name(cls) -> str:
        return "products"
```

## FieldProxy: Type-Safe Querying

Traditional ORMs often rely on strings to reference fields (e.g., `filter(name="Alice")`), which leads to typos and makes refactoring difficult.
`FieldProxy` allows you to build queries using Python expressions.

### Enabling FieldProxy

Define a `ClassVar` in your model:

```python
from typing import ClassVar
from rhosocial.activerecord import FieldProxy

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
Product.find_where(Product.c.price > 100)

# Combination (AND/OR)
User.find_where((User.c.age >= 18) & (User.c.is_active == True))

# IN Query
User.find_where(User.c.status.in_(['active', 'pending']))

# LIKE Query
User.find_where(User.c.username.like("admin%"))
```

> **Tip**: IDEs will autocomplete field names after `User.c` (although it's a dynamic proxy, type hints can support this). Currently dynamic, future versions may provide static generation tools for better IDE support.

## Mapping Legacy Columns

Sometimes database column names don't follow Python naming conventions (e.g., spaces, special characters, or CamelCase), or you simply want to use a different property name in Python.
Use `UseColumn` to handle this easily.

```python
from typing import Annotated, Optional
from rhosocial.activerecord import UseColumn

class LegacyUser(ActiveRecord):
    # DB column is "USER-NAME", Python property is "username"
    username: Annotated[str, UseColumn("USER-NAME")]
    
    # DB column is "db_id", Python property is "id"
    id: Annotated[str, UseColumn("db_id")]
```

`rhosocial-activerecord` automatically handles the conversion between property names and column names during query generation and result mapping.
