"""
Full-Text Search (FTS5): create virtual table, insert documents, and search
using MATCH, prefix, phrase, and NEAR queries.

NOTE: FTS5 virtual tables use CREATE VIRTUAL TABLE ... USING fts5(...)
syntax, which is not covered by the current Expression API (CreateTableExpression
does not support virtual tables). Therefore this example uses backend.execute()
with raw SQL for all FTS5-specific operations. When Expression API support for
virtual tables is added in the future, these sections can be migrated accordingly.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# FTS5 virtual tables require raw SQL because CreateTableExpression
# does not support the CREATE VIRTUAL TABLE ... USING fts5(...) syntax.
# This is a known limitation of the current Expression API.
backend.execute(
    "CREATE VIRTUAL TABLE docs USING fts5(title, content)"
)

# Insert sample documents into the FTS5 table.
# Like table creation, INSERT into FTS5 tables is performed with raw SQL.
documents = [
    ("SQLite FTS5 Extension", "SQLite includes a full-text search engine called FTS5."),
    ("Getting Started with Python", "Python is a versatile programming language for web development."),
    ("Advanced Python Techniques", "Decorators and generators are advanced Python features."),
    ("Database Design Patterns", "Common patterns include repository, unit of work, and active record."),
    ("Python Web Frameworks", "Django and Flask are popular Python web frameworks."),
]
for title, content in documents:
    backend.execute(
        "INSERT INTO docs(title, content) VALUES(?, ?)",
        (title, content),
    )

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# --- Example 1: Basic MATCH search ---
# Search for documents containing the word "Python".
# The MATCH clause is FTS5-specific and not representable via the
# current Expression API predicate system, so raw SQL is used.
match_sql = "SELECT * FROM docs WHERE docs MATCH ?"
match_param = ("Python",)

print(f"Basic MATCH SQL: {match_sql}")
print(f"Params: {match_param}")

# --- Example 2: Prefix search ---
# Use the * suffix for prefix matching: find documents containing
# words that start with "prog".
prefix_sql = "SELECT * FROM docs WHERE docs MATCH ?"
prefix_param = ("prog*",)

print(f"\nPrefix search SQL: {prefix_sql}")
print(f"Params: {prefix_param}")

# --- Example 3: Phrase search ---
# Enclose multiple words in quotes to match the exact phrase.
phrase_sql = "SELECT * FROM docs WHERE docs MATCH ?"
phrase_param = ('"web frameworks"',)

print(f"\nPhrase search SQL: {phrase_sql}")
print(f"Params: {phrase_param}")

# --- Example 4: NEAR query ---
# NEAR finds documents where two terms appear close to each other
# (within 10 tokens by default).
near_sql = "SELECT * FROM docs WHERE docs MATCH ?"
near_param = ("Python NEAR web",)

print(f"\nNEAR query SQL: {near_sql}")
print(f"Params: {near_param}")

# --- Example 5: Column-specific search ---
# Restrict the search to a specific column using the column:term syntax.
column_sql = "SELECT * FROM docs WHERE docs MATCH ?"
column_param = ("title:Python",)

print(f"\nColumn-specific search SQL: {column_sql}")
print(f"Params: {column_param}")

# --- Example 6: Boolean operators (AND, OR, NOT) ---
# Combine terms with boolean operators for more complex queries.
# Note: In FTS5, NOT is a unary operator (not binary), so the syntax
# is "term1 NOT term2" rather than "term1 AND NOT term2".
boolean_sql = "SELECT * FROM docs WHERE docs MATCH ?"
boolean_param = ("Python NOT Django",)

print(f"\nBoolean query SQL: {boolean_sql}")
print(f"Params: {boolean_param}")

# ============================================================
# SECTION: Execution (run the expressions)
# ============================================================

options = ExecutionOptions(stmt_type=StatementType.DQL)

# Execute basic MATCH search
result = backend.execute(match_sql, match_param, options=options)
print("\nBasic MATCH results (documents containing 'Python'):")
for row in result.data or []:
    print(f"  {row}")

# Execute prefix search
result = backend.execute(prefix_sql, prefix_param, options=options)
print("\nPrefix search results (words starting with 'prog'):")
for row in result.data or []:
    print(f"  {row}")

# Execute phrase search
result = backend.execute(phrase_sql, phrase_param, options=options)
print("\nPhrase search results (exact phrase 'web frameworks'):")
for row in result.data or []:
    print(f"  {row}")

# Execute NEAR query
result = backend.execute(near_sql, near_param, options=options)
print("\nNEAR query results ('Python' near 'web'):")
for row in result.data or []:
    print(f"  {row}")

# Execute column-specific search
result = backend.execute(column_sql, column_param, options=options)
print("\nColumn-specific search results ('Python' in title only):")
for row in result.data or []:
    print(f"  {row}")

# Execute boolean query
result = backend.execute(boolean_sql, boolean_param, options=options)
print("\nBoolean query results ('Python NOT Django'):")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
