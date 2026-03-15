# 扩展框架

SQLite 扩展框架提供了统一的扩展检测和管理机制，支持内置扩展、可加载扩展和虚拟表模块。

## 概述

SQLite 支持多种扩展机制：

- **内置扩展**：编译时内置的扩展（如 FTS5、JSON1）
- **可加载扩展**：运行时动态加载的扩展（.so/.dll 文件）
- **虚拟表模块**：自定义虚拟表实现（如 R-Tree、Geopoly）

扩展框架提供以下功能：

- **扩展检测**：检测扩展是否可用
- **版本管理**：基于 SQLite 版本的特性支持
- **特性查询**：检查扩展的特定特性是否可用
- **统一接口**：一致的扩展管理 API

## 扩展类型

```python
from rhosocial.activerecord.backend.impl.sqlite.extension import ExtensionType

class ExtensionType(Enum):
    BUILTIN = "builtin"      # 内置扩展（编译时）
    LOADABLE = "loadable"    # 可加载扩展
    VTABLE = "vtable"        # 虚拟表模块
```

## 支持的扩展

### FTS5（全文搜索）

SQLite 3.9.0+ 内置的全文搜索引擎。

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    FTS5Extension,
    get_fts5_extension
)

fts5 = get_fts5_extension()

# 检查可用性
if fts5.is_available((3, 35, 0)):
    print("FTS5 可用")

# 检查特性
if fts5.check_feature('trigram_tokenizer', (3, 34, 0)):
    print("FTS5 trigram 分词器可用")

# 获取支持的 tokenizer
tokenizers = fts5.get_supported_tokenizers((3, 35, 0))
# ['unicode61', 'ascii', 'porter', 'trigram']
```

**详细信息**：[FTS5 全文搜索](fts5.md)

### JSON1（JSON 函数）

SQLite 3.38.0+ 内置的 JSON 处理函数。

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    JSON1Extension,
    get_json1_extension
)

json1 = get_json1_extension()

# 检查可用性（需要 SQLite 3.38.0+）
if json1.is_available((3, 38, 0)):
    print("JSON1 可用")

# 检查特性
if json1.check_feature('json_arrow_operators', (3, 38, 0)):
    print("JSON 箭头操作符可用")
```

**支持的操作**：

- `json_extract()`, `->`, `->>`
- `json_array()`, `json_object()`
- `json_each()`, `json_tree()`
- `json_patch()`, `json_remove()`
- `json_type()`, `json_valid()`

### R-Tree（空间索引）

用于空间数据索引的虚拟表模块。

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    RTreeExtension,
    get_rtree_extension
)

rtree = get_rtree_extension()

# 检查可用性（需要 SQLite 3.6.0+）
if rtree.is_available((3, 35, 0)):
    print("R-Tree 可用")

# 检查特性
if rtree.check_feature('rtree_query', (3, 8, 5)):
    print("R-Tree 范围查询可用")
```

**用途**：

- 地理坐标索引
- 范围查询
- 最近邻搜索
- 空间连接

### Geopoly（多边形几何）

用于多边形几何操作的虚拟表模块。

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    GeopolyExtension,
    get_geopoly_extension
)

geopoly = get_geopoly_extension()

# 检查可用性（需要 SQLite 3.26.0+）
if geopoly.is_available((3, 26, 0)):
    print("Geopoly 可用")
```

**支持的操作**：

- `geopoly_contains()` - 点在多边形内判断
- `geopoly_within()` - 多边形包含关系
- `geopoly_overlap()` - 多边形重叠检测
- `geopoly_area()` - 面积计算

### FTS3/FTS4（已弃用）

早期版本的全文搜索引擎，已被 FTS5 取代。

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    FTS4Extension,
    get_fts4_extension
)

fts4 = get_fts4_extension()

# 注意：FTS4 已弃用
if fts4.deprecated:
    print(f"FTS4 已弃用，推荐使用 {fts4.successor}")  # fts5
```

## 使用方式

### 通过 Dialect 检测

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# 检测所有扩展
extensions = dialect.detect_extensions()
for name, info in extensions.items():
    status = "可用" if info.installed else "不可用"
    deprecated = " (已弃用)" if info.deprecated else ""
    print(f"{name}: {status}{deprecated}")

# 检查特定扩展
if dialect.is_extension_available('fts5'):
    print("FTS5 可用")

# 检查扩展特性
if dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    print("FTS5 trigram 分词器可用")

# 获取扩展信息
info = dialect.get_extension_info('fts5')
print(f"类型: {info.extension_type}")
print(f"最低版本: {info.min_version}")
print(f"特性: {list(info.features.keys())}")
```

### 直接使用扩展类

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    get_fts5_extension,
    get_json1_extension,
)

# 获取 FTS5 扩展实例
fts5 = get_fts5_extension()

# 检查版本兼容性
sqlite_version = (3, 35, 0)
if fts5.is_available(sqlite_version):
    # 获取扩展信息
    info = fts5.get_info(sqlite_version)
    print(f"扩展名: {info.name}")
    print(f"已安装: {info.installed}")
    
    # 检查特性
    features = ['full_text_search', 'bm25_ranking', 'trigram_tokenizer']
    for feature in features:
        if fts5.check_feature(feature, sqlite_version):
            print(f"✓ {feature}")
        else:
            min_ver = fts5.get_min_version_for_feature(feature)
            print(f"✗ {feature} (需要 {min_ver})")
```

### 使用扩展注册表

```python
from rhosocial.activerecord.backend.impl.sqlite.extension import (
    get_registry,
    reset_registry,
)

# 获取全局注册表
registry = get_registry()

# 注册自定义扩展
from rhosocial.activerecord.backend.impl.sqlite.extension import SQLiteExtensionBase

class MyExtension(SQLiteExtensionBase):
    def __init__(self):
        super().__init__(
            name='my_extension',
            extension_type=ExtensionType.LOADABLE,
            min_version=(3, 0, 0),
            description='My custom extension',
        )

registry.register(MyExtension())

# 检测扩展
detected = registry.detect_extensions((3, 35, 0))

# 重置注册表（主要用于测试）
reset_registry()
```

## 版本兼容性

扩展框架自动处理版本兼容性：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

# 不同版本的 SQLite 支持不同特性
dialect_old = SQLiteDialect(version=(3, 8, 0))
dialect_new = SQLiteDialect(version=(3, 40, 0))

# FTS5 需要 3.9.0+
print(dialect_old.is_extension_available('fts5'))  # False
print(dialect_new.is_extension_available('fts5'))  # True

# JSON1 内置需要 3.38.0+
print(dialect_old.is_extension_available('json1'))  # False
print(dialect_new.is_extension_available('json1'))  # True

# Trigram tokenizer 需要 3.34.0+
dialect_mid = SQLiteDialect(version=(3, 33, 0))
dialect_recent = SQLiteDialect(version=(3, 34, 0))

print(dialect_mid.check_extension_feature('fts5', 'trigram_tokenizer'))  # False
print(dialect_recent.check_extension_feature('fts5', 'trigram_tokenizer'))  # True
```

## 扩展特性列表

### FTS5 特性

| 特性 | 最低版本 | 说明 |
|------|----------|------|
| full_text_search | 3.9.0 | 基础全文搜索 |
| bm25_ranking | 3.9.0 | BM25 排序 |
| highlight | 3.9.0 | 高亮函数 |
| snippet | 3.9.0 | 摘要函数 |
| offset | 3.9.0 | 偏移函数 |
| porter_tokenizer | 3.9.0 | Porter 词干分词器 |
| unicode61_tokenizer | 3.9.0 | Unicode 分词器 |
| ascii_tokenizer | 3.9.0 | ASCII 分词器 |
| trigram_tokenizer | 3.34.0 | Trigram 分词器 |

### JSON1 特性

| 特性 | 最低版本 | 说明 |
|------|----------|------|
| json_functions | 3.38.0 | JSON 函数 |
| json_array | 3.38.0 | json_array() |
| json_object | 3.38.0 | json_object() |
| json_extract | 3.38.0 | json_extract() |
| json_arrow_operators | 3.38.0 | ->, ->> 操作符 |
| json_each | 3.38.0 | json_each() |
| json_tree | 3.38.0 | json_tree() |

### R-Tree 特性

| 特性 | 最低版本 | 说明 |
|------|----------|------|
| rtree_index | 3.6.0 | R-Tree 索引 |
| rtree_query | 3.8.5 | 范围查询 |
| rtree_integrity_check | 3.24.0 | 完整性检查 |
| rtree_auxiliary_functions | 3.25.0 | 辅助函数 |

## API 参考

### SQLiteExtensionSupport

Dialect 通过此协议提供扩展支持。

```python
class SQLiteExtensionSupport(Protocol):
    def detect_extensions(self) -> Dict[str, SQLiteExtensionInfo]:
        """检测所有可用扩展"""
        
    def is_extension_available(self, name: str) -> bool:
        """检查扩展是否可用"""
        
    def get_extension_info(self, name: str) -> Optional[SQLiteExtensionInfo]:
        """获取扩展信息"""
        
    def check_extension_feature(self, ext_name: str, feature_name: str) -> bool:
        """检查扩展特性是否可用"""
```

### SQLiteExtensionInfo

扩展信息数据类。

```python
@dataclass
class SQLiteExtensionInfo:
    name: str                          # 扩展名
    extension_type: ExtensionType      # 扩展类型
    installed: bool                    # 是否已安装
    version: Optional[str]             # 版本号
    min_version: Tuple[int, int, int]  # 最低 SQLite 版本
    deprecated: bool                   # 是否已弃用
    successor: Optional[str]           # 后继扩展名
    description: Optional[str]         # 描述
    features: Dict[str, Dict]          # 特性列表
    documentation_url: Optional[str]   # 文档 URL
```

### SQLiteExtensionBase

扩展基类，用于实现自定义扩展。

```python
class SQLiteExtensionBase(ABC):
    def is_available(self, version: Tuple[int, int, int]) -> bool:
        """检查扩展在指定版本是否可用"""
        
    def get_info(self, version: Tuple[int, int, int]) -> SQLiteExtensionInfo:
        """获取扩展信息"""
        
    def check_feature(self, feature_name: str, version: Tuple[int, int, int]) -> bool:
        """检查特性是否可用"""
        
    def get_supported_features(self, version: Tuple[int, int, int]) -> List[str]:
        """获取支持的特性列表"""
```

### SQLiteExtensionRegistry

扩展注册表。

```python
class SQLiteExtensionRegistry:
    def register(self, extension: SQLiteExtensionBase) -> None:
        """注册扩展"""
        
    def unregister(self, name: str) -> None:
        """注销扩展"""
        
    def get_extension(self, name: str) -> Optional[SQLiteExtensionBase]:
        """获取已注册的扩展"""
        
    def detect_extensions(self, version: Tuple[int, int, int]) -> Dict[str, SQLiteExtensionInfo]:
        """检测所有扩展"""
        
    def is_extension_available(self, name: str, version: Tuple[int, int, int]) -> bool:
        """检查扩展是否可用"""
        
    def check_extension_feature(self, ext_name: str, feature_name: str, version: Tuple[int, int, int]) -> bool:
        """检查扩展特性"""
```

## 参考资料

- [SQLite 扩展文档](https://www.sqlite.org/loadext.html)
- [FTS5 扩展](https://www.sqlite.org/fts5.html)
- [JSON1 扩展](https://www.sqlite.org/json1.html)
- [R-Tree 扩展](https://www.sqlite.org/rtree.html)
- [Geopoly 扩展](https://www.sqlite.org/geopoly.html)
