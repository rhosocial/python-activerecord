# Custom Type Adapters

## Overview

Type adapters convert between Python objects and database values. When the built-in adapters don't cover your needs, you can create custom adapters for specialized data types.

## The Adapter Protocol

Type adapters implement the `SQLTypeAdapter` protocol from `rhosocial.activerecord.backend.type_adapter`:

```python
@runtime_checkable
class SQLTypeAdapter(Protocol):
    def to_database(self, value, target_type, options=None) -> Any: ...
    def from_database(self, value, target_type, options=None) -> Any: ...

    @property
    def supported_types(self) -> Dict[Type, Set[Type]]: ...
```

## Creating a Custom Adapter

Extend `BaseSQLTypeAdapter` for convenience:

```python
from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter


class Color:
    """A simple RGB color class."""
    def __init__(self, r: int, g: int, b: int):
        self.r = r
        self.g = g
        self.b = b

    @classmethod
    def from_hex(cls, hex_str: str) -> 'Color':
        hex_str = hex_str.lstrip('#')
        return cls(
            int(hex_str[0:2], 16),
            int(hex_str[2:4], 16),
            int(hex_str[4:6], 16),
        )

    def to_hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


class ColorAdapter(BaseSQLTypeAdapter):
    """Converts between Python Color objects and database hex strings."""

    def __init__(self):
        super().__init__()
        # Register: {python_type: {db_types}}
        self._register_type(Color, str)

    def _do_to_database(self, value, target_type, options):
        """Convert Color -> hex string for database storage."""
        if isinstance(value, Color):
            return value.to_hex()
        raise TypeError(f"Cannot convert {type(value).__name__} to Color")

    def _do_from_database(self, value, target_type, options):
        """Convert hex string from database -> Color."""
        if isinstance(value, str):
            return Color.from_hex(value)
        raise TypeError(f"Cannot convert {type(value).__name__} from database")
```

## Registering the Adapter

Register your adapter with the backend's type registry:

```python
from rhosocial.activerecord.backend.type_registry import TypeRegistry

# Create registry (or use the backend's existing registry)
registry = TypeRegistry()

# Register: adapter, python_type, db_type
registry.register(ColorAdapter(), Color, str, allow_override=False)
```

Or register via the backend's `_register_default_adapters()` method:

```python
class MyBackend(MySQLBackend):
    def _register_default_adapters(self):
        super()._register_default_adapters()
        self._type_registry.register(
            ColorAdapter(), Color, str, allow_override=False
        )
```

## Using Custom Adapters in Models

Once registered, the adapter is used automatically when you declare a field with your custom type:

```python
class Product(ActiveRecord):
    name: str
    color: Color  # Automatically uses ColorAdapter

    @classmethod
    def table_name(cls) -> str:
        return 'products'

# The adapter handles conversion transparently
product = Product(name='Widget', color=Color(255, 0, 0))
product.save()  # Color is converted to '#ff0000' for storage

loaded = Product.find_one(product.id)
print(loaded.color)  # Color(255, 0, 0) — converted back from '#ff0000'
```

## Adapter Options

Adapters can accept options for configuration:

```python
class JsonAdapter(BaseSQLTypeAdapter):
    def _do_to_database(self, value, target_type, options):
        indent = options.get('indent', None) if options else None
        return json.dumps(value, indent=indent)

    def _do_from_database(self, value, target_type, options):
        return json.loads(value)
```

## See Also

- [Type Adapters](../type_adapters/README.md) — type conversion system
- [Custom Data Types](custom_types.md) — defining new DataType subclasses
- [Type Mapping](../type_adapters/mapping.md) — built-in type mappings
- [Custom Adapters](../type_adapters/custom.md) — more adapter examples

💡 *AI Prompt:* "How do I store a Python object in a database column with custom serialization?"
