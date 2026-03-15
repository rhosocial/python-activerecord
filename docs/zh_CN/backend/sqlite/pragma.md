# Pragma 系统

SQLite PRAGMA 语句是 SQLite 特有的配置和查询机制，用于控制数据库行为、查询数据库状态和执行诊断操作。rhosocial-activerecord 为 SQLite 后端提供了完整的 Pragma 系统支持。

## 概述

Pragma 系统提供以下功能：

- **配置管理**：查询和修改数据库运行时配置
- **信息查询**：获取数据库结构、索引、外键等元信息
- **诊断工具**：执行完整性检查和调试
- **性能调优**：优化缓存、内存映射等性能参数
- **版本兼容**：自动检查 Pragma 的版本兼容性

## Pragma 分类

Pragma 按功能分为六大类：

| 类别 | 说明 | 读写 | 示例 |
|------|------|------|------|
| CONFIGURATION | 配置类 | 读写 | foreign_keys, journal_mode |
| INFORMATION | 信息查询类 | 只读 | table_info, index_list |
| DEBUG | 调试类 | 只读 | integrity_check |
| PERFORMANCE | 性能调优类 | 读写 | cache_size, mmap_size |
| WAL | WAL 专用类 | 读写 | wal_checkpoint |
| COMPILE_TIME | 编译时类 | 只读 | compile_options |

## 使用方式

### 获取 Pragma 信息

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# 获取单个 Pragma 信息
info = dialect.get_pragma_info('foreign_keys')
print(f"名称: {info.name}")
print(f"类别: {info.category}")
print(f"描述: {info.description}")
print(f"只读: {info.read_only}")
print(f"默认值: {info.default_value}")
```

### 生成 Pragma SQL

```python
# 读取 Pragma 的 SQL
sql = dialect.get_pragma_sql('journal_mode')
# 结果: "PRAGMA journal_mode"

# 带参数的 Pragma 查询
sql = dialect.get_pragma_sql('table_info', argument='users')
# 结果: "PRAGMA table_info(users)"
```

### 设置 Pragma SQL

```python
# 设置 Pragma 值的 SQL
sql = dialect.set_pragma_sql('foreign_keys', 1)
# 结果: "PRAGMA foreign_keys = 1"

sql = dialect.set_pragma_sql('journal_mode', 'WAL')
# 结果: "PRAGMA journal_mode = WAL"

# 尝试设置只读 Pragma 会抛出异常
try:
    sql = dialect.set_pragma_sql('table_info', 'users')  # 只读 Pragma
except ValueError as e:
    print(f"错误: {e}")
```

### 按类别查询

```python
from rhosocial.activerecord.backend.impl.sqlite.pragma import PragmaCategory

# 获取所有配置类 Pragma
config_pragmas = dialect.get_pragmas_by_category(PragmaCategory.CONFIGURATION)
for info in config_pragmas:
    print(f"{info.name}: {info.description}")

# 获取所有 Pragma 信息
all_pragmas = dialect.get_all_pragma_infos()
print(f"总共有 {len(all_pragmas)} 个 Pragma")
```

### 检查可用性

```python
# 检查 Pragma 是否在当前版本可用
if dialect.is_pragma_available('table_list'):
    print("table_list Pragma 可用 (需要 SQLite 3.37.0+)")
```

## 配置类 Pragma

配置类 Pragma 用于控制数据库运行时行为，可以读取和修改。

### foreign_keys

控制外键约束检查。

```python
# 获取信息
info = dialect.get_pragma_info('foreign_keys')
# 属性: read_only=False, value_type=bool, default_value=False

# SQL 示例
# PRAGMA foreign_keys          -- 查询当前状态
# PRAGMA foreign_keys = 1      -- 启用外键约束
# PRAGMA foreign_keys = 0      -- 禁用外键约束
```

**版本要求**：SQLite 3.6.19+

### journal_mode

控制数据库日志模式。

```python
info = dialect.get_pragma_info('journal_mode')
# 允许值: ['DELETE', 'TRUNCATE', 'PERSIST', 'MEMORY', 'WAL', 'OFF']
# 默认值: 'DELETE'

# SQL 示例
# PRAGMA journal_mode          -- 查询当前模式
# PRAGMA journal_mode = WAL    -- 设置为 WAL 模式
```

**版本要求**：SQLite 3.0.0+

### synchronous

控制数据同步到磁盘的方式。

```python
info = dialect.get_pragma_info('synchronous')
# 允许值: ['OFF', 'NORMAL', 'FULL', 'EXTRA']
# 默认值: 'FULL'

# SQL 示例
# PRAGMA synchronous = NORMAL  -- 推荐用于 WAL 模式
```

**版本要求**：SQLite 3.0.0+

### 其他配置类 Pragma

| Pragma | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| locking_mode | str | NORMAL | 锁定模式 |
| temp_store | str | DEFAULT | 临时存储位置 |
| auto_vacuum | str | NONE | 自动清理模式 |
| busy_timeout | int | 0 | 忙等待超时（毫秒） |
| cache_size | int | -2000 | 缓存大小 |
| recursive_triggers | bool | False | 递归触发器 |

## 信息查询类 Pragma

信息查询类 Pragma 用于获取数据库元信息，只能读取。

### table_info

获取表的列信息。

```python
info = dialect.get_pragma_info('table_info')
# 属性: requires_argument=True, argument_type=str

# SQL 示例
# PRAGMA table_info(users)
```

**返回列**：cid, name, type, notnull, dflt_value, pk

### index_list

获取表的索引列表。

```python
# SQL 示例
# PRAGMA index_list(users)
```

**返回列**：seq, name, unique, origin, partial

### database_list

获取所有数据库连接。

```python
# SQL 示例
# PRAGMA database_list
```

**返回列**：seq, name, file

### 其他信息查询类 Pragma

| Pragma | 参数 | 说明 |
|--------|------|------|
| table_xinfo | 表名 | 扩展表信息（包含隐藏列） |
| index_info | 索引名 | 索引列信息 |
| index_xinfo | 索引名 | 扩展索引信息 |
| foreign_key_list | 表名 | 外键列表 |
| collation_list | - | 排序规则列表 |
| function_list | - | SQL 函数列表 |
| table_list | - | 所有表列表（3.37.0+） |

## 调试类 Pragma

调试类 Pragma 用于数据库诊断和完整性检查。

### integrity_check

执行数据库完整性检查。

```python
info = dialect.get_pragma_info('integrity_check')
# 属性: read_only=True, value_type=list

# SQL 示例
# PRAGMA integrity_check
# 返回 'ok' 或错误信息列表
```

### quick_check

快速完整性检查（不检查 B-tree 结构）。

```python
# SQL 示例
# PRAGMA quick_check
```

### foreign_key_check

检查外键约束违规。

```python
# SQL 示例
# PRAGMA foreign_key_check
```

## 性能调优类 Pragma

性能调优类 Pragma 用于优化数据库性能。

### cache_size

设置数据库缓存大小。

```python
info = dialect.get_pragma_info('cache_size')
# 类型: int, 默认值: -2000（负数表示 KB）

# SQL 示例
# PRAGMA cache_size = -64000  -- 64MB 缓存
# PRAGMA cache_size = 2000    -- 2000 页
```

### mmap_size

设置内存映射 I/O 大小。

```python
# SQL 示例
# PRAGMA mmap_size = 268435456  -- 256MB
```

**版本要求**：SQLite 3.7.17+

### page_size

设置数据库页面大小（仅在建库前有效）。

```python
info = dialect.get_pragma_info('page_size')
# 允许值: [512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]
```

## WAL 类 Pragma

WAL（Write-Ahead Logging）相关的 Pragma。

### wal_checkpoint

执行 WAL 检查点。

```python
info = dialect.get_pragma_info('wal_checkpoint')
# 允许值: ['PASSIVE', 'FULL', 'RESTART', 'TRUNCATE']

# SQL 示例
# PRAGMA wal_checkpoint(PASSIVE)
# PRAGMA wal_checkpoint(FULL)
# PRAGMA wal_checkpoint(RESTART)
# PRAGMA wal_checkpoint(TRUNCATE)
```

### wal_autocheckpoint

设置自动检查点间隔。

```python
# SQL 示例
# PRAGMA wal_autocheckpoint = 1000  -- 每 1000 页自动检查点
```

## 编译时类 Pragma

获取 SQLite 编译时信息。

### compile_options

获取 SQLite 编译选项。

```python
# SQL 示例
# PRAGMA compile_options
# 返回编译时启用的选项列表，如: ENABLE_FTS5, ENABLE_JSON1
```

### encoding

获取数据库编码。

```python
# SQL 示例
# PRAGMA encoding
# 返回: 'UTF-8', 'UTF-16le', 或 'UTF-16be'
```

### user_version

获取或设置用户版本号。

```python
# SQL 示例
# PRAGMA user_version        -- 查询
# PRAGMA user_version = 1    -- 设置
```

## API 参考

### SQLitePragmaMixin

SQLiteDialect 通过 `SQLitePragmaMixin` 提供 Pragma 支持。

```python
class SQLitePragmaMixin:
    def get_pragma_info(self, name: str) -> Optional[PragmaInfo]:
        """获取 Pragma 信息"""
        
    def get_pragma_sql(self, name: str, argument: Any = None) -> str:
        """生成读取 Pragma 的 SQL"""
        
    def set_pragma_sql(self, name: str, value: Any, argument: Any = None) -> str:
        """生成设置 Pragma 的 SQL"""
        
    def is_pragma_available(self, name: str) -> bool:
        """检查 Pragma 是否可用"""
        
    def get_pragmas_by_category(self, category: PragmaCategory) -> List[PragmaInfo]:
        """按类别获取 Pragma 列表"""
        
    def get_all_pragma_infos(self) -> Dict[str, PragmaInfo]:
        """获取所有 Pragma 信息"""
```

### PragmaInfo

Pragma 信息数据类。

```python
@dataclass
class PragmaInfo:
    name: str                          # Pragma 名称
    category: PragmaCategory           # 类别
    description: str                   # 描述
    read_only: bool = False            # 是否只读
    min_version: Tuple[int, int, int]  # 最低版本
    value_type: type = str             # 值类型
    allowed_values: Optional[List[Any]] # 允许值列表
    default_value: Optional[Any]        # 默认值
    requires_argument: bool = False     # 是否需要参数
    argument_type: Optional[type]       # 参数类型
    documentation_url: Optional[str]    # 文档 URL
```

### PragmaCategory

Pragma 分类枚举。

```python
class PragmaCategory(Enum):
    CONFIGURATION = "configuration"  # 配置类
    INFORMATION = "information"      # 信息查询类
    DEBUG = "debug"                  # 调试类
    PERFORMANCE = "performance"      # 性能调优类
    WAL = "wal"                      # WAL 类
    COMPILE_TIME = "compile_time"    # 编译时类
```

## 参考资料

- [SQLite PRAGMA 文档](https://www.sqlite.org/pragma.html)
- [rhosocial-activerecord Pragma 源码](../../../src/rhosocial/activerecord/backend/impl/sqlite/pragma/)
