"""
Basic transaction control using transaction manager.
"""
META = {
    'title': 'Transaction Control',
    'dialect_protocols': [],
    'priority': 10,
}

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)

# Setup
backend.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        balance REAL DEFAULT 0
    )
""")
backend.execute("INSERT INTO accounts (name, balance) VALUES ('Alice', 100)")

# Use transaction manager
with backend.transaction():
    backend.execute("UPDATE accounts SET balance = balance - 50 WHERE name = 'Alice'")

# Verify
result = backend.execute("SELECT balance FROM accounts WHERE name = 'Alice'")
print(f"Balance after transaction: {result.affected_rows}")

backend.disconnect()