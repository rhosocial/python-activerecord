# FTS5 Full-Text Search

FTS5 (Full-Text Search version 5) is SQLite's full-text search engine, providing powerful text search capabilities. rhosocial-activerecord provides complete FTS5 support for the SQLite backend.

## Overview

FTS5 Features:

- **Full-Text Search**: Fast text search with Boolean queries, phrase queries, NEAR queries
- **BM25 Ranking**: Relevance-based result ranking
- **Highlight and Snippet**: Search result highlighting and snippet extraction
- **Multiple Tokenizers**: Support for unicode61, ascii, porter, trigram tokenizers
- **Column Weights**: Support for setting search weights for different columns
- **External Content**: Support for external content mode linked to regular tables

**Version Required**: SQLite 3.9.0+

## Version Compatibility Check

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# Check FTS5 support
if dialect.supports_fts5():
    print("FTS5 available")

# Check specific features
if dialect.supports_fts5_bm25():
    print("BM25 ranking available")

if dialect.supports_fts5_highlight():
    print("highlight() function available")

# Check tokenizers
tokenizers = dialect.get_supported_fts5_tokenizers()
print(f"Supported tokenizers: {tokenizers}")
# ['unicode61', 'ascii', 'porter', 'trigram'] (requires 3.34.0+)
```

## Creating FTS5 Virtual Tables

### Basic Creation

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect

dialect = SQLiteDialect(version=(3, 35, 0))

# Create basic FTS5 table
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content', 'author']
)
# Result: CREATE VIRTUAL TABLE "articles_fts" USING fts5("title", "content", "author")

# Execute
backend.execute(sql, params)
```

### Using Tokenizers

```python
# Use Porter stemmer tokenizer (supports stemming)
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    tokenizer='porter'
)
# Result: CREATE VIRTUAL TABLE "articles_fts" USING fts5("title", "content", tokenize='porter')

# Use unicode61 tokenizer with options
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    tokenizer='unicode61',
    tokenizer_options={'remove_diacritics': 1}
)
# Result: CREATE VIRTUAL TABLE ... tokenize='unicode61 remove_diacritics 1'
```

### Available Tokenizers

| Tokenizer | Min Version | Description |
|-----------|-------------|-------------|
| unicode61 | 3.9.0 | Default tokenizer, Unicode support |
| ascii | 3.9.0 | Simple ASCII tokenizer |
| porter | 3.9.0 | Porter stemmer tokenizer (stemming) |
| trigram | 3.34.0 | Trigram tokenizer (substring search) |

```python
# Check tokenizer availability
if dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    sql, params = dialect.format_fts5_create_virtual_table(
        table_name='articles_fts',
        columns=['content'],
        tokenizer='trigram'
    )
```

### Prefix Indexing

```python
# Enable prefix indexing (supports prefix search)
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    prefix=[2, 3]  # Support 2-char and 3-char prefixes
)
# Result: CREATE VIRTUAL TABLE ... prefix='2 3'
```

### External Content Mode

```python
# Create FTS5 table linked to regular table
# First create regular table
backend.execute("""
    CREATE TABLE articles (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        author TEXT
    )
""")

# Create linked FTS5 table
sql, params = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    content='articles',        # Content table
    content_rowid='id'         # Row ID column
)
# Result: CREATE VIRTUAL TABLE "articles_fts" USING fts5(
#     "title", "content", content='articles', content_rowid='id'
# )
```

## Full-Text Search Queries

### Basic MATCH Query

```python
# Generate MATCH expression
sql, params = dialect.format_fts5_match_expression(
    table_name='articles_fts',
    query='sqlite database'
)
# SQL: "articles_fts" MATCH ?
# params: ('sqlite database',)

# Full query
query_sql = f"""
    SELECT * FROM articles_fts 
    WHERE {sql}
    ORDER BY bm25(articles_fts)
"""
results = backend.fetch_all(query_sql, params)
```

### Column-Specific Search

```python
# Search only title column
sql, params = dialect.format_fts5_match_expression(
    table_name='articles_fts',
    query='python',
    columns=['title']
)
# params: ('{title:} python',)

# Search multiple columns
sql, params = dialect.format_fts5_match_expression(
    table_name='articles_fts',
    query='python',
    columns=['title', 'content']
)
# params: ('{title: OR content:} python',)
```

### Negated Search

```python
# NOT MATCH (exclude matching results)
sql, params = dialect.format_fts5_match_expression(
    table_name='articles_fts',
    query='python',
    negate=True
)
# SQL: "articles_fts" NOT MATCH ?
```

### Query Syntax

FTS5 supports rich query syntax:

```python
# Boolean queries
query = 'python AND database'     # Contains both
query = 'python OR database'      # Contains either
query = 'python NOT database'     # Contains python but not database

# Phrase query
query = '"sqlite database"'       # Exact phrase

# NEAR query
query = 'python NEAR database'    # Words are adjacent
query = 'python NEAR/5 database'  # Words within 5 tokens

# Prefix query
query = 'sql*'                    # Starts with sql

# Column-specific
query = 'title:python'            # Search only title column
query = 'title, content:python'   # Search multiple columns
```

## Result Ranking (BM25)

### Basic Ranking

```python
# Generate BM25 ranking expression
sql, params = dialect.format_fts5_rank_expression(
    table_name='articles_fts'
)
# Result: bm25("articles_fts")

# Use in query
query_sql = f"""
    SELECT *, {sql} as rank
    FROM articles_fts
    WHERE "articles_fts" MATCH ?
    ORDER BY rank
"""
```

### Weighted Ranking

```python
# Set weights for different columns
sql, params = dialect.format_fts5_rank_expression(
    table_name='articles_fts',
    weights=[10.0, 1.0]  # title weight 10, content weight 1
)
# Result: bm25("articles_fts", 10.0, 1.0)
```

### Custom BM25 Parameters

```python
# Custom k1 and b parameters
sql, params = dialect.format_fts5_rank_expression(
    table_name='articles_fts',
    bm25_params={'k1': 1.5, 'b': 0.75}
)
# Result: bm25("articles_fts", 'k1', 1.5, 'b', 0.75)

# Both weights and BM25 parameters
sql, params = dialect.format_fts5_rank_expression(
    table_name='articles_fts',
    weights=[10.0, 1.0],
    bm25_params={'k1': 1.2}
)
# Result: bm25("articles_fts", 10.0, 1.0, 'k1', 1.2)
```

## Highlight and Snippet

### Highlighting Matches

```python
# Generate highlight expression
sql, params = dialect.format_fts5_highlight_expression(
    table_name='articles_fts',
    column='content',
    query='python',
    prefix_marker='<mark>',
    suffix_marker='</mark>'
)
# SQL: highlight("articles_fts", "content", ?, ?)
# params: ('<mark>', '</mark>')

# Use in query
query_sql = f"""
    SELECT title, {sql} as highlighted_content
    FROM articles_fts
    WHERE "articles_fts" MATCH ?
"""
```

### Generating Snippets

```python
# Generate snippet expression
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

## Dropping FTS5 Tables

```python
# Drop FTS5 virtual table
sql, params = dialect.format_fts5_drop_virtual_table(
    table_name='articles_fts'
)
# Result: DROP TABLE "articles_fts"

# With IF EXISTS
sql, params = dialect.format_fts5_drop_virtual_table(
    table_name='articles_fts',
    if_exists=True
)
# Result: DROP TABLE IF EXISTS "articles_fts"
```

## Complete Example

### Creating an Article Search System

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteDialect
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# Create backend
backend = SQLiteBackend(database=":memory:")
backend.connect()

dialect = backend.dialect

# Check FTS5 support
if not dialect.supports_fts5():
    raise RuntimeError("FTS5 not supported")

# Create articles table
backend.execute("""
    CREATE TABLE articles (
        id INTEGER PRIMARY KEY,
        title TEXT,
        content TEXT,
        author TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Create FTS5 virtual table
fts_sql, _ = dialect.format_fts5_create_virtual_table(
    table_name='articles_fts',
    columns=['title', 'content'],
    tokenizer='porter',
    content='articles',
    content_rowid='id'
)
backend.execute(fts_sql)

# Insert test data
articles = [
    ('SQLite Tutorial', 'SQLite is a powerful embedded database for Python applications', 'Alice'),
    ('Python Programming', 'Learn Python from basics to advanced topics', 'Bob'),
    ('Database Design', 'Best practices for database schema design with SQLite', 'Alice'),
]

insert_sql = "INSERT INTO articles (title, content, author) VALUES (?, ?, ?)"
insert_opts = ExecutionOptions(stmt_type=StatementType.INSERT)
for title, content, author in articles:
    backend.execute(insert_sql, (title, content, author), options=insert_opts)

# Rebuild FTS index
backend.execute("INSERT INTO articles_fts(articles_fts) VALUES('rebuild')")

# Full-text search
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

# Search with highlighting
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

# Cleanup
backend.disconnect()
```

### Using Trigram Tokenizer

```python
# Trigram tokenizer supports substring search
if dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    # Create FTS5 table with trigram
    sql, _ = dialect.format_fts5_create_virtual_table(
        'products_fts',
        ['name', 'description'],
        tokenizer='trigram'
    )
    backend.execute(sql)
    
    # Insert data
    backend.execute("INSERT INTO products_fts VALUES (?, ?)", 
                    ('SQLite Database Guide', 'Comprehensive guide'))
    
    # Substring search
    results = backend.fetch_all(
        "SELECT * FROM products_fts WHERE products_fts MATCH ?",
        ('ite',)  # Matches "ite" in "SQLite"
    )
```

## API Reference

### VirtualTableMixin

SQLiteDialect provides complete virtual table support through VirtualTableMixin, including FTS5.

```python
class VirtualTableMixin:
    # Virtual table capability detection
    def supports_virtual_table(self) -> bool:
        """Check if virtual tables are supported"""
        
    def supports_fts5(self) -> bool:
        """Check if FTS5 is supported"""
        
    def supports_rtree(self) -> bool:
        """Check if R-Tree is supported"""
        
    def supports_geopoly(self) -> bool:
        """Check if Geopoly is supported"""
        
    # FTS5 capability detection
    def supports_fts5_bm25(self) -> bool:
        """Check if BM25 ranking is supported"""
        
    def supports_fts5_highlight(self) -> bool:
        """Check if highlight() is supported"""
        
    def supports_fts5_snippet(self) -> bool:
        """Check if snippet() is supported"""
        
    def supports_fts5_offset(self) -> bool:
        """Check if offset() is supported"""
        
    def get_supported_fts5_tokenizers(self) -> List[str]:
        """Get list of supported tokenizers"""
        
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
        """Generate CREATE VIRTUAL TABLE statement"""
        
    def format_fts5_match_expression(
        self,
        table_name: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """Generate MATCH expression"""
        
    def format_fts5_rank_expression(
        self,
        table_name: str,
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, tuple]:
        """Generate BM25 ranking expression"""
        
    def format_fts5_highlight_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
    ) -> Tuple[str, tuple]:
        """Generate highlight() expression"""
        
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
        """Generate snippet() expression"""
        
    def format_fts5_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Generate DROP TABLE statement"""
```

### FTS5Extension

FTS5 extension class providing lower-level FTS5 functionality.

```python
class FTS5Extension(SQLiteExtensionBase):
    def get_supported_tokenizers(self, version: Tuple[int, int, int]) -> List[str]:
        """Get tokenizers supported for specified version"""
        
    def format_create_virtual_table(...) -> Tuple[str, tuple]:
        """Generate CREATE statement"""
        
    def format_match_expression(...) -> Tuple[str, tuple]:
        """Generate MATCH expression"""
        
    def format_rank_expression(...) -> Tuple[str, tuple]:
        """Generate ranking expression"""
        
    def format_highlight_expression(...) -> Tuple[str, tuple]:
        """Generate highlight expression"""
        
    def format_snippet_expression(...) -> Tuple[str, tuple]:
        """Generate snippet expression"""
        
    def format_drop_virtual_table(...) -> Tuple[str, tuple]:
        """Generate DROP statement"""
```

## References

- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html)
- [FTS5 Tokenizers](https://www.sqlite.org/fts5.html#tokenizers)
- [BM25 Ranking Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [rhosocial-activerecord FTS5 Source](../../../src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/fts5.py)
