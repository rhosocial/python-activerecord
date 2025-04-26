# 扩展现有后端

本指南解释了如何在rhosocial ActiveRecord中扩展或修改现有数据库后端的行为。

## 引言

有时您可能需要自定义现有数据库后端的行为，而无需创建全新的实现。rhosocial ActiveRecord提供了几种扩展现有后端的方法，以添加功能或修改行为。

## 何时扩展现有后端

在以下情况下，扩展现有后端是合适的：

1. 您需要添加标准实现中未包含的数据库特定功能支持
2. 您想要为特定用例修改某些操作的行为
3. 您需要与其他库或服务集成，同时保持与基础后端的兼容性
4. 您想要为数据库操作添加监控、日志记录或性能跟踪

## 扩展方法

扩展现有后端有几种方法：

### 1. 子类化

最直接的方法是对现有后端实现进行子类化：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class ExtendedSQLiteBackend(SQLiteBackend):
    """具有自定义功能的扩展SQLite后端"""
    
    def execute(self, query, params=None, **options):
        """重写execute方法以添加自定义行为"""
        # 在此添加执行前逻辑
        self.logger.debug(f"自定义日志：执行查询：{query}")
        
        # 调用父实现
        result = super().execute(query, params, **options)
        
        # 在此添加执行后逻辑
        self.logger.debug(f"查询返回{len(result.rows)}行")
        
        return result
    
    def connect(self):
        """重写connect方法以添加自定义初始化"""
        # 调用父实现
        super().connect()
        
        # 添加自定义初始化
        cursor = self._get_cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # 示例：强制WAL模式
```

### 2. 扩展方言

您可以扩展SQL方言以自定义SQL生成：

```python
from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect, MySQLBuilder

class ExtendedMySQLDialect(MySQLDialect):
    """具有自定义SQL生成的扩展MySQL方言"""
    
    def create_builder(self):
        """创建自定义SQL构建器"""
        return ExtendedMySQLBuilder(self)

class ExtendedMySQLBuilder(MySQLBuilder):
    """扩展MySQL SQL构建器"""
    
    def build_select(self, query_parts):
        """重写select查询构建以添加自定义行为"""
        # 为SELECT查询添加自定义提示或选项
        if 'hints' in query_parts and query_parts['hints']:
            query_parts['select'] = f"SELECT /*+ {query_parts['hints']} */"
        
        # 调用父实现
        return super().build_select(query_parts)
```

### 3. 自定义类型处理

扩展类型映射器以添加对自定义类型的支持：

```python
from rhosocial.activerecord.backend.impl.pgsql.types import PostgreSQLTypeMapper
from rhosocial.activerecord.backend.dialect import TypeMapping, DatabaseType

class ExtendedPostgreSQLTypeMapper(PostgreSQLTypeMapper):
    """具有自定义类型的扩展PostgreSQL类型映射器"""
    
    def __init__(self):
        super().__init__()
        
        # 添加或覆盖类型映射
        self._type_map[DatabaseType.CUSTOM] = TypeMapping("JSONB")  # 将CUSTOM映射到JSONB
        
        # 添加自定义类型处理程序
        self._value_handlers[DatabaseType.CUSTOM] = self._handle_custom_type
    
    def _handle_custom_type(self, value):
        """自定义类型转换处理程序"""
        import json
        if isinstance(value, dict) or isinstance(value, list):
            return json.dumps(value)
        return str(value)
```

## 与ActiveRecord集成

要使用您的扩展后端，您需要将其注册到ActiveRecord：

```python
from rhosocial.activerecord import configure
from your_module import ExtendedSQLiteBackend

# 创建您的扩展后端的实例
extended_backend = ExtendedSQLiteBackend(database='your_database.db')

# 配置ActiveRecord使用您的扩展后端
configure(backend=extended_backend)
```

或者，您可以修改后端工厂以支持您的扩展后端：

```python
from rhosocial.activerecord.backend import create_backend as original_create_backend
from your_module import ExtendedSQLiteBackend, ExtendedMySQLBackend

def create_backend(backend_type, **config):
    """扩展后端工厂"""
    if backend_type == 'extended_sqlite':
        return ExtendedSQLiteBackend(**config)
    elif backend_type == 'extended_mysql':
        return ExtendedMySQLBackend(**config)
    else:
        return original_create_backend(backend_type, **config)

# 替换原始工厂
import rhosocial.activerecord.backend
rhosocial.activerecord.backend.create_backend = create_backend
```

## 实用示例

### 添加查询分析

```python
import time
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class ProfilingMySQLBackend(MySQLBackend):
    """具有查询分析的MySQL后端"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_stats = []
    
    def execute(self, query, params=None, **options):
        """执行带分析的查询"""
        start_time = time.time()
        
        try:
            result = super().execute(query, params, **options)
            duration = time.time() - start_time
            
            # 记录查询统计信息
            self.query_stats.append({
                'query': query,
                'params': params,
                'duration': duration,
                'rows': len(result.rows) if result.rows else 0,
                'success': True
            })
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            
            # 记录失败的查询
            self.query_stats.append({
                'query': query,
                'params': params,
                'duration': duration,
                'error': str(e),
                'success': False
            })
            
            raise
    
    def get_slow_queries(self, threshold=1.0):
        """获取耗时超过阈值的查询"""
        return [q for q in self.query_stats if q['duration'] > threshold]
```

### 添加自定义JSON操作

```python
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLBackend
from rhosocial.activerecord.backend.impl.pgsql.dialect import PostgreSQLDialect

class JSONEnhancedPostgreSQLDialect(PostgreSQLDialect):
    """具有增强JSON操作的PostgreSQL方言"""
    
    def json_contains(self, column, value):
        """检查JSON列是否包含值"""
        return f"{column} @> %s::jsonb"
    
    def json_extract_path(self, column, path):
        """从JSON路径提取值"""
        return f"{column}#>>%s"

class JSONEnhancedPostgreSQLBackend(PostgreSQLBackend):
    """具有增强JSON支持的PostgreSQL后端"""
    
    @property
    def dialect(self):
        """获取此后端的SQL方言"""
        if not hasattr(self, '_dialect_instance'):
            self._dialect_instance = JSONEnhancedPostgreSQLDialect()
        return self._dialect_instance
```

## 最佳实践

1. **最小化重写**：只重写您需要更改的方法
2. **调用父方法**：除非您完全替换功能，否则始终调用父实现
3. **保持兼容性**：确保您的扩展与ActiveRecord API保持兼容
4. **全面测试**：为您的扩展后端创建全面的测试
5. **记录更改**：清晰记录您的扩展后端中的更改和添加内容

## 实现位置的灵活性

虽然标准后端实现通常位于`rhosocial.activerecord.backend.impl`目录下，但您的扩展后端可以放置在项目的任何位置：

1. **在impl目录中**：如果您计划将扩展贡献回主项目，可以将其放在impl目录中
2. **在自立目录中**：如果您的扩展是特定于应用程序的或将作为单独的包发布，可以将其放在任何Python模块中

```python
# 在自定义位置实现的扩展后端
from your_package.database.backends import CustomSQLiteBackend

# 配置ActiveRecord使用您的扩展后端
from rhosocial.activerecord import configure
configure(backend=CustomSQLiteBackend(database='your_database.db'))
```

## 测试您的扩展

彻底测试您的扩展后端至关重要：

1. **模仿现有后端测试**：查看rhosocial ActiveRecord的测试套件，了解如何测试标准后端
2. **确保分支覆盖完整**：测试所有重写方法的各种条件和边缘情况
3. **模拟各种使用场景**：测试您的后端在不同查询类型、事务和错误条件下的行为

```python
import unittest
from your_package.database.backends import ExtendedSQLiteBackend

class TestExtendedSQLiteBackend(unittest.TestCase):
    def setUp(self):
        self.backend = ExtendedSQLiteBackend(database=':memory:')
        self.backend.connect()
        
    def tearDown(self):
        self.backend.disconnect()
        
    def test_custom_functionality(self):
        # 测试您添加的自定义功能
        result = self.backend.execute("SELECT sqlite_version()")
        self.assertIsNotNone(result)
        
    # 添加更多测试...
```

## 限制和注意事项

1. **升级兼容性**：升级到较新版本的rhosocial ActiveRecord时，您的扩展可能会中断
2. **性能影响**：复杂的扩展可能会影响性能
3. **维护负担**：随着基础实现的发展，您需要维护您的扩展

## 结论

扩展现有数据库后端提供了一种强大的方式，可以根据您的特定需求自定义rhosocial ActiveRecord，而无需创建全新的实现。通过遵循本指南中概述的方法，您可以添加功能、修改行为或与其他服务集成，同时保持与ActiveRecord框架的兼容性。