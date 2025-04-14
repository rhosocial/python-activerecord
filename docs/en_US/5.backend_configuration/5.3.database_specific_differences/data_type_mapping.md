# Data Type Mapping

This document explains how Python ActiveRecord maps data types between Python, the unified ActiveRecord type system, and the native types of each supported database system.

## Contents

- [Type System Overview](#type-system-overview)
- [Unified Type System](#unified-type-system)
- [Database-Specific Type Mappings](#database-specific-type-mappings)
  - [SQLite](#sqlite)
  - [MySQL/MariaDB](#mysqlmariadb)
  - [PostgreSQL](#postgresql)
  - [Oracle](#oracle)
  - [SQL Server](#sql-server)
- [Custom Type Handling](#custom-type-handling)
- [Type Conversion Considerations](#type-conversion-considerations)
- [Best Practices](#best-practices)

## Type System Overview

Python ActiveRecord uses a three-layer type system:

1. **Python Types**: The native Python types used in your application code (str, int, float, datetime, etc.)
2. **Unified ActiveRecord Types**: A standardized set of types defined in the `DatabaseType` enum that provides a consistent interface across all database backends
3. **Native Database Types**: The actual data types used by each specific database system

This layered approach allows you to write database-agnostic code while still leveraging the specific capabilities of each database system.

## Unified Type System

Python ActiveRecord defines a unified type system through the `DatabaseType` enum in the `dialect` module. This enum includes common data types that are mapped to appropriate native types for each database backend:

```python
class DatabaseType(Enum):
    # String types
    CHAR = auto()
    VARCHAR = auto()
    TEXT = auto()
    
    # Numeric types
    INTEGER = auto()
    BIGINT = auto()
    SMALLINT = auto()
    FLOAT = auto()
    DOUBLE = auto()
    DECIMAL = auto()
    
    # Date/time types
    DATE = auto()
    TIME = auto()
    DATETIME = auto()
    TIMESTAMP = auto()
    
    # Boolean type
    BOOLEAN = auto()
    
    # Binary data
    BLOB = auto()
    
    # JSON data
    JSON = auto()
    
    # Other types
    UUID = auto()
    ARRAY = auto()
    ENUM = auto()
    CUSTOM = auto()  # For database-specific types not covered above
```

## Database-Specific Type Mappings

Each database backend implements a `TypeMapper` that maps the unified `DatabaseType` enum values to appropriate native types for that database system.

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

### MySQL/MariaDB

| ActiveRecord Type | MySQL/MariaDB Native Type | Notes |
|-------------------|--------------------------|-------|
| CHAR              | CHAR                     | |
| VARCHAR           | VARCHAR                  | |
| TEXT              | TEXT                     | |
| INTEGER           | INT                      | |
| BIGINT            | BIGINT                   | |
| SMALLINT          | SMALLINT                 | |
| FLOAT             | FLOAT                    | |
| DOUBLE            | DOUBLE                   | |
| DECIMAL           | DECIMAL                  | |
| DATE              | DATE                     | |
| TIME              | TIME                     | |
| DATETIME          | DATETIME                 | |
| TIMESTAMP         | TIMESTAMP                | |
| BOOLEAN           | TINYINT(1)               | |
| BLOB              | BLOB                     | |
| JSON              | JSON                     | Native JSON type in MySQL 5.7+ and MariaDB 10.2+ |
| UUID              | CHAR(36)                 | |
| ARRAY             | JSON                     | Stored as JSON array |
| ENUM              | ENUM                     | Native ENUM type |

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

For database-specific types not covered by the unified type system, Python ActiveRecord provides the `CUSTOM` type in the `DatabaseType` enum. When using this type, you can specify the exact native type as a string:

```python
class MyModel(ActiveRecord):
    # Using a PostgreSQL-specific type
    point_field = Field(DatabaseType.CUSTOM, custom_type="POINT")
```

Each database backend's `TypeMapper` implementation handles the `CUSTOM` type by passing through the specified custom type string directly to the database.

## Type Conversion Considerations

When data is transferred between Python, ActiveRecord, and the database, several type conversions occur:

1. **Python to Database**: When saving Python objects to the database, ActiveRecord converts Python types to appropriate database types
2. **Database to Python**: When retrieving data from the database, ActiveRecord converts database types back to Python types

These conversions are handled by the `ValueMapper` class in each database backend. Some important considerations:

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