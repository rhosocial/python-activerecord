# Pragma System

SQLite PRAGMA statements are SQLite-specific configuration and query mechanisms used to control database behavior, query database state, and perform diagnostic operations. rhosocial-activerecord provides complete Pragma system support for the SQLite backend.

## Overview

The Pragma system provides:

- **Configuration Management**: Query and modify runtime database configuration
- **Information Queries**: Get metadata about database structure, indexes, foreign keys
- **Diagnostic Tools**: Perform integrity checks and debugging
- **Performance Tuning**: Optimize cache, memory mapping, and other performance parameters
- **Version Compatibility**: Automatic Pragma version compatibility checking

## Pragma Categories

Pragmas are organized into six categories:

| Category | Description | Read/Write | Examples |
|----------|-------------|------------|----------|
| CONFIGURATION | Configuration pragmas | Read/Write | foreign_keys, journal_mode |
| INFORMATION | Information query pragmas | Read-only | table_info, index_list |
| DEBUG | Debug pragmas | Read-only | integrity_check |
| PERFORMANCE | Performance tuning pragmas | Read/Write | cache_size, mmap_size |
| WAL | WAL-specific pragmas | Read/Write | wal_checkpoint |
| COMPILE_TIME | Compile-time pragmas | Read-only | compile_options |

## Usage

### Getting Pragma Information

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# Get single pragma info
info = dialect.get_pragma_info('foreign_keys')
print(f"Name: {info.name}")
print(f"Category: {info.category}")
print(f"Description: {info.description}")
print(f"Read-only: {info.read_only}")
print(f"Default value: {info.default_value}")
```

### Generating Pragma SQL

```python
# SQL to read pragma
sql = dialect.get_pragma_sql('journal_mode')
# Result: "PRAGMA journal_mode"

# Pragma query with argument
sql = dialect.get_pragma_sql('table_info', argument='users')
# Result: "PRAGMA table_info(users)"
```

### Setting Pragma SQL

```python
# SQL to set pragma value
sql = dialect.set_pragma_sql('foreign_keys', 1)
# Result: "PRAGMA foreign_keys = 1"

sql = dialect.set_pragma_sql('journal_mode', 'WAL')
# Result: "PRAGMA journal_mode = WAL"

# Attempting to set read-only pragma raises exception
try:
    sql = dialect.set_pragma_sql('table_info', 'users')  # Read-only pragma
except ValueError as e:
    print(f"Error: {e}")
```

### Querying by Category

```python
from rhosocial.activerecord.backend.impl.sqlite.pragma import PragmaCategory

# Get all configuration pragmas
config_pragmas = dialect.get_pragmas_by_category(PragmaCategory.CONFIGURATION)
for info in config_pragmas:
    print(f"{info.name}: {info.description}")

# Get all pragma information
all_pragmas = dialect.get_all_pragma_infos()
print(f"Total pragmas: {len(all_pragmas)}")
```

### Checking Availability

```python
# Check if pragma is available for current version
if dialect.is_pragma_available('table_list'):
    print("table_list pragma available (requires SQLite 3.37.0+)")
```

## Configuration Pragmas

Configuration pragmas control database runtime behavior and can be read and modified.

### foreign_keys

Control foreign key constraint checking.

```python
# Get info
info = dialect.get_pragma_info('foreign_keys')
# Properties: read_only=False, value_type=bool, default_value=False

# SQL examples
# PRAGMA foreign_keys          -- Query current state
# PRAGMA foreign_keys = 1      -- Enable foreign keys
# PRAGMA foreign_keys = 0      -- Disable foreign keys
```

**Version Required**: SQLite 3.6.19+

### journal_mode

Control database journaling mode.

```python
info = dialect.get_pragma_info('journal_mode')
# Allowed values: ['DELETE', 'TRUNCATE', 'PERSIST', 'MEMORY', 'WAL', 'OFF']
# Default: 'DELETE'

# SQL examples
# PRAGMA journal_mode          -- Query current mode
# PRAGMA journal_mode = WAL    -- Set to WAL mode
```

**Version Required**: SQLite 3.0.0+

### synchronous

Control how data is synced to disk.

```python
info = dialect.get_pragma_info('synchronous')
# Allowed values: ['OFF', 'NORMAL', 'FULL', 'EXTRA']
# Default: 'FULL'

# SQL examples
# PRAGMA synchronous = NORMAL  -- Recommended for WAL mode
```

**Version Required**: SQLite 3.0.0+

### Other Configuration Pragmas

| Pragma | Type | Default | Description |
|--------|------|---------|-------------|
| locking_mode | str | NORMAL | Locking mode |
| temp_store | str | DEFAULT | Temporary storage location |
| auto_vacuum | str | NONE | Auto-vacuum mode |
| busy_timeout | int | 0 | Busy timeout (milliseconds) |
| cache_size | int | -2000 | Cache size |
| recursive_triggers | bool | False | Recursive triggers |

## Information Query Pragmas

Information pragmas retrieve database metadata and are read-only.

### table_info

Get table column information.

```python
info = dialect.get_pragma_info('table_info')
# Properties: requires_argument=True, argument_type=str

# SQL example
# PRAGMA table_info(users)
```

**Returns**: cid, name, type, notnull, dflt_value, pk

### index_list

Get table index list.

```python
# SQL example
# PRAGMA index_list(users)
```

**Returns**: seq, name, unique, origin, partial

### database_list

Get all database connections.

```python
# SQL example
# PRAGMA database_list
```

**Returns**: seq, name, file

### Other Information Pragmas

| Pragma | Argument | Description |
|--------|----------|-------------|
| table_xinfo | table name | Extended table info (includes hidden columns) |
| index_info | index name | Index column information |
| index_xinfo | index name | Extended index information |
| foreign_key_list | table name | Foreign key list |
| collation_list | - | Collation sequence list |
| function_list | - | SQL function list |
| table_list | - | All tables list (3.37.0+) |

## Debug Pragmas

Debug pragmas are used for database diagnostics and integrity checks.

### integrity_check

Perform database integrity check.

```python
info = dialect.get_pragma_info('integrity_check')
# Properties: read_only=True, value_type=list

# SQL example
# PRAGMA integrity_check
# Returns 'ok' or list of errors
```

### quick_check

Quick integrity check (doesn't check B-tree structure).

```python
# SQL example
# PRAGMA quick_check
```

### foreign_key_check

Check foreign key constraint violations.

```python
# SQL example
# PRAGMA foreign_key_check
```

## Performance Tuning Pragmas

Performance pragmas optimize database performance.

### cache_size

Set database cache size.

```python
info = dialect.get_pragma_info('cache_size')
# Type: int, Default: -2000 (negative means KB)

# SQL examples
# PRAGMA cache_size = -64000  -- 64MB cache
# PRAGMA cache_size = 2000    -- 2000 pages
```

### mmap_size

Set memory-mapped I/O size.

```python
# SQL example
# PRAGMA mmap_size = 268435456  -- 256MB
```

**Version Required**: SQLite 3.7.17+

### page_size

Set database page size (only effective before database creation).

```python
info = dialect.get_pragma_info('page_size')
# Allowed values: [512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]
```

## WAL Pragmas

WAL (Write-Ahead Logging) related pragmas.

### wal_checkpoint

Execute WAL checkpoint.

```python
info = dialect.get_pragma_info('wal_checkpoint')
# Allowed values: ['PASSIVE', 'FULL', 'RESTART', 'TRUNCATE']

# SQL examples
# PRAGMA wal_checkpoint(PASSIVE)
# PRAGMA wal_checkpoint(FULL)
# PRAGMA wal_checkpoint(RESTART)
# PRAGMA wal_checkpoint(TRUNCATE)
```

### wal_autocheckpoint

Set auto-checkpoint interval.

```python
# SQL example
# PRAGMA wal_autocheckpoint = 1000  -- Auto-checkpoint every 1000 pages
```

## Compile-Time Pragmas

Get SQLite compile-time information.

### compile_options

Get SQLite compile options.

```python
# SQL example
# PRAGMA compile_options
# Returns list of compile-time enabled options like: ENABLE_FTS5, ENABLE_JSON1
```

### encoding

Get database encoding.

```python
# SQL example
# PRAGMA encoding
# Returns: 'UTF-8', 'UTF-16le', or 'UTF-16be'
```

### user_version

Get or set user version number.

```python
# SQL examples
# PRAGMA user_version        -- Query
# PRAGMA user_version = 1    -- Set
```

## API Reference

### SQLitePragmaMixin

SQLiteDialect provides Pragma support through `SQLitePragmaMixin`.

```python
class SQLitePragmaMixin:
    def get_pragma_info(self, name: str) -> Optional[PragmaInfo]:
        """Get pragma information"""
        
    def get_pragma_sql(self, name: str, argument: Any = None) -> str:
        """Generate SQL to read pragma"""
        
    def set_pragma_sql(self, name: str, value: Any, argument: Any = None) -> str:
        """Generate SQL to set pragma"""
        
    def is_pragma_available(self, name: str) -> bool:
        """Check if pragma is available"""
        
    def get_pragmas_by_category(self, category: PragmaCategory) -> List[PragmaInfo]:
        """Get pragmas by category"""
        
    def get_all_pragma_infos(self) -> Dict[str, PragmaInfo]:
        """Get all pragma information"""
```

### PragmaInfo

Pragma information dataclass.

```python
@dataclass
class PragmaInfo:
    name: str                          # Pragma name
    category: PragmaCategory           # Category
    description: str                   # Description
    read_only: bool = False            # Is read-only
    min_version: Tuple[int, int, int]  # Minimum version
    value_type: type = str             # Value type
    allowed_values: Optional[List[Any]] # Allowed values
    default_value: Optional[Any]        # Default value
    requires_argument: bool = False     # Requires argument
    argument_type: Optional[type]       # Argument type
    documentation_url: Optional[str]    # Documentation URL
```

### PragmaCategory

Pragma category enumeration.

```python
class PragmaCategory(Enum):
    CONFIGURATION = "configuration"  # Configuration pragmas
    INFORMATION = "information"      # Information query pragmas
    DEBUG = "debug"                  # Debug pragmas
    PERFORMANCE = "performance"      # Performance tuning pragmas
    WAL = "wal"                      # WAL pragmas
    COMPILE_TIME = "compile_time"    # Compile-time pragmas
```

## References

- [SQLite PRAGMA Documentation](https://www.sqlite.org/pragma.html)
- [rhosocial-activerecord Pragma Source](../../../src/rhosocial/activerecord/backend/impl/sqlite/pragma/)
