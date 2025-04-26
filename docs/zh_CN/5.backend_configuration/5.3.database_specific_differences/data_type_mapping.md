# 数据类型映射

本文档解释了rhosocial ActiveRecord如何在Python、统一的ActiveRecord类型系统和每个支持的数据库系统的原生类型之间映射数据类型。

## 目录

- [类型系统概述](#类型系统概述)
- [统一类型系统](#统一类型系统)
- [类型转换器系统](#类型转换器系统)
- [类型注册表](#类型注册表)
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

rhosocial ActiveRecord通过`typing`模块中的`DatabaseType`枚举定义了统一的类型系统。这个枚举包括常见的数据类型，这些类型会映射到每个数据库后端的适当原生类型：

```python
class DatabaseType(Enum):
    """
    跨各种数据库系统的统一数据库类型定义。

    此枚举提供了一组标准的数据库列类型，可以映射到每个数据库后端的特定实现。
    """

    # --- 标准数值类型 ---
    TINYINT = auto()  # 小整数（通常为1字节）
    SMALLINT = auto()  # 小整数（通常为2字节）
    INTEGER = auto()  # 标准整数（通常为4字节）
    BIGINT = auto()  # 大整数（通常为8字节）
    FLOAT = auto()  # 单精度浮点数
    DOUBLE = auto()  # 双精度浮点数
    DECIMAL = auto()  # 固定精度小数
    NUMERIC = auto()  # 通用数值类型
    REAL = auto()  # 实数类型

    # --- 标准字符串类型 ---
    CHAR = auto()  # 固定长度字符串
    VARCHAR = auto()  # 有限制的可变长度字符串
    TEXT = auto()  # 无限制的可变长度字符串
    TINYTEXT = auto()  # 非常小的文本（最多255个字符）
    MEDIUMTEXT = auto()  # 中等大小的文本
    LONGTEXT = auto()  # 大文本

    # --- 标准日期和时间类型 ---
    DATE = auto()  # 仅日期（年、月、日）
    TIME = auto()  # 仅时间（时、分、秒）
    DATETIME = auto()  # 不带时区的日期和时间
    TIMESTAMP = auto()  # 带时区的日期和时间
    INTERVAL = auto()  # 时间间隔

    # --- 标准二进制类型 ---
    BLOB = auto()  # 二进制大对象
    TINYBLOB = auto()  # 小二进制对象
    MEDIUMBLOB = auto()  # 中等二进制对象
    LONGBLOB = auto()  # 大二进制对象
    BYTEA = auto()  # 二进制数据

    # --- 标准布尔类型 ---
    BOOLEAN = auto()  # 布尔值（真/假）

    # --- 常见扩展类型 ---
    UUID = auto()  # 通用唯一标识符

    # --- JSON类型 ---
    JSON = auto()  # JSON文档
    JSONB = auto()  # 二进制JSON

    # --- 数组类型 ---
    ARRAY = auto()  # 值数组

    # --- XML类型 ---
    XML = auto()  # XML文档

    # --- 键值类型 ---
    HSTORE = auto()  # 键值存储

    # --- 网络地址类型 ---
    INET = auto()  # IPv4或IPv6主机地址
    CIDR = auto()  # IPv4或IPv6网络地址
    MACADDR = auto()  # MAC地址
    MACADDR8 = auto()  # MAC地址（EUI-64格式）

    # --- 几何类型 ---
    POINT = auto()  # 平面上的点(x,y)
    LINE = auto()  # 无限线
    LSEG = auto()  # 线段
    BOX = auto()  # 矩形框
    PATH = auto()  # 闭合和开放路径
    POLYGON = auto()  # 多边形（类似于闭合路径）
    CIRCLE = auto()  # 圆
    GEOMETRY = auto()  # 通用几何类型
    GEOGRAPHY = auto()  # 地理数据类型

    # --- 范围类型 ---
    INT4RANGE = auto()  # 整数范围
    INT8RANGE = auto()  # 大整数范围
    NUMRANGE = auto()  # 数值范围
    TSRANGE = auto()  # 不带时区的时间戳范围
    TSTZRANGE = auto()  # 带时区的时间戳范围
    DATERANGE = auto()  # 日期范围

    # --- 全文搜索类型 ---
    TSVECTOR = auto()  # 文本搜索文档
    TSQUERY = auto()  # 文本搜索查询

    # --- 货币类型 ---
    MONEY = auto()  # 货币金额

    # --- 位字符串类型 ---
    BIT = auto()  # 固定长度位字符串
    VARBIT = auto()  # 可变长度位字符串

    # --- 枚举和集合类型 ---
    ENUM = auto()  # 字符串值的枚举
    SET = auto()  # 字符串值的集合

    # --- 大对象类型 ---
    CLOB = auto()  # 字符大对象
    NCLOB = auto()  # 国家字符大对象

    # --- Unicode类型 ---
    NCHAR = auto()  # Unicode固定长度字符数据
    NVARCHAR = auto()  # Unicode可变长度字符数据
    NTEXT = auto()  # Unicode可变长度字符数据

    # --- 行标识符类型 ---
    ROWID = auto()  # 物理行地址
    UROWID = auto()  # 通用行ID

    # --- 层次类型 ---
    HIERARCHYID = auto()  # 树层次位置

    # --- 可扩展自定义类型 ---
    CUSTOM = auto()  # 用于上面未涵盖的数据库特定类型
```

## 类型转换器系统

类型转换器系统负责在Python类型和数据库类型之间转换数据。它由一系列处理特定类型转换的转换器类组成。

### 转换器架构

转换器系统围绕以下组件构建：

1. **BaseTypeConverter**：定义所有类型转换器接口的抽象基类
2. **TypeConverterFactory**：创建和管理类型转换器实例的工厂类
3. **专用转换器**：针对特定类型转换的具体实现

```python
class BaseTypeConverter(ABC):
    @abstractmethod
    def to_python(self, value, field=None):
        """将数据库值转换为Python对象"""
        pass
        
    @abstractmethod
    def to_database(self, value, field=None):
        """将Python对象转换为数据库值"""
        pass
```

### 内置转换器

rhosocial ActiveRecord为常见数据类型提供了内置转换器：

| 转换器类 | Python类型 | 数据库类型 |
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

## 类型注册表

类型注册表是一个中央存储库，管理Python类型、ActiveRecord类型和数据库特定类型之间的映射。它允许动态注册自定义类型转换器。

### 注册表架构

注册表系统由以下部分组成：

1. **TypeRegistry**：维护类型之间映射的单例类
2. **TypeRegistration**：保存已注册类型信息的数据类

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
        """注册新的类型映射"""
        self._python_to_db_type[python_type] = db_type
        self._db_type_to_converter[db_type] = converter_class
    
    def get_db_type(self, python_type):
        """获取Python类型对应的数据库类型"""
        return self._python_to_db_type.get(python_type)
    
    def get_converter(self, db_type):
        """获取数据库类型对应的转换器"""
        return self._db_type_to_converter.get(db_type)
```

### 自定义类型注册

您可以注册自定义类型转换器来处理专门的数据类型：

```python
# 创建自定义转换器
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

# 注册自定义转换器
registry = TypeRegistry()
registry.register(Point, DatabaseType.CUSTOM, PointConverter)
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

8. **利用类型注册表**：为专门的数据类型注册自定义类型转换器，以确保在整个应用程序中一致处理

9. **扩展转换器系统**：对于复杂的数据类型，实现正确处理序列化和反序列化的自定义转换器