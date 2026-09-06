# SQLite 特有功能

本节介绍 SQLite 特有的功能，这些功能使其与其他后端区分开来。SQLite 后端通过其 pragma 系统、扩展框架和虚拟表支持提供了多项独特功能。

## Pragma 系统

SQLite PRAGMA 语句控制数据库行为、查询元数据和执行诊断。后端提供了一个完整的 pragma 系统，具有版本感知的可用性检查。

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# 获取 pragma 信息
info = dialect.get_pragma_info('foreign_keys')

# 生成 pragma SQL
sql = dialect.get_pragma_sql('journal_mode')  # PRAGMA journal_mode

# 设置 pragma 值
sql = dialect.set_pragma_sql('journal_mode', 'WAL')  # PRAGMA journal_mode = WAL
```

Pragma 分为六个类别：CONFIGURATION、INFORMATION、DEBUG、PERFORMANCE、WAL 和 COMPILE_TIME。

详细文档请参阅 [Pragma 系统](../pragma.md)。

## 扩展框架

SQLite 通过内置功能、可加载模块和虚拟表支持扩展。扩展框架提供统一的检测和版本感知功能检查。

```python
dialect = SQLiteDialect(version=(3, 35, 0))

# 检测所有可用扩展
extensions = dialect.detect_extensions()

# 检查特定扩展
if dialect.is_extension_available('fts5'):
    print("FTS5 available")

# 检查扩展功能
if dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    print("FTS5 trigram tokenizer available")
```

支持的扩展包括 FTS5（全文搜索）、JSON1（JSON 函数）、R-Tree（空间索引）和 Geopoly（多边形几何）。

详细文档请参阅 [扩展框架](../extension.md)。

## 全文搜索 (FTS5)

FTS5 提供强大的全文搜索功能，包括布尔查询、短语查询、NEAR 查询、BM25 排名、高亮/片段提取和多种分词器。

```python
# 创建 FTS5 虚拟表
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    tokenizer='porter'
)

# 带排名的全文搜索
match_sql, match_params = dialect.format_fts5_match_expression(
    'articles_fts', 'sqlite database'
)
rank_sql, _ = dialect.format_fts5_rank_expression('articles_fts')
```

详细文档请参阅 [FTS5 全文搜索](../fts5.md)。

## 版本功能支持矩阵

功能可用性取决于运行时的 SQLite 版本：

| 功能 | 最低版本 | 推荐版本 |
|------|---------|---------|
| 基本 CTE | 3.8.3 | 3.8.3+ |
| 递归 CTE | 3.8.3 | 3.8.3+ |
| 窗口函数 | 3.25.0 | 3.25.0+ |
| RENAME COLUMN | 3.25.0 | 3.25.0+ |
| RETURNING 子句 | 3.35.0 | 3.35.0+ |
| DROP COLUMN | 3.35.0 | 3.35.0+ |
| STRICT 表 | 3.37.0 | 3.37.0+ |
| PRAGMA table_list | 3.37.0 | 3.37.0+ |
| JSON1（内置） | 3.38.0 | 3.38.0+ |
| FTS5 | 3.9.0 | 3.9.0+ |
| FTS5 trigram 分词器 | 3.34.0 | 3.34.0+ |
| R-Tree | 3.6.0 | 3.6.0+ |
| Geopoly | 3.26.0 | 3.26.0+ |

后端会根据检测到的 SQLite 版本自动调整功能。

## 已知限制

| 限制 | 描述 |
|------|------|
| 不支持 RIGHT/FULL JOIN | SQLite 不支持 RIGHT JOIN 或 FULL JOIN |
| 有限的 ALTER TABLE | 不能 ALTER COLUMN；RENAME COLUMN 需要 3.25.0+；DROP COLUMN 需要 3.35.0+ |
| 不支持 TRUNCATE | 使用 `DELETE FROM` 代替；使用 VACUUM 回收空间 |
| 不支持 schema | SQLite 没有 schema/命名空间概念 |
| 不支持序列 | 改为在 INTEGER PRIMARY KEY 上使用 AUTOINCREMENT |
| 仅 B-tree 索引 | 不支持 GIN、GiST、BRIN 或 HASH 索引类型 |
| 不支持并发索引创建 | 不支持 CONCURRENTLY |
| 不支持物化视图 | 仅支持标准视图 |
| 并发限制 | 写操作获取独占文件锁 |
| 不适合网络存储 | 不建议用于 NFS 或类似存储 |

## 另请参阅

- [Pragma 系统](../pragma.md) — PRAGMA 配置和查询
- [扩展框架](../extension.md) — 扩展检测和管理
- [FTS5 全文搜索](../fts5.md) — 全文搜索功能
- [自定义 SQLite 构建](../custom-sqlite-build.md) — 构建带有扩展的自定义 SQLite

💡 *AI 提示*："如何检查正在运行的 SQLite 版本及其支持的功能？"
