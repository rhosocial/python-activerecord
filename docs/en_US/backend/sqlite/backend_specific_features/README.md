# SQLite Specific Features

This section covers SQLite-specific features that differentiate it from other backends. The SQLite backend provides several unique capabilities through its pragma system, extension framework, and virtual table support.

## Pragma System

SQLite PRAGMA statements control database behavior, query metadata, and perform diagnostics. The backend provides a complete pragma system with version-aware availability checking.

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# Get pragma info
info = dialect.get_pragma_info('foreign_keys')

# Generate pragma SQL
sql = dialect.get_pragma_sql('journal_mode')  # PRAGMA journal_mode

# Set pragma value
sql = dialect.set_pragma_sql('journal_mode', 'WAL')  # PRAGMA journal_mode = WAL
```

Pragmas are organized into six categories: CONFIGURATION, INFORMATION, DEBUG, PERFORMANCE, WAL, and COMPILE_TIME.

For detailed documentation, see [Pragma System](../pragma.md).

## Extension Framework

SQLite supports extensions through built-in features, loadable modules, and virtual tables. The extension framework provides unified detection and version-aware feature checking.

```python
dialect = SQLiteDialect(version=(3, 35, 0))

# Detect all available extensions
extensions = dialect.detect_extensions()

# Check specific extension
if dialect.is_extension_available('fts5'):
    print("FTS5 available")

# Check extension feature
if dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    print("FTS5 trigram tokenizer available")
```

Supported extensions include FTS5 (full-text search), JSON1 (JSON functions), R-Tree (spatial indexing), and Geopoly (polygon geometry).

For detailed documentation, see [Extension Framework](../extension.md).

## Full-Text Search (FTS5)

FTS5 provides powerful full-text search capabilities including Boolean queries, phrase queries, NEAR queries, BM25 ranking, highlight/snippet extraction, and multiple tokenizers.

```python
# Create FTS5 virtual table
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    tokenizer='porter'
)

# Full-text search with ranking
match_sql, match_params = dialect.format_fts5_match_expression(
    'articles_fts', 'sqlite database'
)
rank_sql, _ = dialect.format_fts5_rank_expression('articles_fts')
```

For detailed documentation, see [FTS5 Full-Text Search](../fts5.md).

## Version Feature Support Matrix

Feature availability depends on the SQLite version at runtime:

| Feature | Minimum Version | Recommended Version |
|---------|-----------------|---------------------|
| Basic CTE | 3.8.3 | 3.8.3+ |
| Recursive CTE | 3.8.3 | 3.8.3+ |
| Window functions | 3.25.0 | 3.25.0+ |
| RENAME COLUMN | 3.25.0 | 3.25.0+ |
| RETURNING clause | 3.35.0 | 3.35.0+ |
| DROP COLUMN | 3.35.0 | 3.35.0+ |
| STRICT tables | 3.37.0 | 3.37.0+ |
| PRAGMA table_list | 3.37.0 | 3.37.0+ |
| JSON1 (built-in) | 3.38.0 | 3.38.0+ |
| FTS5 | 3.9.0 | 3.9.0+ |
| FTS5 trigram tokenizer | 3.34.0 | 3.34.0+ |
| R-Tree | 3.6.0 | 3.6.0+ |
| Geopoly | 3.26.0 | 3.26.0+ |

The backend automatically adjusts functionality based on the detected SQLite version.

## Known Limitations

| Limitation | Description |
|------------|-------------|
| No RIGHT/FULL JOIN | SQLite does not support RIGHT JOIN or FULL JOIN |
| Limited ALTER TABLE | No ALTER COLUMN; RENAME COLUMN requires 3.25.0+; DROP COLUMN requires 3.35.0+ |
| No TRUNCATE | Use `DELETE FROM` instead; VACUUM to reclaim space |
| No schema support | SQLite has no schema/namespace concept |
| No sequence support | Uses AUTOINCREMENT on INTEGER PRIMARY KEY instead |
| B-tree indexes only | No GIN, GiST, BRIN, or HASH index types |
| No concurrent index creation | No CONCURRENTLY support |
| No materialized views | Only standard views |
| Concurrency limits | Write operations acquire exclusive file locks |
| Not for network storage | Not recommended for NFS or similar |

## See Also

- [Pragma System](../pragma.md) — PRAGMA configuration and queries
- [Extension Framework](../extension.md) — Extension detection and management
- [FTS5 Full-Text Search](../fts5.md) — Full-text search functionality
- [Custom SQLite Build](../custom-sqlite-build.md) — Building custom SQLite with extensions

💡 *AI Prompt:* "How do I check which SQLite version is running and what features it supports?"
