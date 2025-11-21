# 实现自定义数据库后端

本指南提供了如何为rhosocial ActiveRecord实现自定义数据库后端的详细说明。

## 前提条件

在实现自定义数据库后端之前，您应该：

1. 熟悉rhosocial ActiveRecord架构
2. 了解您想要实现的数据库系统
3. 已安装必要的数据库驱动程序包

## 实现步骤

实现自定义数据库后端涉及几个关键步骤：

### 1. 创建后端目录结构

您可以在两个位置实现自定义后端：

#### 在标准实现目录中

如果您计划将后端贡献回主项目，可以在标准实现目录中创建：

```
rhosocial/activerecord/backend/impl/your_backend_name/
```

#### 在自定义位置

如果您的后端是特定于应用程序的或将作为单独的包发布，可以在任何Python模块中实现：

```
your_package/database/backends/your_backend_name/
```

无论选择哪个位置，都应创建以下文件：

```
__init__.py       # 包初始化和导出
backend.py        # 主要后端实现
dialect.py        # SQL方言实现
types.py          # 类型映射定义
```

### 2. 实现后端类

在`backend.py`中，创建一个继承自`StorageBackend`的类：

```python
from ...base import StorageBackend, ColumnTypes

class YourBackendName(StorageBackend):
    """您的数据库后端实现"""
    
    def __init__(self, **kwargs):
        """初始化您的后端
        
        Args:
            **kwargs: 配置参数
        """
        super().__init__(**kwargs)
        # 初始化您的数据库连接和设置
        
    @property
    def dialect(self):
        """获取此后端的SQL方言"""
        from .dialect import YourDialectClass
        return YourDialectClass()
    
    def connect(self):
        """建立数据库连接"""
        # 实现连接逻辑
        
    def disconnect(self):
        """关闭数据库连接"""
        # 实现断开连接逻辑
        
    def is_connected(self) -> bool:
        """检查数据库是否已连接"""
        # 实现连接检查
        
    def execute(self, query, params=None, **options):
        """执行查询
        
        Args:
            query: SQL查询字符串
            params: 查询参数
            **options: 附加选项
            
        Returns:
            QueryResult: 查询结果
        """
        # 实现查询执行逻辑
        
    # 实现其他必需方法
```

### 3. 实现SQL方言

在`dialect.py`中，创建一个继承自`SQLDialectBase`的类：

```python
from ...dialect import SQLDialectBase, SQLBuilder, TypeMapper
from .types import YourTypeMapper

class YourDialectClass(SQLDialectBase):
    """您的数据库的SQL方言实现"""
    
    def __init__(self):
        super().__init__()
        self._type_mapper = YourTypeMapper()
    
    @property
    def type_mapper(self) -> TypeMapper:
        """获取此方言的类型映射器"""
        return self._type_mapper
    
    def create_builder(self) -> SQLBuilder:
        """为此方言创建SQL构建器"""
        return YourSQLBuilder(self)
    
    # 实现其他方言特定方法

class YourSQLBuilder(SQLBuilder):
    """您的数据库的SQL构建器"""
    
    def __init__(self, dialect):
        super().__init__(dialect)
    
    def get_placeholder(self, index=None) -> str:
        """获取参数占位符语法
        
        Args:
            index: 参数索引（可选）
            
        Returns:
            str: 占位符字符串
        """
        # 返回适合您的数据库的占位符语法
        # 示例：SQLite使用'?'，MySQL使用'%s'，PostgreSQL使用'$1'
        
    # 实现其他构建器特定方法
```

### 4. 实现类型映射与适配器

在 `types.py` 文件中，您需要为您的数据库定义类型映射并创建特定的 `SQLTypeAdapter` 实现。这对于确保数据在 Python 类型和数据库原生类型之间正确转换至关重要。

#### a. SQLTypeAdapter 协议

`SQLTypeAdapter` 协议是类型转换系统的基础。您创建的任何自定义适配器都必须遵循此协议：

```python
from typing import Any
from ...typing import SQLTypeAdapter

class YourCustomAdapter(SQLTypeAdapter):
    """
    一个为您的后端处理特定数据类型的适配器。
    """
    def to_database(self, value: Any) -> Any:
        """
        将 Python 值转换为其数据库表示形式。
        例如，将 Python 的 `datetime` 对象转换为适用于 DATETIME 列的字符串。
        """
        # 在此实现
        return str(value)

    def to_python(self, value: Any, from_type: Any) -> Any:
        """
        将数据库中的值转换回指定的 Python 类型。
        例如，将数据库中的字符串转换回 `datetime` 对象。
        """
        # 在此实现
        import datetime
        return datetime.datetime.fromisoformat(value)
```

#### b. 创建后端特定的适配器

您的后端可能需要为不同的数据类型（例如，处理 JSON、UUID 或特定的日期/时间格式）提供多个自定义适配器。您应该在 `types.py` 文件中实现这些适配器。

```python
# 位于 rhosocial/activerecord/backend/impl/your_backend_name/types.py

from ...base import SQLTypeAdapter, adapter_registry
from ...typing import DatabaseType

# 处理布尔值作为整数的示例适配器
class BooleanAdapter(SQLTypeAdapter):
    def to_database(self, value: bool) -> int:
        return 1 if value else 0

    def to_python(self, value: int, from_type: Any) -> bool:
        return bool(value)

# 直接支持的类型的示例
class StringAdapter(SQLTypeAdapter):
    def to_database(self, value: str) -> str:
        return value

    def to_python(self, value: str, from_type: Any) -> str:
        return value
```

#### c. 注册类型适配器

定义适配器后，您必须注册它们，以便后端知道为每个 `DatabaseType` 使用哪个适配器。这通常在 `types.py` 文件中的一个专用函数中完成。主 `Backend` 类将在其初始化期间调用此函数。

```python
# 位于 rhosocial/activerecord/backend/impl/your_backend_name/types.py

def register_your_backend_adapters():
    """
    为 YourBackend 注册所有自定义类型适配器。
    """
    #为您要覆盖的类型注销默认适配器
    adapter_registry.unregister(DatabaseType.BOOLEAN)
    
    # 注册您的自定义适配器
    adapter_registry.register(DatabaseType.BOOLEAN, BooleanAdapter())
    
    # 您还可以为后端特有的自定义类型注册适配器
    # 例如，如果您的数据库有原生的 'MONEY' 类型：
    # adapter_registry.register(DatabaseType.CUSTOM, MoneyAdapter(), "MONEY")
```

在您的主后端类（`backend.py`）中，您必须调用此注册函数。

```python
# 位于 rhosocial/activerecord/backend/impl/your_backend_name/backend.py
from .types import register_your_backend_adapters

class YourBackendName(StorageBackend):
    """您的数据库后端实现"""
    
    def __init__(self, **kwargs):
        """初始化您的后端"""
        super().__init__(**kwargs)
        # 为此后端注册类型适配器
        register_your_backend_adapters()
        # ...其余的初始化
```

此注册过程可确保当您的后端处于活动状态时，ActiveRecord 将使用您的自定义类型转换逻辑而不是默认实现。

### 5. 更新包初始化

在`__init__.py`中，导出您的后端类：

```python
"""您的rhosocial ActiveRecord数据库后端实现。

本模块提供：
- 您的数据库后端，具有连接管理和查询执行功能
- 您的数据库的SQL方言实现
- Python类型与您的数据库类型之间的类型映射
"""

from .backend import YourBackendName
from .dialect import YourDialectClass

__all__ = [
    # 方言
    'YourDialectClass',
    
    # 后端
    'YourBackendName',
]
```

## 必需方法

您的后端实现必须提供以下方法：

| 方法 | 描述 |
|--------|-------------|
| `connect()` | 建立数据库连接 |
| `disconnect()` | 关闭数据库连接 |
| `is_connected()` | 检查数据库是否已连接 |
| `execute()` | 执行查询 |
| `begin_transaction()` | 开始事务 |
| `commit_transaction()` | 提交事务 |
| `rollback_transaction()` | 回滚事务 |
| `create_table()` | 创建数据库表 |
| `drop_table()` | 删除数据库表 |
| `table_exists()` | 检查表是否存在 |
| `get_columns()` | 获取表的列信息 |

## 事务支持

实现事务支持对于数据库后端至关重要。您的实现应处理：

1. 事务嵌套（如果您的数据库支持）
2. 保存点（如果支持）
3. 不同的隔离级别

```python
def begin_transaction(self, isolation_level=None):
    """开始事务
    
    Args:
        isolation_level: 可选的隔离级别
    """
    if self._transaction_level == 0:
        # 开始新事务
        cursor = self._get_cursor()
        if isolation_level:
            # 如果指定了隔离级别，则设置
            cursor.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
        cursor.execute("BEGIN TRANSACTION")
    else:
        # 为嵌套事务创建保存点（如果支持）
        cursor = self._get_cursor()
        cursor.execute(f"SAVEPOINT sp_{self._transaction_level}")
    
    self._transaction_level += 1
```

## 错误处理

您的后端应处理数据库特定的错误，并将其转换为ActiveRecord异常：

```python
def _handle_execution_error(self, error):
    """处理数据库特定错误
    
    Args:
        error: 原始数据库错误
        
    Raises:
        适当的ActiveRecord异常
    """
    # 将数据库特定错误映射到ActiveRecord异常
    error_code = getattr(error, 'code', None)
    
    if error_code == 'YOUR_DB_CONSTRAINT_ERROR':
        from ...errors import ConstraintViolationError
        raise ConstraintViolationError(str(error))
    elif error_code == 'YOUR_DB_CONNECTION_ERROR':
        from ...errors import ConnectionError
        raise ConnectionError(str(error))
    # 处理其他特定错误
    
    # 如果未处理，则重新引发为通用数据库错误
    from ...errors import DatabaseError
    raise DatabaseError(str(error))
```

## 测试您的后端

为您的后端实现创建全面的测试：

1. 基本连接测试
2. CRUD操作测试
3. 事务测试
4. 错误处理测试
5. 性能测试

## 注册您的后端

一旦您实现了自定义后端，您需要将其注册到ActiveRecord：

```python
from rhosocial.activerecord import configure
from your_module import YourBackendName

# 创建您的后端的实例
your_backend = YourBackendName(**config)

# 配置ActiveRecord使用您的后端
configure(backend=your_backend)
```

或者，您可以扩展后端工厂以支持您的自定义后端：

```python
from rhosocial.activerecord.backend import create_backend as original_create_backend
from your_module import YourBackendName

def create_backend(backend_type, **config):
    """扩展后端工厂"""
    if backend_type == 'your_backend_name':
        return YourBackendName(**config)
    else:
        return original_create_backend(backend_type, **config)

# 替换原始工厂
import rhosocial.activerecord.backend
rhosocial.activerecord.backend.create_backend = create_backend
```

## 测试您的后端

彻底测试您的自定义后端对于确保其可靠性和兼容性至关重要：

### 创建全面的测试套件

```python
import unittest
from rhosocial.activerecord import configure
from your_module import YourBackendName

class TestYourBackend(unittest.TestCase):
    def setUp(self):
        # 使用适合测试的配置初始化您的后端
        self.backend = YourBackendName(in_memory=True)  # 如果支持内存模式
        self.backend.connect()
        configure(backend=self.backend)
        
    def tearDown(self):
        self.backend.disconnect()
        
    def test_basic_operations(self):
        # 测试基本CRUD操作
        self.backend.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        self.backend.execute("INSERT INTO test VALUES (1, 'Test')")
        result = self.backend.execute("SELECT * FROM test")
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]['name'], 'Test')
        
    def test_transactions(self):
        # 测试事务支持
        self.backend.create_table('test_tx', {'id': 'INTEGER', 'value': 'TEXT'})
        
        # 测试提交
        self.backend.begin_transaction()
        self.backend.execute("INSERT INTO test_tx VALUES (1, 'Commit')")
        self.backend.commit_transaction()
        result = self.backend.execute("SELECT * FROM test_tx")
        self.assertEqual(len(result.rows), 1)
        
        # 测试回滚
        self.backend.begin_transaction()
        self.backend.execute("INSERT INTO test_tx VALUES (2, 'Rollback')")
        self.backend.rollback_transaction()
        result = self.backend.execute("SELECT * FROM test_tx")
        self.assertEqual(len(result.rows), 1)  # 仍然只有一行
        
    # 添加更多测试...
```

### 测试最佳实践

1. **模仿现有后端测试**：查看rhosocial ActiveRecord的测试套件，了解如何测试标准后端
2. **确保分支覆盖完整**：测试所有方法的各种条件和边缘情况
3. **模拟各种使用场景**：测试您的后端在不同查询类型、事务和错误条件下的行为
4. **集成测试**：测试您的后端与ActiveRecord模型的集成
5. **性能测试**：评估您的后端在各种负载条件下的性能

## 使用示例

一旦实现，您的后端可以像任何其他ActiveRecord后端一样使用：

```python
from rhosocial.activerecord.model import ActiveRecord, configure

# 配置ActiveRecord使用您的后端
configure(backend='your_backend_name', host='localhost', database='your_db')

# 使用您的后端定义模型
class User(ActiveRecord):
    __tablename__ = 'users'
```

## 最佳实践

1. **遵循现有模式**：研究现有后端实现（SQLite、MySQL、PostgreSQL）以获取指导
2. **处理边缘情况**：考虑所有可能的错误场景和边缘情况
3. **全面记录**：为您的后端的功能和限制提供清晰的文档
4. **全面测试**：为您的后端的所有方面创建全面的测试
5. **考虑性能**：优化您的实现以提高性能

## 结论

为rhosocial ActiveRecord实现自定义数据库后端需要仔细关注细节，并全面了解ActiveRecord架构和您的目标数据库系统。通过遵循本指南，您可以创建一个与ActiveRecord框架无缝集成的强大后端实现。