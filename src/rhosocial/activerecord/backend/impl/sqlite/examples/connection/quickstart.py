"""
Quick Start: Connect to SQLite and execute queries.

This example demonstrates:
1. How to establish a connection to SQLite
2. How to view connection information
3. How to execute queries
4. How to access query results (result data structure)

For more details on SQLite configuration, see:
- SQLiteConnectionConfig
- SQLiteBackend
"""

# ============================================================
# SECTION: Connection Setup
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# Create connection configuration
# SQLite supports:
# - :memory: for in-memory database (temporary)
# - file path for file-based database
# - empty string '' for temporary database (deleted on close)

# In-memory database (temporary, deleted when connection closes)
config = SQLiteConnectionConfig(database=':memory:')

# File-based database
# config = SQLiteConnectionConfig(database='/path/to/database.db')

# Temporary database (deleted when connection closes)
# config = SQLiteConnectionConfig(database='')

# Create backend instance
backend = SQLiteBackend(connection_config=config)

# ============================================================
# SECTION: Establish Connection
# ============================================================
# Connect to the database
# For SQLite, this creates the file if it doesn't exist (for file-based)
backend.connect()

# After connecting, you can access:
# - backend.connection: the underlying connection
# - backend.dialect: the dialect for SQL generation

# ============================================================
# SECTION: View Connection Information
# ============================================================
print(f"Database: {config.database}")
print(f"Is memory: {config.database == ':memory:'}")

# ============================================================
# SECTION: Execute Queries
# ============================================================
# Execute a simple query
result = backend.execute("SELECT 1 AS test")

# ============================================================
# SECTION: Access Query Results
# ============================================================
# QueryResult structure:
# - data: List[Dict] - query results as list of dictionaries
# - affected_rows: int - number of rows affected (for INSERT/UPDATE/DELETE)
# - last_insert_id: Any - last inserted ID (for INSERT with auto-increment)
# - duration: float - query execution duration in seconds

print(f"Result data: {result.data}")       # [{'test': 1}]
print(f"Rows: {result.affected_rows}")    # 1 (for SELECT, shows number of rows)
print(f"Duration: {result.duration:.3f}s")
print(f"Last insert ID: {result.last_insert_id}")  # None for SELECT

# Access individual rows
if result.data:
    row = result.data[0]
    value = row['test']
    print(f"Value from first row: {value}")

# ============================================================
# SECTION: Execute Parameterized Queries (Recommended)
# ============================================================
# Use parameterized queries to prevent SQL injection
# Parameters are passed as a separate tuple
result = backend.execute(
    "SELECT * FROM users WHERE id = ? AND status = ?",
    (1, 'active')
)
print(f"Parameterized query result: {result.data}")

# ============================================================
# SECTION: Execute Script
# ============================================================
# Execute multiple SQL statements at once
sql_script = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE
);

INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');
INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com');
"""

backend.executescript(sql_script)

# ============================================================
# SECTION: Handle Transactions
# ============================================================
# SQLite transactions work similarly to other databases
with backend.connection() as conn:
    conn.execute("BEGIN")
    try:
        conn.execute("INSERT INTO logs (message) VALUES (?)", ('test',))
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        raise e

# ============================================================
# SECTION: Disconnect
# ============================================================
# Always disconnect when done to release resources
# For :memory: databases, data is lost after disconnect
backend.disconnect()

# ============================================================
# SECTION: Error Handling
# ============================================================
try:
    backend.connect()
    result = backend.execute("SELECT * FROM nonexistent_table")
except Exception as e:
    print(f"Error: {e}")
    # Handle specific exceptions:
    # - ConnectionError: connection failed
    # - OperationalError: SQL execution error
    # - ProgrammingError: SQL syntax error
finally:
    if backend.connection:
        backend.disconnect()

# ============================================================
# SECTION: Summary
# ============================================================
# Key points:
# 1. Create SQLiteConnectionConfig with database path
#    - ':memory:' for temporary in-memory database
#    - '' for temporary file-based database
#    - '/path/to/file.db' for persistent file
# 2. Create SQLiteBackend with the config
# 3. Call backend.connect() to establish connection
# 4. Use backend.execute() to run queries
# 5. Use backend.executescript() for multiple statements
# 6. Access result.data for query results
# 7. Call backend.disconnect() when done
#
# SQLite-specific features:
# - Auto-increment uses INTEGER PRIMARY KEY (not AUTOINCREMENT keyword)
# - Use backend.executescript() for multiple SQL statements
# - :memory: databases are temporary and lost on disconnect
#
# Result data structure:
# - QueryResult.data: List[Dict] - query results
# - QueryResult.affected_rows: int
# - QueryResult.last_insert_id: Any
# - QueryResult.duration: float