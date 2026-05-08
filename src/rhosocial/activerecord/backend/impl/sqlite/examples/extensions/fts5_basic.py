# src/rhosocial/activerecord/backend/impl/sqlite/examples/extensions/fts5_basic.py
"""
FTS5 Full-Text Search advanced features demonstration.

Covers: CREATE TABLE with tokenizers, MATCH (basic/prefix/phrase/NEAR/column/boolean),
BM25 ranking (default/weighted/custom params), highlight(), snippet(), offset(),
Porter stemmer, unicode61 diacritics removal, prefix indexing, trigram tokenizer,
and DROP TABLE.

Uses the dialect's FTS5 formatting methods directly to focus on FTS5 capabilities,
alongside raw SQL execution for clarity.
"""

# ============================================================
# SECTION: Setup
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect
ddl_opts = ExecutionOptions(stmt_type=StatementType.DDL)
dml_opts = ExecutionOptions(stmt_type=StatementType.INSERT)


# ============================================================
# SECTION 1: CREATE Virtual Table with different tokenizers
# ============================================================
print("=" * 60)
print("1. FTS5 Virtual Table Creation")
print("=" * 60)

# 1a. Basic FTS5 table (default unicode61 tokenizer)
sql, _ = dialect.format_fts5_create_virtual_table(
    'articles', ['title', 'body']
)
print(f"\n[1a] Basic FTS5 table (default tokenizer):")
print(f"    SQL: {sql}")
backend.execute(sql, options=ddl_opts)

# 1b. FTS5 table with Porter stemmer tokenizer
sql, _ = dialect.format_fts5_create_virtual_table(
    'posts', ['content'],
    tokenizer='porter'
)
print(f"\n[1b] FTS5 with Porter stemmer:")
print(f"    SQL: {sql}")
backend.execute(sql, options=ddl_opts)

# 1c. FTS5 table with unicode61 + diacritics removal + prefix indexing
sql, _ = dialect.format_fts5_create_virtual_table(
    'texts', ['content'],
    tokenizer='unicode61',
    tokenizer_options={'remove_diacritics': 1},
    prefix=[2, 3]
)
print(f"\n[1c] FTS5 with unicode61+diacritics removal+prefix indexing:")
print(f"    SQL: {sql}")
backend.execute(sql, options=ddl_opts)

# 1d. FTS5 table with ascii tokenizer (ASCII-only word boundaries)
sql, _ = dialect.format_fts5_create_virtual_table(
    'ascii_docs', ['title', 'body'],
    tokenizer='ascii'
)
print(f"\n[1d] FTS5 with ascii tokenizer:")
print(f"    SQL: {sql}")
backend.execute(sql, options=ddl_opts)


# ============================================================
# SECTION 2: Insert data into FTS5 tables
# ============================================================
print("\n" + "=" * 60)
print("2. Inserting documents")
print("=" * 60)

articles_data = [
    ('Python Tutorial', 'Python is a powerful programming language for web development and data science.'),
    ('SQLite Guide', 'SQLite is a lightweight embedded database engine written in C.'),
    ('Web Frameworks', 'Django and Flask are popular Python web frameworks.'),
    ('Database Design', 'Good database design requires understanding of normalization and indexing.'),
    ('Advanced SQL', 'This article covers window functions, CTEs, and query optimization.'),
    ('Python vs JavaScript', 'Both Python and JavaScript are widely used programming languages.'),
    ('Machine Learning', 'Python dominates machine learning with libraries like TensorFlow and PyTorch.'),
]

for title, body in articles_data:
    backend.execute(
        "INSERT INTO articles(title, body) VALUES (?, ?)",
        (title, body), options=dml_opts
    )
print(f"    Inserted {len(articles_data)} documents into 'articles'")

posts_data = [
    ('The cats are running and jumping in the garden.',),
    ('She runs every morning before work.',),
    ('He jumped over the fence and ran away.',),
    ('I like swimming in the lake during summer.',),
    ('Database programming requires careful planning.',),
    ('The runners completed the marathon yesterday.',),
]
for (content,) in posts_data:
    backend.execute(
        "INSERT INTO posts(content) VALUES (?)",
        (content,), options=dml_opts
    )
print(f"    Inserted {len(posts_data)} documents into 'posts'")

texts_data = [
    ('The café menu offers résumé writing services.',),
    ('Visit São Paulo for the best coxinha in Brasil.',),
    ('François adopted naïve approaches to the problème.',),
]
for (content,) in texts_data:
    backend.execute(
        "INSERT INTO texts(content) VALUES (?)",
        (content,), options=dml_opts
    )
print(f"    Inserted {len(texts_data)} documents into 'texts'")

ascii_data = [
    ('English Only', 'Hello world this is a simple ASCII text.'),
    ('With Numbers', 'Page 42 contains 100 examples for testing.'),
    ('Unicode Test', 'café résumé naïve — but only ASCII words are indexed.'),
]
for title, body in ascii_data:
    backend.execute(
        "INSERT INTO ascii_docs(title, body) VALUES (?, ?)",
        (title, body), options=dml_opts
    )
print(f"    Inserted {len(ascii_data)} documents into 'ascii_docs'")


# ============================================================
# SECTION 3: MATCH query types
# ============================================================
print("\n" + "=" * 60)
print("3. MATCH Query Types")
print("=" * 60)

# Helper: fetch with a MATCH query
def search(table: str, query: str, extra_cols: str = "") -> list:
    cols = f"rowid, title, body{extra_cols}" if table == 'articles' else f"rowid, content{extra_cols}"
    sql = f"SELECT {cols} FROM \"{table}\" WHERE \"{table}\" MATCH ?"
    result = backend.fetch_all(sql, (query,))
    return result

def print_results(label: str, results: list, cols_to_show: list = None):
    print(f"\n  [{label}] {len(results)} result(s):")
    for row in results:
        if cols_to_show:
            parts = [f"{k}={row[k]!r}" for k in cols_to_show if k in row]
            print(f"    {', '.join(parts)}")
        else:
            print(f"    {dict(row)}")

# 3a. Basic MATCH
print("\n  --- 3a. Basic MATCH ---")
r = search('articles', 'python')
print_results("python", r, ['title'])

r = search('articles', 'database')
print_results("database", r, ['title'])

# 3b. AND / OR / NOT operators
print("\n  --- 3b. Boolean operators (AND, OR, NOT) ---")
r = search('articles', 'python AND database')
print_results("python AND database", r, ['title'])

r = search('articles', 'python OR database')
print_results("python OR database", r, ['title'])

r = search('articles', 'python NOT javascript')
print_results("python NOT javascript", r, ['title'])

# 3c. Phrase search (exact phrase)
print("\n  --- 3c. Phrase search ---")
r = search('articles', '"web frameworks"')
print_results('"web frameworks"', r, ['title'])

r = search('articles', '"data science"')
print_results('"data science"', r, ['title'])

# 3d. Prefix search
print("\n  --- 3d. Prefix search ---")
r = search('articles', 'prog*')
print_results("prog*", r, ['title', 'body'])

r = search('articles', 'dat*')
print_results("dat*", r, ['title'])

# 3e. NEAR proximity search (NEAR(term1 term2) - terms within ~10 tokens)
print("\n  --- 3e. NEAR proximity search ---")
r = search('articles', 'NEAR(Python web)')
print_results("NEAR(Python web)", r, ['title'])

r = search('articles', 'NEAR(database design)')
print_results("NEAR(database design)", r, ['title'])

# 3f. Column-specific search (FTS5 uses 'col:query' prefix syntax)
print("\n  --- 3f. Column-specific search ---")
sql = "SELECT title, body FROM articles WHERE articles MATCH ?"
r = backend.fetch_all(sql, ('title:Python',))
print_results("title:Python", r, ['title'])

sql = "SELECT title, body FROM articles WHERE articles MATCH ?"
r = backend.fetch_all(sql, ('body:database',))
print_results("body:database", r, ['title'])

# 3g. Negation via query string (FTS5 'NOT' operator within MATCH)
print("\n  --- 3g. Negation using 'python NOT javascript' ---")
r = search('articles', 'python NOT javascript')
print_results("python NOT javascript", r, ['title'])

# Show total count vs match count to demonstrate negation
all_count = backend.fetch_all("SELECT count(*) as cnt FROM articles")[0]['cnt']
python_count = backend.fetch_all(
    "SELECT count(*) as cnt FROM articles WHERE articles MATCH ?",
    ('python',)
)[0]['cnt']
print(f"  Total docs: {all_count}, docs with 'python': {python_count}, without: {all_count - python_count}")


# ============================================================
# SECTION 4: BM25 Ranking
# ============================================================
print("\n" + "=" * 60)
print("4. BM25 Ranking")
print("=" * 60)

# 4a. Default BM25 ranking
print("\n  --- 4a. Default BM25 ranking ---")
sql = ("SELECT title, bm25(articles) as rank FROM articles "
       "WHERE articles MATCH ? ORDER BY rank")
r = backend.fetch_all(sql, ('python',))
print_results("python, ordered by rank", r, ['title', 'rank'])

# The document with most 'python' mentions should rank lowest (best score is lowest for bm25)
sql = ("SELECT title, bm25(articles) as rank FROM articles "
       "WHERE articles MATCH ? ORDER BY rank")
r = backend.fetch_all(sql, ('database',))
print_results("database, ordered by rank", r, ['title', 'rank'])

# 4b. Weighted column ranking (title matched 10x more important)
print("\n  --- 4b. Weighted BM25 ranking ---")
sql = ("SELECT title, bm25(articles, 10.0, 1.0) as rank FROM articles "
       "WHERE articles MATCH ? ORDER BY rank")
r = backend.fetch_all(sql, ('python',))
print_results("python, weighted title=10x body=1x", r, ['title', 'rank'])

# 4c. Custom BM25 parameters (k1, b)
print("\n  --- 4c. Custom BM25 parameters ---")
sql = ("SELECT title, bm25(articles, 'k1', 1.5, 'b', 0.75) as rank FROM articles "
       "WHERE articles MATCH ? ORDER BY rank")
r = backend.fetch_all(sql, ('python',))
print_results("python, k1=1.5 b=0.75", r, ['title', 'rank'])


# ============================================================
# SECTION 5: highlight() function
# ============================================================
print("\n" + "=" * 60)
print("5. highlight() Function")
print("=" * 60)

# 5a. Basic highlight with default <b> markers
print("\n  --- 5a. highlight() with default <b> markers ---")
hl_sql, hl_params = dialect.format_fts5_highlight_expression(
    'articles', 'title', 'python'
)
full_sql = f"SELECT {hl_sql} as highlighted, title FROM articles WHERE articles MATCH ?"
r = backend.fetch_all(full_sql, hl_params + ('python',))
for row in r:
    print(f"    {row['highlighted']}")

# 5b. highlight with custom markers (ANSI terminal coloring)
print("\n  --- 5b. highlight() with custom [[markers]] ---")
sql = ("SELECT highlight(articles, body, '[[', ']]') as highlighted, title FROM articles "
       "WHERE articles MATCH ?")
r = backend.fetch_all(sql, ('database',))
for row in r:
    print(f"    [{row['title']}] {row['highlighted']}")


# ============================================================
# SECTION 6: snippet() function
# ============================================================
print("\n" + "=" * 60)
print("6. snippet() Function")
print("=" * 60)

# 6a. Basic snippet with default settings (10 context tokens)
print("\n  --- 6a. snippet() with defaults (10 context tokens) ---")
sql = ("SELECT snippet(articles, body, '<b>', '</b>', '...', 10) as snip, title FROM articles "
       "WHERE articles MATCH ?")
r = backend.fetch_all(sql, ('web',))
for row in r:
    print(f"    [{row['title']}] {row['snip']}")

# 6b. snippet with custom context window
print("\n  --- 6b. snippet() with 3 context tokens ---")
sql = ("SELECT snippet(articles, body, '[', ']', '..', 3) as snip, title FROM articles "
       "WHERE articles MATCH ?")
r = backend.fetch_all(sql, ('python',))
for row in r:
    print(f"    [{row['title']}] {row['snip']}")


# ============================================================
# SECTION 7: rank (built-in FTS5 rank column)
# ============================================================
print("\n" + "=" * 60)
print("7. FTS5 Built-in rank Column")
print("=" * 60)
sql = ("SELECT title, rank FROM articles WHERE articles MATCH ? "
       "ORDER BY rank")
r = backend.fetch_all(sql, ('python',))
print(f"\n  Results ordered by rank (lower = more relevant):")
for row in r:
    print(f"    rank={row['rank']:.6e} title={row['title']!r}")


# ============================================================
# SECTION 8: ASCII Tokenizer
# ============================================================
print("\n" + "=" * 60)
print("8. ASCII Tokenizer")
print("=" * 60)

# ASCII tokenizer splits on ASCII whitespace and punctuation.
# Non-ASCII characters (like café, résumé) are treated as token boundaries.
print("\n  --- ASCII tokenizer: only ASCII word tokens ---")
r = backend.fetch_all(
    "SELECT rowid, title, body FROM ascii_docs WHERE ascii_docs MATCH ?",
    ('hello',)
)
print(f"    MATCH 'hello': {len(r)} result(s) (expected 1 — 'English Only')")

r = backend.fetch_all(
    "SELECT rowid, title, body FROM ascii_docs WHERE ascii_docs MATCH ?",
    ('naïve',)
)
print(f"    MATCH 'naïve': {len(r)} result(s) (expected 0 — ASCII tokenizer splits at non-ASCII chars)")

r = backend.fetch_all(
    "SELECT rowid, title, body FROM ascii_docs WHERE ascii_docs MATCH ?",
    ('100',)
)
print(f"    MATCH '100': {len(r)} result(s) (expected 1 — numbers are ASCII tokens)")


# ============================================================
# SECTION 9: Porter Stemmer Tokenizer
# ============================================================
print("\n" + "=" * 60)
print("9. Porter Stemmer Tokenizer")
print("=" * 60)

# Porter stemmer reduces words to their root form:
#   "running"/"runs" -> stem "run", "jumping" -> stem "jump", "swimming" -> stem "swim"
print("\n  --- Porter stemmer: searching with stemmed terms ---")
test_cases = [
    ("run",   "matches 'running' and 'runs' (stem: run)"),
    ("runner", "matches 'runners' (stem: runner)"),
    ("program", "matches 'programming' (stem: program)"),
]
for query, desc in test_cases:
    r = backend.fetch_all(
        "SELECT rowid, content FROM posts WHERE posts MATCH ?",
        (query,)
    )
    print(f"    MATCH '{query}' ({desc}): {len(r)} row(s)")
    for row in r:
        print(f"      rowid={row['rowid']}: {row['content']!r}")


# ============================================================
# SECTION 9: Unicode61 Tokenizer with Diacritics Removal
# ============================================================
print("\n" + "=" * 60)
print("10. Unicode61 Tokenizer - Diacritics Removal")
print("=" * 60)
print("\n  --- Searching without diacritics should match accented text ---")
test_cases = [
    ("cafe",      "matching 'café' via diacritics removal"),
    ("resume",    "matching 'résumé' via diacritics removal"),
    ("Sao Paulo", "matching 'São Paulo'"),
    ("naive",     "matching 'naïve'"),
]
for query, desc in test_cases:
    r = backend.fetch_all(
        "SELECT rowid, content FROM texts WHERE texts MATCH ?",
        (query,)
    )
    match_count = len(r)
    print(f"    MATCH '{query}' ({desc}): {match_count} row(s)")
    for row in r:
        print(f"      rowid={row['rowid']}: {row['content']!r}")


# ============================================================
# SECTION 10: Trigram Tokenizer (substring matching)
# ============================================================
print("\n" + "=" * 60)
print("11. Trigram Tokenizer (Substring Matching)")
print("=" * 60)

# Check if trigram is supported (SQLite >= 3.34.0)
if 'trigram' in dialect.get_supported_fts5_tokenizers():
    sql, _ = dialect.format_fts5_create_virtual_table(
        'substrings', ['content'],
        tokenizer='trigram'
    )
    backend.execute(sql, options=ddl_opts)
    print(f"\n  Created 'substrings' table with trigram tokenizer")

    trigram_data = [
        ('hello world',),
        ('python programming',),
        ('postgresql database',),
    ]
    for (content,) in trigram_data:
        backend.execute(
            "INSERT INTO substrings(content) VALUES (?)",
            (content,), options=dml_opts
        )
    print(f"  Inserted {len(trigram_data)} documents")

    # Trigram allows substring matching (not just word boundaries)
    print("\n  --- Trigram substring matching ---")
    for query in ['wor', 'ogr', 'sql', 'tho']:
        r = backend.fetch_all(
            "SELECT rowid, content FROM substrings WHERE substrings MATCH ?",
            (query,)
        )
        print(f"    MATCH '{query}': {len(r)} result(s)")
        for row in r:
            print(f"      {row['content']!r}")
else:
    print("\n  Trigram tokenizer requires SQLite >= 3.34.0, skipping.")


# ============================================================
# SECTION 11: DROP Virtual Table
# ============================================================
print("\n" + "=" * 60)
print("12. DROP FTS5 Virtual Table")
print("=" * 60)

sql_if, _ = dialect.format_fts5_drop_virtual_table('articles', if_exists=True)
sql_noif, _ = dialect.format_fts5_drop_virtual_table('posts')
print(f"\n  [11a] DROP IF EXISTS: {sql_if}")
print(f"  [11b] DROP: {sql_noif}")

# Drop all FTS5 virtual tables (shadow tables are auto-removed)
for tbl in ['posts', 'texts', 'articles', 'ascii_docs', 'substrings']:
    if len(backend.fetch_all(f"SELECT name FROM sqlite_master WHERE name='{tbl}'")) > 0:
        backend.execute(
            dialect.format_fts5_drop_virtual_table(tbl, if_exists=True)[0],
            options=ddl_opts
        )

# Verify FTS5 virtual tables are gone (shadow tables auto-removed on DROP)
remaining = backend.fetch_all(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
)
print(f"\n  Remaining tables after cleanup: {len(remaining)} (all clean)" if len(remaining) == 0 else f"\n  Remaining tables: {[r['name'] for r in remaining]}")


# ============================================================
# SECTION: Teardown
# ============================================================
print("\n" + "=" * 60)
print("FTS5 demonstration complete.")
print("=" * 60)
backend.disconnect()