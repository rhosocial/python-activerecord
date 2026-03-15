# Extension Framework

The SQLite extension framework provides unified extension detection and management, supporting built-in extensions, loadable extensions, and virtual table modules.

## Overview

SQLite supports several extension mechanisms:

- **Built-in Extensions**: Extensions compiled into SQLite (e.g., FTS5, JSON1)
- **Loadable Extensions**: Dynamically loaded extensions at runtime (.so/.dll files)
- **Virtual Table Modules**: Custom virtual table implementations (e.g., R-Tree, Geopoly)

The extension framework provides:

- **Extension Detection**: Check if extensions are available
- **Version Management**: Feature support based on SQLite version
- **Feature Queries**: Check if specific extension features are available
- **Unified Interface**: Consistent extension management API

## Extension Types

```python
from rhosocial.activerecord.backend.impl.sqlite.extension import ExtensionType

class ExtensionType(Enum):
    BUILTIN = "builtin"      # Built-in extension (compile-time)
    LOADABLE = "loadable"    # Loadable extension
    VTABLE = "vtable"        # Virtual table module
```

## Supported Extensions

### FTS5 (Full-Text Search)

Built-in full-text search engine since SQLite 3.9.0.

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    FTS5Extension,
    get_fts5_extension
)

fts5 = get_fts5_extension()

# Check availability
if fts5.is_available((3, 35, 0)):
    print("FTS5 available")

# Check features
if fts5.check_feature('trigram_tokenizer', (3, 34, 0)):
    print("FTS5 trigram tokenizer available")

# Get supported tokenizers
tokenizers = fts5.get_supported_tokenizers((3, 35, 0))
# ['unicode61', 'ascii', 'porter', 'trigram']
```

**Details**: [FTS5 Full-Text Search](fts5.md)

### JSON1 (JSON Functions)

Built-in JSON processing functions since SQLite 3.38.0.

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    JSON1Extension,
    get_json1_extension
)

json1 = get_json1_extension()

# Check availability (requires SQLite 3.38.0+)
if json1.is_available((3, 38, 0)):
    print("JSON1 available")

# Check features
if json1.check_feature('json_arrow_operators', (3, 38, 0)):
    print("JSON arrow operators available")
```

**Supported Operations**:

- `json_extract()`, `->`, `->>`
- `json_array()`, `json_object()`
- `json_each()`, `json_tree()`
- `json_patch()`, `json_remove()`
- `json_type()`, `json_valid()`

### R-Tree (Spatial Indexing)

Virtual table module for spatial data indexing.

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    RTreeExtension,
    get_rtree_extension
)

rtree = get_rtree_extension()

# Check availability (requires SQLite 3.6.0+)
if rtree.is_available((3, 35, 0)):
    print("R-Tree available")

# Check features
if rtree.check_feature('rtree_query', (3, 8, 5)):
    print("R-Tree range query available")
```

**Use Cases**:

- Geographic coordinate indexing
- Range queries
- Nearest neighbor search
- Spatial joins

### Geopoly (Polygon Geometry)

Virtual table module for polygon geometry operations.

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    GeopolyExtension,
    get_geopoly_extension
)

geopoly = get_geopoly_extension()

# Check availability (requires SQLite 3.26.0+)
if geopoly.is_available((3, 26, 0)):
    print("Geopoly available")
```

**Supported Operations**:

- `geopoly_contains()` - Point-in-polygon test
- `geopoly_within()` - Polygon containment
- `geopoly_overlap()` - Polygon overlap detection
- `geopoly_area()` - Area calculation

### FTS3/FTS4 (Deprecated)

Earlier versions of full-text search, superseded by FTS5.

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    FTS4Extension,
    get_fts4_extension
)

fts4 = get_fts4_extension()

# Note: FTS4 is deprecated
if fts4.deprecated:
    print(f"FTS4 is deprecated, recommend using {fts4.successor}")  # fts5
```

## Usage

### Detection via Dialect

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# Detect all extensions
extensions = dialect.detect_extensions()
for name, info in extensions.items():
    status = "available" if info.installed else "not available"
    deprecated = " (deprecated)" if info.deprecated else ""
    print(f"{name}: {status}{deprecated}")

# Check specific extension
if dialect.is_extension_available('fts5'):
    print("FTS5 available")

# Check extension feature
if dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    print("FTS5 trigram tokenizer available")

# Get extension info
info = dialect.get_extension_info('fts5')
print(f"Type: {info.extension_type}")
print(f"Min Version: {info.min_version}")
print(f"Features: {list(info.features.keys())}")
```

### Using Extension Classes Directly

```python
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    get_fts5_extension,
    get_json1_extension,
)

# Get FTS5 extension instance
fts5 = get_fts5_extension()

# Check version compatibility
sqlite_version = (3, 35, 0)
if fts5.is_available(sqlite_version):
    # Get extension info
    info = fts5.get_info(sqlite_version)
    print(f"Name: {info.name}")
    print(f"Installed: {info.installed}")
    
    # Check features
    features = ['full_text_search', 'bm25_ranking', 'trigram_tokenizer']
    for feature in features:
        if fts5.check_feature(feature, sqlite_version):
            print(f"✓ {feature}")
        else:
            min_ver = fts5.get_min_version_for_feature(feature)
            print(f"✗ {feature} (requires {min_ver})")
```

### Using Extension Registry

```python
from rhosocial.activerecord.backend.impl.sqlite.extension import (
    get_registry,
    reset_registry,
)

# Get global registry
registry = get_registry()

# Register custom extension
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

# Detect extensions
detected = registry.detect_extensions((3, 35, 0))

# Reset registry (mainly for testing)
reset_registry()
```

## Version Compatibility

The extension framework automatically handles version compatibility:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

# Different SQLite versions support different features
dialect_old = SQLiteDialect(version=(3, 8, 0))
dialect_new = SQLiteDialect(version=(3, 40, 0))

# FTS5 requires 3.9.0+
print(dialect_old.is_extension_available('fts5'))  # False
print(dialect_new.is_extension_available('fts5'))  # True

# JSON1 built-in requires 3.38.0+
print(dialect_old.is_extension_available('json1'))  # False
print(dialect_new.is_extension_available('json1'))  # True

# Trigram tokenizer requires 3.34.0+
dialect_mid = SQLiteDialect(version=(3, 33, 0))
dialect_recent = SQLiteDialect(version=(3, 34, 0))

print(dialect_mid.check_extension_feature('fts5', 'trigram_tokenizer'))  # False
print(dialect_recent.check_extension_feature('fts5', 'trigram_tokenizer'))  # True
```

## Extension Feature Lists

### FTS5 Features

| Feature | Min Version | Description |
|---------|-------------|-------------|
| full_text_search | 3.9.0 | Basic full-text search |
| bm25_ranking | 3.9.0 | BM25 ranking |
| highlight | 3.9.0 | highlight() function |
| snippet | 3.9.0 | snippet() function |
| offset | 3.9.0 | offset() function |
| porter_tokenizer | 3.9.0 | Porter stemmer tokenizer |
| unicode61_tokenizer | 3.9.0 | Unicode tokenizer |
| ascii_tokenizer | 3.9.0 | ASCII tokenizer |
| trigram_tokenizer | 3.34.0 | Trigram tokenizer |

### JSON1 Features

| Feature | Min Version | Description |
|---------|-------------|-------------|
| json_functions | 3.38.0 | JSON functions |
| json_array | 3.38.0 | json_array() |
| json_object | 3.38.0 | json_object() |
| json_extract | 3.38.0 | json_extract() |
| json_arrow_operators | 3.38.0 | ->, ->> operators |
| json_each | 3.38.0 | json_each() |
| json_tree | 3.38.0 | json_tree() |

### R-Tree Features

| Feature | Min Version | Description |
|---------|-------------|-------------|
| rtree_index | 3.6.0 | R-Tree index |
| rtree_query | 3.8.5 | Range query |
| rtree_integrity_check | 3.24.0 | Integrity check |
| rtree_auxiliary_functions | 3.25.0 | Auxiliary functions |

## API Reference

### SQLiteExtensionSupport

Dialect provides extension support through this protocol.

```python
class SQLiteExtensionSupport(Protocol):
    def detect_extensions(self) -> Dict[str, SQLiteExtensionInfo]:
        """Detect all available extensions"""
        
    def is_extension_available(self, name: str) -> bool:
        """Check if extension is available"""
        
    def get_extension_info(self, name: str) -> Optional[SQLiteExtensionInfo]:
        """Get extension information"""
        
    def check_extension_feature(self, ext_name: str, feature_name: str) -> bool:
        """Check if extension feature is available"""
```

### SQLiteExtensionInfo

Extension information dataclass.

```python
@dataclass
class SQLiteExtensionInfo:
    name: str                          # Extension name
    extension_type: ExtensionType      # Extension type
    installed: bool                    # Is installed
    version: Optional[str]             # Version number
    min_version: Tuple[int, int, int]  # Minimum SQLite version
    deprecated: bool                   # Is deprecated
    successor: Optional[str]           # Successor extension name
    description: Optional[str]         # Description
    features: Dict[str, Dict]          # Features list
    documentation_url: Optional[str]   # Documentation URL
```

### SQLiteExtensionBase

Extension base class for implementing custom extensions.

```python
class SQLiteExtensionBase(ABC):
    def is_available(self, version: Tuple[int, int, int]) -> bool:
        """Check if extension is available for specified version"""
        
    def get_info(self, version: Tuple[int, int, int]) -> SQLiteExtensionInfo:
        """Get extension information"""
        
    def check_feature(self, feature_name: str, version: Tuple[int, int, int]) -> bool:
        """Check if feature is available"""
        
    def get_supported_features(self, version: Tuple[int, int, int]) -> List[str]:
        """Get list of supported features"""
```

### SQLiteExtensionRegistry

Extension registry.

```python
class SQLiteExtensionRegistry:
    def register(self, extension: SQLiteExtensionBase) -> None:
        """Register extension"""
        
    def unregister(self, name: str) -> None:
        """Unregister extension"""
        
    def get_extension(self, name: str) -> Optional[SQLiteExtensionBase]:
        """Get registered extension"""
        
    def detect_extensions(self, version: Tuple[int, int, int]) -> Dict[str, SQLiteExtensionInfo]:
        """Detect all extensions"""
        
    def is_extension_available(self, name: str, version: Tuple[int, int, int]) -> bool:
        """Check if extension is available"""
        
    def check_extension_feature(self, ext_name: str, feature_name: str, version: Tuple[int, int, int]) -> bool:
        """Check extension feature"""
```

## References

- [SQLite Extension Documentation](https://www.sqlite.org/loadext.html)
- [FTS5 Extension](https://www.sqlite.org/fts5.html)
- [JSON1 Extension](https://www.sqlite.org/json1.html)
- [R-Tree Extension](https://www.sqlite.org/rtree.html)
- [Geopoly Extension](https://www.sqlite.org/geopoly.html)
