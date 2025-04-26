# Primary Key Configuration

Primary keys are essential for uniquely identifying records in a database. rhosocial ActiveRecord provides flexible options for configuring primary keys in your models.

## Default Primary Key

By default, ActiveRecord assumes that your model has a primary key field named `id`. This is automatically handled for you, and you don't need to explicitly define it unless you want to customize its behavior.

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    __tablename__ = 'products'
    
    name: str
    price: float
    # 'id' is implicitly used as the primary key
```

## Custom Primary Key Name

If your table uses a different column name for the primary key, you can specify it using the `__primary_key__` class attribute:

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    __tablename__ = 'products'
    __primary_key__ = 'product_id'  # Use 'product_id' as the primary key
    
    product_id: int
    name: str
    price: float
```

## Integer Primary Keys

For tables with integer primary keys, rhosocial ActiveRecord provides the `IntegerPKMixin` to simplify handling:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin

class Product(IntegerPKMixin, ActiveRecord):
    __tablename__ = 'products'
    
    name: str
    price: float
```

The `IntegerPKMixin` automatically sets the primary key to `None` for new records, allowing the database to assign an auto-incremented value when the record is saved.

## UUID Primary Keys

For applications that require globally unique identifiers, rhosocial ActiveRecord provides the `UUIDMixin` for UUID-based primary keys:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import UUIDMixin

class Product(UUIDMixin, ActiveRecord):
    __tablename__ = 'products'
    
    name: str
    price: float
```

The `UUIDMixin` automatically generates a new UUID for the primary key when creating a new record. This is particularly useful for distributed systems or when you need to generate IDs before inserting records into the database.

## Composite Primary Keys

While not directly supported through a mixin, you can implement composite primary keys by overriding the `primary_key()` method and customizing the query conditions in your model:

```python
from rhosocial.activerecord import ActiveRecord

class OrderItem(ActiveRecord):
    __tablename__ = 'order_items'
    
    order_id: int
    item_id: int
    quantity: int
    price: float
    
    @classmethod
    def primary_key(cls):
        return ['order_id', 'item_id']
    
    # You'll need to override other methods to handle the composite key properly
```

## Finding Records by Primary Key

Regardless of how you configure your primary key, ActiveRecord provides a consistent API for finding records:

```python
# Find by primary key
product = Product.find(1)  # Returns the product with id=1

# Find multiple records by primary keys
products = Product.find_all([1, 2, 3])  # Returns products with ids 1, 2, and 3
```

## Database-Specific Considerations

Different database backends handle primary keys differently:

- **SQLite**: Integer primary keys are automatically auto-incrementing when defined as `INTEGER PRIMARY KEY`
- **MySQL/MariaDB**: Uses `AUTO_INCREMENT` for auto-incrementing primary keys
- **PostgreSQL**: Typically uses `SERIAL` or `BIGSERIAL` types for auto-incrementing keys

rhosocial ActiveRecord handles these differences for you, but it's good to be aware of them when designing your schema.

## Best Practices

1. **Use Integer Primary Keys** for most tables unless you have a specific reason not to
2. **Use UUID Primary Keys** when you need globally unique identifiers or generate IDs before insertion
3. **Be Consistent** with your primary key naming convention across your application
4. **Consider Performance** implications, especially with UUID keys which can impact indexing and join performance

## Next Steps

Now that you understand how to configure primary keys, you might want to explore:

- [Timestamp Fields](timestamp_fields.md) - For automatic creation and update time tracking
- [Relationships](../relationships/README.md) - For defining associations between models