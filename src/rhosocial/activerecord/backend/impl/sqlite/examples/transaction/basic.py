"""
Basic transaction control using transaction manager.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=':memory:')
backend = SQLiteBackend(config)

# Create table for testing
backend.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        balance REAL DEFAULT 0
    )
""")
backend.execute("INSERT INTO accounts (name, balance) VALUES ('Alice', 100)")

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
# The transaction is used as a context manager, no special import needed

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
with backend.transaction():
    backend.execute("UPDATE accounts SET balance = balance - 50 WHERE name = 'Alice'")

# Verify
result = backend.execute("SELECT balance FROM accounts WHERE name = 'Alice'")
print(f"Balance after transaction: {result.affected_rows}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()