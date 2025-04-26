# 数据类型映射

本文档解释了rhosocial ActiveRecord如何在Python、统一的ActiveRecord类型系统和每个支持的数据库系统的原生类型之间映射数据类型。

## 目录

- [类型系统概述](#类型系统概述)
- [统一类型系统](#统一类型系统)
- [数据库特定类型映射](#数据库特定类型映射)
  - [SQLite](#sqlite)
  - [MySQL](#mysql)
  - [MariaDB](#mariadb)
  - [PostgreSQL](#postgresql)
  - [Oracle](#oracle)
  - [SQL Server](#sql-server)
- [自定义类型处理](#自定义类型处理)
- [类型转换注意事项](#类型转换注意事项)
- [最佳实践](#最佳实践)

## 类型系统概述

rhosocial ActiveRecord使用三层类型系统：

1. **Python类型**：应用程序代码中使用的原生Python类型（str、int、float、datetime等）
2. **统一ActiveRecord类型**：在`DatabaseType`枚举中定义的标准化类型集，为所有数据库后端提供一致的接口
3. **原生数据库类型**：每个特定数据库系统使用的实际数据类型

这种分层方法允许您编写与数据库无关的代码，同时仍然利用每个数据库系统的特定功能。

## 统一类型系统

rhosocial ActiveRecord通过`dialect`模块中的`DatabaseType`枚举定义了统一的类型系统。这个枚举包括常见的数据类型，这些类型会映射到每个数据库后端的适当原生类型：

```python
class DatabaseType(Enum):
    # 字符串类型
    CHAR = auto()
    VARCHAR = auto()
    TEXT = auto()
    
    # 数值类型
    INTEGER = auto()
    BIGINT = auto()
    SMALLINT = auto()
    FLOAT = auto()
    DOUBLE = auto()
    DECIMAL = auto()
    
    # 日期/时间类型
    DATE = auto()
    TIME = auto()
    DATETIME = auto()
    TIMESTAMP = auto()
    
    # 布尔类型
    BOOLEAN = auto()
    
    # 二进制数据
    BLOB = auto()
    
    # JSON数据
    JSON = auto()
    
    # 其他类型
    UUID = auto()
    ARRAY = auto()
    ENUM = auto()
    CUSTOM = auto()  # 用于上面未涵盖的数据库特定类型
```

## 数据库特定类型映射

每个数据库后端实现了一个`TypeMapper`，将统一的`DatabaseType`枚举值映射到该数据库系统的适当原生类型。

### SQLite

| ActiveRecord类型 | SQLite原生类型 | 备注 |
|-------------------|-------------------|-------|
| CHAR              | TEXT              | SQLite没有固定长度的CHAR类型 |
| VARCHAR           | TEXT              | SQLite对所有字符串使用单一的TEXT类型 |
| TEXT              | TEXT              | |
| INTEGER           | INTEGER           | |
| BIGINT            | INTEGER           | SQLite的INTEGER可以存储64位值 |
| SMALLINT          | INTEGER           | SQLite不区分整数大小 |
| FLOAT             | REAL              | |
| DOUBLE            | REAL              | SQLite不区分FLOAT和DOUBLE |
| DECIMAL           | TEXT              | 存储为文本以保持精度 |
| DATE              | TEXT              | 以ISO8601格式存储：YYYY-MM-DD |
| TIME              | TEXT              | 以ISO8601格式存储：HH:MM:SS |
| DATETIME          | TEXT              | 以ISO8601格式存储：YYYY-MM-DD HH:MM:SS |
| TIMESTAMP         | TEXT              | 以ISO8601格式存储 |
| BOOLEAN           | INTEGER           | 0表示false，1表示true |
| BLOB              | BLOB              | |
| JSON              | TEXT              | 存储为JSON字符串 |
| UUID              | TEXT              | 存储为字符串 |
| ARRAY             | TEXT              | 存储为JSON字符串 |
| ENUM              | TEXT              | 存储为字符串 |

### MySQL

| ActiveRecord类型 | MySQL原生类型 | 备注 |
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
| JSON              | JSON                     | MySQL 5.7+中的原生JSON类型 |
| UUID              | CHAR(36)                 | |
| ARRAY             | JSON                     | 存储为JSON数组 |
| ENUM              | ENUM                     | 原生ENUM类型 |

### MariaDB

| ActiveRecord类型 | MariaDB原生类型 | 备注 |
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
| JSON              | JSON                     | MariaDB 10.2+中的原生JSON类型 |
| UUID              | CHAR(36)                 | |
| ARRAY             | JSON                     | 存储为JSON数组 |
| ENUM              | ENUM                     | 原生ENUM类型 |

### PostgreSQL

| ActiveRecord类型 | PostgreSQL原生类型 | 备注 |
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
| JSON              | JSONB                  | 带索引支持的二进制JSON格式 |
| UUID              | UUID                   | 原生UUID类型 |
| ARRAY             | ARRAY                  | 原生数组类型 |
| ENUM              | ENUM                   | 自定义枚举类型 |

### Oracle

| ActiveRecord类型 | Oracle原生类型 | 备注 |
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
| DATE              | DATE              | 包括日期和时间组件 |
| TIME              | TIMESTAMP         | |
| DATETIME          | TIMESTAMP         | |
| TIMESTAMP         | TIMESTAMP WITH TIME ZONE | |
| BOOLEAN           | NUMBER(1)         | 0表示false，1表示true |
| BLOB              | BLOB              | |
| JSON              | CLOB              | 在Oracle 12c及更早版本中存储为文本，在Oracle 21c+中为原生JSON |
| UUID              | VARCHAR2(36)      | |
| ARRAY             | VARRAY或嵌套表 | 实现取决于特定需求 |
| ENUM              | 带CHECK约束的VARCHAR2 | |

### SQL Server

| ActiveRecord类型 | SQL Server原生类型 | 备注 |
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
| JSON              | NVARCHAR(MAX)          | 在SQL Server 2016及更早版本中存储为文本，SQL Server 2016+中有原生JSON函数 |
| UUID              | UNIQUEIDENTIFIER       | |
| ARRAY             | 作为JSON的NVARCHAR(MAX)  | 存储为JSON字符串 |
| ENUM              | 带CHECK约束的VARCHAR | |

## 自定义类型处理

对于统一类型系统未涵盖的数据库特定类型，rhosocial ActiveRecord在`DatabaseType`枚举中提供了`CUSTOM`类型。使用此类型时，您可以将确切的原生类型指定为字符串：

```python
class MyModel(ActiveRecord):
    # 使用PostgreSQL特定类型
    point_field = Field(DatabaseType.CUSTOM, custom_type="POINT")
```

每个数据库后端的`TypeMapper`实现通过直接将指定的自定义类型字符串传递给数据库来处理`CUSTOM`类型。

## 类型转换注意事项

当数据在Python、ActiveRecord和数据库之间传输时，会发生几种类型转换：

1. **Python到数据库**：将Python对象保存到数据库时，ActiveRecord将Python类型转换为适当的数据库类型
2. **数据库到Python**：从数据库检索数据时，ActiveRecord将数据库类型转换回Python类型

这些转换由每个数据库后端的`ValueMapper`类处理。一些重要的注意事项：

- **精度损失**：某些转换可能导致精度损失（例如，浮点数）
- **时区**：日期/时间值可能受到数据库和应用程序中时区设置的影响
- **字符编码**：字符串数据可能受到字符编码设置的影响
- **范围限制**：某些数据库类型的范围限制与Python类型不同

## 最佳实践

1. **使用统一类型系统**：尽可能使用统一的`DatabaseType`枚举，而不是直接指定原生数据库类型

2. **了解数据库限制**：了解每个数据库系统的限制，特别是在处理专门的数据类型时

3. **测试类型转换**：处理关键数据时，测试类型转换以确保数据完整性

4. **考虑可移植性**：如果您的应用程序可能需要支持多个数据库后端，避免使用数据库特定类型

5. **使用适当的类型**：为您的数据选择最合适的类型，以确保最佳存储和性能

6. **处理NULL值**：在不同数据库系统中一致地处理NULL值

7. **记录自定义类型**：使用`CUSTOM`类型时，记录不同数据库系统中的预期行为