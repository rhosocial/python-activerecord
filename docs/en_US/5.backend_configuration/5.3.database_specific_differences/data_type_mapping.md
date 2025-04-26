# Data Type Mapping

This document explains how rhosocial ActiveRecord maps data types between Python, the unified ActiveRecord type system, and the native types of each supported database system.

## Contents

- [Type System Overview](#type-system-overview)
- [Unified Type System](#unified-type-system)
- [Type Converter System](#type-converter-system)
- [Type Registry](#type-registry)
- [Database-Specific Type Mappings](#database-specific-type-mappings)
  - [SQLite](#sqlite)
  - [MySQL](#mysql)
  - [MariaDB](#mariadb)
  - [PostgreSQL](#postgresql)
  - [Oracle](#oracle)
  - [SQL Server](#sql-server)
- [Custom Type Handling](#custom-type-handling)
- [Type Conversion Considerations](#type-conversion-considerations)
- [Best Practices](#best-practices)

## Type System Overview

rhosocial ActiveRecord uses a three-layer type system:

1. **Python Types**: The native Python types used in your application code (str, int, float, datetime, etc.)
2. **Unified ActiveRecord Types**: A standardized set of types defined in the `DatabaseType` enum that provides a consistent interface across all database backends
3. **Native Database Types**: The actual data types used by each specific database system

This layered approach allows you to write database-agnostic code while still leveraging the specific capabilities of each database system.

## Unified Type System

rhosocial ActiveRecord defines a unified type system through the `DatabaseType` enum in the `typing` module. This enum includes common data types that are mapped to appropriate native types for each database backend:

```python
class DatabaseType(Enum):
    """
    Unified database type definitions across various database systems.

    This enum provides a standard set of database column types that can be
    mapped to specific implementations in each database backend.
    """

    # --- Standard numeric types ---
    TINYINT = auto()  # Small integer (usually 1 byte)
    SMALLINT = auto()  # Small integer (usually 2 bytes)
    INTEGER = auto()  # Standard integer (usually 4 bytes)
    BIGINT = auto()  # Large integer (usually 8 bytes)
    FLOAT = auto()  # Single-precision floating point
    DOUBLE = auto()  # Double-precision floating point
    DECIMAL = auto()  # Fixed-precision decimal number
    NUMERIC = auto()  # Generic numeric type
    REAL = auto()  # Real number type

    # --- Standard string types ---
    CHAR = auto()  # Fixed-length character string
    VARCHAR = auto()  # Variable-length character string with limit
    TEXT = auto()  # Variable-length character string without limit
    TINYTEXT = auto()  # Very small text (max 255 chars)
    MEDIUMTEXT = auto()  # Medium-sized text
    LONGTEXT = auto()  # Large text

    # --- Standard date and time types ---
    DATE = auto()  # Date only (year, month, day)
    TIME = auto()  # Time only (hour, minute, second)
    DATETIME = auto()  # Date and time without timezone
    TIMESTAMP = auto()  # Date and time with timezone
    INTERVAL = auto()  # Time interval

    # --- Standard binary types ---
    BLOB = auto()  # Binary large object
    TINYBLOB = auto()  # Small binary object
    MEDIUMBLOB = auto()  # Medium binary object
    LONGBLOB = auto()  # Large binary object
    BYTEA = auto()  # Binary data

    # --- Standard boolean type ---
    BOOLEAN = auto()  # Boolean (true/false)

    # --- Common extended types ---
    UUID = auto()  # Universally unique identifier

    # --- JSON types ---
    JSON = auto()  # JSON document
    JSONB = auto()  # Binary JSON

    # --- Array types ---
    ARRAY = auto()  # Array of values

    # --- XML type ---
    XML = auto()  # XML document

    # --- Key-value type ---
    HSTORE = auto()  # Key-value store

    # --- Network address types ---
    INET = auto()  # IPv4 or IPv6 host address
    CIDR = auto()  # IPv4 or IPv6 network address
    MACADDR = auto()  # MAC address
    MACADDR8 = auto()  # MAC address (EUI-64 format)

    # --- Geometric types ---
    POINT = auto()  # Point on a plane (x,y)
    LINE = auto()  # Infinite line
    LSEG = auto()  # Line segment
    BOX = auto()  # Rectangular box
    PATH = auto()  # Closed and open paths
    POLYGON = auto()  # Polygon (similar to closed path)
    CIRCLE = auto()  # Circle
    GEOMETRY = auto()  # Generic geometry type
    GEOGRAPHY = auto()  # Geographic data type

    # --- Range types ---
    INT4RANGE = auto()  # Range of integers
    INT8RANGE = auto()  # Range of bigints
    NUMRANGE = auto()  # Range of numerics
    TSRANGE = auto()  # Range of timestamps without time zone
    TSTZRANGE = auto()  # Range of timestamps with time zone
    DATERANGE = auto()  # Range of dates

    # --- Full text search types ---
    TSVECTOR = auto()  # Text search document
    TSQUERY = auto()  # Text search query

    # --- Money type ---
    MONEY = auto()  # Currency amount

    # --- Bit string types ---
    BIT = auto()  # Fixed-length bit string
    VARBIT = auto()  # Variable-length bit string

    # --- Enumeration and set types ---
    ENUM = auto()  # Enumeration of string values
    SET = auto()  # Set of string values

    # --- Large object types ---
    CLOB = auto()  # Character large object
    NCLOB = auto()  # National character large object

    # --- Unicode types ---
    NCHAR = auto()  # Unicode fixed-length character data
    NVARCHAR = auto()  # Unicode variable-length character data
    NTEXT = auto()  # Unicode variable-length character data

    # --- Row identifier types ---
    ROWID = auto()  # Physical row address
    UROWID = auto()  # Universal row id

    # --- Hierarchical type ---
    HIERARCHYID = auto()  # Tree hierarchy position

    # --- Extensible custom type ---
    CUSTOM = auto()  # For database-specific types not covered above
```

## Type Converter System

The Type Converter System is responsible for converting data between Python types and database types. It consists of a collection of converter classes that handle specific type conversions.

### Converter Architecture

The converter system is built around the following components:

1. **BaseTypeConverter**: An abstract base class that defines the interface for all type converters
2. **TypeConverterFactory**: A factory class that creates and manages type converter instances
3. **Specialized Converters**: Concrete implementations for specific type conversions

```python
class BaseTypeConverter(ABC):
    @abstractmethod
    def to_python(self, value, field=None):
        """Convert a database value to a Python object"""
        pass
        
    @abstractmethod
    def to_database(self, value, field=None):
        """Convert a Python object to a database value"""
        pass
```

### Built-in Converters

rhosocial ActiveRecord provides built-in converters for common data types:

| Converter Class | Python Type | Database Type |
|-----------------|-------------|---------------|
| StringConverter | str | VARCHAR, CHAR, TEXT |
| IntegerConverter | int | INTEGER, SMALLINT, BIGINT |
| FloatConverter | float | FLOAT, DOUBLE |
| DecimalConverter | Decimal | DECIMAL |
| BooleanConverter | bool | BOOLEAN |
| DateConverter | date | DATE |
| TimeConverter | time | TIME |
| DateTimeConverter | datetime | DATETIME, TIMESTAMP |
| JsonConverter | dict, list | JSON |
| UuidConverter | UUID | UUID |
| BytesConverter | bytes | BLOB |

## Type Registry

The Type Registry is a central repository that manages the mapping between Python types, ActiveRecord types, and database-specific types. It allows for dynamic registration of custom type converters.

### Registry Architecture

The registry system consists of:

1. **TypeRegistry**: A singleton class that maintains mappings between types
2. **TypeRegistration**: A data class that holds information about a registered type

```python
class TypeRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self._python_to_db_type = {}
        self._db_type_to_converter = {}
        self._register_defaults()
    
    def register(self, python_type, db_type, converter_class):
        """Register a new type mapping"""
        self._python_to_db_type[python_type] = db_type
        self._db_type_to_converter[db_type] = converter_class
    
    def get_db_type(self, python_type):
        """Get the database type for a Python type"""
        return self._python_to_db_type.get(python_type)
    
    def get_converter(self, db_type):
        """Get the converter for a database type"""
        return self._db_type_to_converter.get(db_type)
```

### Custom Type Registration

You can register custom type converters to handle specialized data types:

```python
# Create a custom converter
class PointConverter(BaseTypeConverter):
    def to_python(self, value, field=None):
        if value is None:
            return None
        x, y = value.strip('()').split(',')
        return Point(float(x), float(y))
    
    def to_database(self, value, field=None):
        if value is None:
            return None
        return f'({value.x},{value.y})'

# Register the custom converter
registry = TypeRegistry()
registry.register(Point, DatabaseType.CUSTOM, PointConverter)
```

## Database-Specific Type Mappings

Each database backend defines type mappings that convert the unified `DatabaseType` enum values to appropriate native types for that database system.

### SQLite

| ActiveRecord Type | SQLite Native Type | Notes |
|-------------------|-------------------|-------|
| CHAR              | TEXT              | SQLite doesn't have a fixed-length CHAR type |
| VARCHAR           | TEXT              | SQLite uses a single TEXT type for all strings |
| TEXT              | TEXT              | |
| INTEGER           | INTEGER           | |
| BIGINT            | INTEGER           | SQLite's INTEGER can store 64-bit values |
| SMALLINT          | INTEGER           | SQLite doesn't distinguish between integer sizes |
| FLOAT             | REAL              | |
| DOUBLE            | REAL              | SQLite doesn't distinguish between FLOAT and DOUBLE |
| DECIMAL           | TEXT              | Stored as text to preserve precision |
| DATE              | TEXT              | Stored in ISO8601 format: YYYY-MM-DD |
| TIME              | TEXT              | Stored in ISO8601 format: HH:MM:SS |
| DATETIME          | TEXT              | Stored in ISO8601 format: YYYY-MM-DD HH:MM:SS |
| TIMESTAMP         | TEXT              | Stored in ISO8601 format |
| BOOLEAN           | INTEGER           | 0 for false, 1 for true |
| BLOB              | BLOB              | |
| JSON              | TEXT              | Stored as JSON string |
| UUID              | TEXT              | Stored as string |
| ARRAY             | TEXT              | Stored as JSON string |
| ENUM              | TEXT              | Stored as string |

### MySQL

| ActiveRecord Type | MySQL Native Type | Notes |
|-------------------|-------------------|-------|
| CHAR              | CHAR              | |
| VARCHAR           | VARCHAR           | |
| TEXT              | TEXT              | |
| INTEGER           | INT               | |
| BIGINT            | BIGINT            | |
| SMALLINT          | SMALLINT          | |
| FLOAT             | FLOAT             | |
| DOUBLE            | DOUBLE            | |
| DECIMAL           | DECIMAL           | |
| DATE              | DATE              | |
| TIME              | TIME              | |
| DATETIME          | DATETIME          | |
| TIMESTAMP         | TIMESTAMP         | |
| BOOLEAN           | TINYINT(1)        | |
| BLOB              | BLOB              | |
| JSON              | JSON              | Native JSON type in MySQL 5.7+ |
| UUID              | CHAR(36)          | |
| ARRAY             | JSON              | Stored as JSON array |
| ENUM              | ENUM              | Native ENUM type |

### MariaDB

| ActiveRecord Type | MariaDB Native Type | Notes |
|-------------------|---------------------|-------|
| CHAR              | CHAR                | |
| VARCHAR           | VARCHAR             | |
| TEXT              | TEXT                | |
| INTEGER           | INT                 | |
| BIGINT            | BIGINT              | |
| SMALLINT          | SMALLINT            | |
| FLOAT             | FLOAT               | |
| DOUBLE            | DOUBLE              | |
| DECIMAL           | DECIMAL             | |
| DATE              | DATE                | |
| TIME              | TIME                | |
| DATETIME          | DATETIME            | |
| TIMESTAMP         | TIMESTAMP           | |
| BOOLEAN           | TINYINT(1)          | |
| BLOB              | BLOB                | |
| JSON              | JSON                | Native JSON type in MariaDB 10.2+ |
| UUID              | CHAR(36)            | |
| ARRAY             | JSON                | Stored as JSON array |
| ENUM              | ENUM                | Native ENUM type |

### PostgreSQL

| ActiveRecord Type | PostgreSQL Native Type | Notes |
|-------------------|------------------------|-------|
| CHAR              | CHAR                   | |
| VARCHAR           | VARCHAR                | |
| TEXT              | TEXT                   | |
| INTEGER           | INTEGER                | |
| BIGINT            | BIGINT                 | |
| SMALLINT          | SMALLINT               | |
| FLOAT             | REAL                   | |
| DOUBLE            | DOUBLE PRECISION       | |
| DECIMAL           | NUMERIC                | |
| DATE              | DATE                   | |
| TIME              | TIME                   | |
| DATETIME          | TIMESTAMP              | |
| TIMESTAMP         | TIMESTAMP WITH TIME ZONE | |
| BOOLEAN           | BOOLEAN                | |
| BLOB              | BYTEA                  | |
| JSON              | JSONB                  | Binary JSON format with indexing support |
| UUID              | UUID                   | Native UUID type |
| ARRAY             | ARRAY                  | Native array type |
| ENUM              | ENUM                   | Custom enumerated type |

### Oracle

| ActiveRecord Type | Oracle Native Type | Notes |
|-------------------|-------------------|-------|
| CHAR              | CHAR              | |
| VARCHAR           | VARCHAR2          | |
| TEXT              | CLOB              | |
| INTEGER           | NUMBER(10)        | |
| BIGINT            | NUMBER(19)        | |
| SMALLINT          | NUMBER(5)         | |
| FLOAT             | BINARY_FLOAT      | |
| DOUBLE            | BINARY_DOUBLE     | |
| DECIMAL           | NUMBER            | |
| DATE              | DATE              | Includes both date and time components |
| TIME              | TIMESTAMP         | |
| DATETIME          | TIMESTAMP         | |
| TIMESTAMP         | TIMESTAMP WITH TIME ZONE | |
| BOOLEAN           | NUMBER(1)         | 0 for false, 1 for true |
| BLOB              | BLOB              | |
| JSON              | CLOB              | Stored as text in Oracle 12c and earlier, native JSON in Oracle 21c+ |
| UUID              | VARCHAR2(36)      | |
| ARRAY             | VARRAY or Nested Table | Implementation depends on specific requirements |
| ENUM              | VARCHAR2 with CHECK constraint | |

### SQL Server

| ActiveRecord Type | SQL Server Native Type | Notes |
|-------------------|------------------------|-------|
| CHAR              | CHAR                   | |
| VARCHAR           | VARCHAR                | |
| TEXT              | NVARCHAR(MAX)          | |
| INTEGER           | INT                    | |
| BIGINT            | BIGINT                 | |
| SMALLINT          | SMALLINT               | |
| FLOAT             | REAL                   | |
| DOUBLE            | FLOAT                  | |
| DECIMAL           | DECIMAL                | |
| DATE              | DATE                   | |
| TIME              | TIME                   | |
| DATETIME          | DATETIME2              | |
| TIMESTAMP         | DATETIMEOFFSET         | |
| BOOLEAN           | BIT                    | |
| BLOB              | VARBINARY(MAX)         | |
| JSON              | NVARCHAR(MAX)          | Stored as text in SQL Server 2016 and earlier, native JSON functions in SQL Server 2016+ |
| UUID              | UNIQUEIDENTIFIER       | |
| ARRAY             | NVARCHAR(MAX) as JSON  | Stored as JSON string |
| ENUM              | VARCHAR with CHECK constraint | |

## Custom Type Handling

For database-specific types not covered by the unified type system, rhosocial ActiveRecord provides the `CUSTOM` type in the `DatabaseType` enum. When using this type, you can specify the exact native type as a string:

```python
class MyModel(ActiveRecord):
    # Using a PostgreSQL-specific type
    point_field = Field(DatabaseType.CUSTOM, custom_type="POINT")
```

Each database backend's type mapping configuration handles the `CUSTOM` type by passing through the specified custom type string directly to the database.

## Type Conversion Considerations

When data is transferred between Python, ActiveRecord, and the database, several type conversions occur:

1. **Python to Database**: When saving Python objects to the database, ActiveRecord converts Python types to appropriate database types
2. **Database to Python**: When retrieving data from the database, ActiveRecord converts database types back to Python types

These conversions are handled by the type converter system using `TypeConverter` protocol implementations. Some important considerations:

- **Precision Loss**: Some conversions may result in precision loss (e.g., floating-point numbers)
- **Time Zones**: Date/time values may be affected by time zone settings in the database and application
- **Character Encoding**: String data may be affected by character encoding settings
- **Range Limitations**: Some database types have range limitations that differ from Python types

## Best Practices

1. **Use the Unified Type System**: Whenever possible, use the unified `DatabaseType` enum rather than specifying native database types directly

2. **Be Aware of Database Limitations**: Understand the limitations of each database system, especially when working with specialized data types

3. **Test Type Conversions**: When working with critical data, test type conversions to ensure data integrity

4. **Consider Portability**: If your application might need to support multiple database backends, avoid using database-specific types

5. **Use Appropriate Types**: Choose the most appropriate type for your data to ensure optimal storage and performance

6. **Handle NULL Values**: Be consistent in how you handle NULL values across different database systems

7. **Document Custom Types**: When using the `CUSTOM` type, document the expected behavior across different database systems

8. **Leverage the Type Registry**: Register custom type converters for specialized data types to ensure consistent handling across your application

9. **Extend the Converter System**: For complex data types, implement custom converters that properly handle serialization and deserialization