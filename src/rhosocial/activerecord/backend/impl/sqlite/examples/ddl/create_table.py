"""
Create a table with primary key, auto-increment, and index.
"""
META = {
    'title': 'Create Table',
    'dialect_protocols': [],
    'priority': 10,
}

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)
dialect = backend.dialect

# Execute DDL directly using raw SQL
backend.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

backend.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

# Insert after table creation
backend.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
print(f"Table created: users table ready")

backend.disconnect()