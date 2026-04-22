# FTS5 全文搜索

FTS5（Full-Text Search version 5）是 SQLite 的全文搜索引擎，提供了强大的文本搜索能力。rhosocial-activerecord 为 SQLite 后端提供了完整的 FTS5 支持。

## 概述

FTS5 特性：

- **全文搜索**：快速文本搜索，支持布尔查询、短语查询、NEAR 查询
- **BM25 排序**：基于相关性的结果排序
- **高亮和摘要**：搜索结果高亮和摘要提取
- **多种分词器**：支持 unicode61、ascii、porter、trigram 等分词器
- **列权重**：支持为不同列设置搜索权重
- **外部内容**：支持与普通表关联的外部内容模式

**版本要求**：SQLite 3.9.0+

## 版本兼容性检查

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# 检查 FTS5 支持
if dialect.supports_fts5():
    print("FTS5 可用")

# 检查特定功能
if dialect.supports_fts5_bm25():
    print("BM25 排序可用")

if dialect.supports_fts5_highlight():
    print("highlight() 函数可用")

# 检查分词器
tokenizers = dialect.get_supported_fts5_tokenizers()
print(f"支持的 tokenizer: {tokenizers}")
# ['unicode61', 'ascii', 'porter', 'trigram'] (需要 3.34.0+)
```

## 创建 FTS5 虚拟表

### 基本创建

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# 创建基本 FTS5 表
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content', 'author']
)
# 结果: CREATE VIRTUAL TABLE "articles_fts" USING fts5("title", "content", "author")

# 执行
backend.execute(sql, params)
```

### 使用分词器

```python
# 使用 Porter 词干分词器（支持词形还原）
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    tokenizer='porter'
)
# 结果: CREATE VIRTUAL TABLE "articles_fts" USING fts5("title", "content", tokenize='porter')

# 使用 unicode61 分词器并配置选项
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    tokenizer='unicode61',
    tokenizer_options={'remove_diacritics': 1}
)
# 结果: CREATE VIRTUAL TABLE ... tokenize='unicode61 remove_diacritics 1'
```

### 可用的分词器

| 分词器 | 版本要求 | 说明 |
|--------|----------|------|
| unicode61 | 3.9.0 | 默认分词器，支持 Unicode |
| ascii | 3.9.0 | 简单 ASCII 分词器 |
| porter | 3.9.0 | Porter 词干分词器（词形还原） |
| trigram | 3.34.0 | Trigram 分词器（支持子字符串搜索） |

```python
# 检查分词器可用性
if dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    sql, params = dialect.format_fts5_create_virtual_table(
        table_name='articles_fts',
        columns=['content'],
        tokenizer='trigram'
    )
```

### 前缀索引

```python
# 启用前缀索引（支持前缀搜索）
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    prefix=[2, 3]  # 支持 2 字符和 3 字符前缀
)
# 结果: CREATE VIRTUAL TABLE ... prefix='2 3'
```

### 外部内容模式

```python
# 创建与普通表关联的 FTS5 表
# 首先创建普通表
backend.execute("""
    CREATE TABLE articles (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        author TEXT
    )
""")

# 创建关联的 FTS5 表
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    content='articles',        # 内容表
    content_rowid='id'         # 行 ID 列
)
# 结果: CREATE VIRTUAL TABLE "articles_fts" USING fts5(
#     "title", "content", content='articles', content_rowid='id'
# )
```

## 全文搜索查询

### 基本 MATCH 查询

```python
# 生成 MATCH 表达式
sql, params = dialect.format_fts5_match_expression(
    table_name='articles_fts',
    query='sqlite database'
)
# SQL: "articles_fts" MATCH ?
# params: ('sqlite database',)

# 完整查询
query_sql = f"""
    SELECT * FROM articles_fts 
    WHERE {sql}
    ORDER BY bm25(articles_fts)
"""
results = backend.fetch_all(query_sql, params)
```

### 列限定搜索

```python
# 只搜索 title 列
sql, params = dialect.format_fts5_match_expression(
    table_name='articles_fts',
    query='python',
    columns=['title']
)
# params: ('{title:} python',)

# 搜索多个列
sql, params = dialect.format_fts5_match_expression(
    table_name='articles_fts',
    query='python',
    columns=['title', 'content']
)
# params: ('{title: OR content:} python',)
```

### 否定搜索

```python
# NOT MATCH（排除匹配结果）
sql, params = dialect.format_fts5_match_expression(
    table_name='articles_fts',
    query='python',
    negate=True
)
# SQL: "articles_fts" NOT MATCH ?
```

### 查询语法

FTS5 支持丰富的查询语法：

```python
# 布尔查询
query = 'python AND database'     # 同时包含
query = 'python OR database'      # 包含任一
query = 'python NOT database'     # 包含 python 但不包含 database

# 短语查询
query = '"sqlite database"'       # 精确短语

# NEAR 查询
query = 'python NEAR database'    # 两个词相邻
query = 'python NEAR/5 database'  # 两个词在 5 个词范围内

# 前缀查询
query = 'sql*'                    # 以 sql 开头

# 列限定
query = 'title:python'            # 只在 title 列搜索
query = 'title, content:python'   # 在多个列搜索
```

## 结果排序（BM25）

### 基本排序

```python
# 生成 BM25 排序表达式
sql, params = dialect.format_fts5_rank_expression(
    table_name='articles_fts'
)
# 结果: bm25("articles_fts")

# 在查询中使用
query_sql = f"""
    SELECT *, {sql} as rank
    FROM articles_fts
    WHERE "articles_fts" MATCH ?
    ORDER BY rank
"""
```

### 带权重的排序

```python
# 为不同列设置权重
sql, params = dialect.format_fts5_rank_expression(
    table_name='articles_fts',
    weights=[10.0, 1.0]  # title 权重 10，content 权重 1
)
# 结果: bm25("articles_fts", 10.0, 1.0)
```

### 自定义 BM25 参数

```python
# 自定义 k1 和 b 参数
sql, params = dialect.format_fts5_rank_expression(
    table_name='articles_fts',
    bm25_params={'k1': 1.5, 'b': 0.75}
)
# 结果: bm25("articles_fts", 'k1', 1.5, 'b', 0.75)

# 同时使用权重和 BM25 参数
sql, params = dialect.format_fts5_rank_expression(
    table_name='articles_fts',
    weights=[10.0, 1.0],
    bm25_params={'k1': 1.2}
)
# 结果: bm25("articles_fts", 10.0, 1.0, 'k1', 1.2)
```

## 高亮和摘要

### 高亮匹配词

```python
# 生成高亮表达式
sql, params = dialect.format_fts5_highlight_expression(
    table_name='articles_fts',
    column='content',
    query='python',
    prefix_marker='<mark>',
    suffix_marker='</mark>'
)
# SQL: highlight("articles_fts", "content", ?, ?)
# params: ('<mark>', '</mark>')

# 在查询中使用
query_sql = f"""
    SELECT title, {sql} as highlighted_content
    FROM articles_fts
    WHERE "articles_fts" MATCH ?
"""
```

### 生成摘要

```python
# 生成摘要表达式
sql, params = dialect.format_fts5_snippet_expression(
    table_name='articles_fts',
    column='content',
    query='python',
    prefix_marker='<b>',
    suffix_marker='</b>',
    context_tokens=15,
    ellipsis='...'
)
# SQL: snippet("articles_fts", "content", ?, ?, ?, ?)
# params: ('<b>', '</b>', '...', 15)
```

## 删除 FTS5 表

```python
# 删除 FTS5 虚拟表
sql, params = dialect.format_fts5_drop_virtual_table(
    table_name='articles_fts'
)
# 结果: DROP TABLE "articles_fts"

# 带 IF EXISTS
sql, params = dialect.format_fts5_drop_virtual_table(
    table_name='articles_fts',
    if_exists=True
)
# 结果: DROP TABLE IF EXISTS "articles_fts"
```

## 完整示例

### 创建文章搜索系统

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteDialect
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# 创建后端
backend = SQLiteBackend(database=":memory:")
backend.connect()

dialect = backend.dialect

# 检查 FTS5 支持
if not dialect.supports_fts5():
    raise RuntimeError("FTS5 not supported")

# 创建文章表
backend.execute("""
    CREATE TABLE articles (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        author TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# 创建 FTS5 虚拟表
fts_sql, _ = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    tokenizer='porter',
    content='articles',
    content_rowid='id'
)
backend.execute(fts_sql)

# 插入测试数据
articles = [
    ('SQLite Tutorial', 'SQLite is a powerful embedded database for Python applications', 'Alice'),
    ('Python Programming', 'Learn Python from basics to advanced topics', 'Bob'),
    ('Database Design', 'Best practices for database schema design with SQLite', 'Alice'),
]

insert_sql = "INSERT INTO articles (title, content, author) VALUES (?, ?, ?)"
insert_opts = ExecutionOptions(stmt_type=StatementType.INSERT)
for title, content, author in articles:
    backend.execute(insert_sql, (title, content, author), options=insert_opts)

# 同步 FTS 索引
backend.execute("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')")

# 全文搜索
match_sql, match_params = dialect.format_fts5_match_expression(
    'articles_fts',
    'SQLite database'
)

rank_sql, _ = dialect.format_fts5_rank_expression('articles_fts')

query_sql = f"""
    SELECT articles.id, articles.title, articles.content, {rank_sql} as score
    FROM articles
    JOIN articles_fts ON articles.id = articles_fts.rowid
    WHERE {match_sql}
    ORDER BY score
"""

results = backend.fetch_all(query_sql, match_params)
for row in results:
    print(f"ID: {row['id']}, Title: {row['title']}, Score: {row['score']}")

# 带高亮的搜索
highlight_sql, highlight_params = dialect.format_fts5_highlight_expression(
    'articles_fts',
    'content',
    'SQLite',
    prefix_marker='**',
    suffix_marker='**'
)

query_sql = f"""
    SELECT articles.title, {highlight_sql} as highlighted
    FROM articles
    JOIN articles_fts ON articles.id = articles_fts.rowid
    WHERE "articles_fts" MATCH ?
"""

results = backend.fetch_all(query_sql, ('SQLite',))
for row in results:
    print(f"Title: {row['title']}")
    print(f"Content: {row['highlighted']}")
    print()

# 清理
backend.disconnect()
```

### 使用 Trigram 分词器

```python
# Trigram 分词器支持子字符串搜索
if dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    # 创建使用 trigram 的 FTS5 表
    sql, _ = dialect.format_fts5_create_virtual_table(
        'products_fts',
        ['name', 'description'],
        tokenizer='trigram'
    )
    backend.execute(sql)
    
    # 插入数据
    backend.execute("INSERT INTO products_fts VALUES (?, ?)", 
                    ('SQLite Database Guide', 'Comprehensive guide'))
    
    # 子字符串搜索
    results = backend.fetch_all(
        "SELECT * FROM products_fts WHERE products_fts MATCH ?",
        ('ite',)  # 匹配 "SQLite" 中的 "ite"
    )
```

## API 参考

### VirtualTableMixin

SQLiteDialect 通过 VirtualTableMixin 提供完整的虚拟表支持，包括 FTS5。

```python
class VirtualTableMixin:
    # 虚拟表能力检测
    def supports_virtual_table(self) -> bool:
        """检查虚拟表是否支持"""
        
    def supports_fts5(self) -> bool:
        """检查 FTS5 是否支持"""
        
    def supports_rtree(self) -> bool:
        """检查 R-Tree 是否支持"""
        
    def supports_geopoly(self) -> bool:
        """检查 Geopoly 是否支持"""
        
    # FTS5 能力检测
    def supports_fts5_bm25(self) -> bool:
        """检查 BM25 排序是否支持"""
        
    def supports_fts5_highlight(self) -> bool:
        """检查 highlight() 是否支持"""
        
    def supports_fts5_snippet(self) -> bool:
        """检查 snippet() 是否支持"""
        
    def supports_fts5_offset(self) -> bool:
        """检查 offset() 是否支持"""
        
    def get_supported_fts5_tokenizers(self) -> List[str]:
        """获取支持的 tokenizer 列表"""
        
    def format_fts5_create_virtual_table(
        self,
        table_name: str,
        columns: List[str],
        tokenizer: Optional[str] = None,
        tokenizer_options: Optional[Dict[str, Any]] = None,
        prefix: Optional[List[int]] = None,
        content: Optional[str] = None,
        content_rowid: Optional[str] = None,
        tokenize: Optional[str] = None,
    ) -> Tuple[str, tuple]:
        """生成 CREATE VIRTUAL TABLE 语句"""
        
    def format_fts5_match_expression(
        self,
        table_name: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """生成 MATCH 表达式"""
        
    def format_fts5_rank_expression(
        self,
        table_name: str,
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, tuple]:
        """生成 BM25 排序表达式"""
        
    def format_fts5_highlight_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
    ) -> Tuple[str, tuple]:
        """生成 highlight() 表达式"""
        
    def format_fts5_snippet_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
        context_tokens: int = 10,
        ellipsis: str = "...",
    ) -> Tuple[str, tuple]:
        """生成 snippet() 表达式"""
        
    def format_fts5_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """生成 DROP TABLE 语句"""
```

### FTS5Extension

FTS5 扩展类，提供更底层的 FTS5 功能。

```python
class FTS5Extension(SQLiteExtensionBase):
    def get_supported_tokenizers(self, version: Tuple[int, int, int]) -> List[str]:
        """获取指定版本支持的 tokenizer"""
        
    def format_create_virtual_table(...) -> Tuple[str, tuple]:
        """生成创建语句"""
        
    def format_match_expression(...) -> Tuple[str, tuple]:
        """生成 MATCH 表达式"""
        
    def format_rank_expression(...) -> Tuple[str, tuple]:
        """生成排序表达式"""
        
    def format_highlight_expression(...) -> Tuple[str, tuple]:
        """生成高亮表达式"""
        
    def format_snippet_expression(...) -> Tuple[str, tuple]:
        """生成摘要表达式"""
        
    def format_drop_virtual_table(...) -> Tuple[str, tuple]:
        """生成删除语句"""
```

## 参考资料

- [SQLite FTS5 文档](https://www.sqlite.org/fts5.html)
- [FTS5 分词器](https://www.sqlite.org/fts5.html#tokenizers)
- [BM25 排序算法](https://en.wikipedia.org/wiki/Okapi_BM25)
- [rhosocial-activerecord FTS5 源码](../../../src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/fts5.py)
