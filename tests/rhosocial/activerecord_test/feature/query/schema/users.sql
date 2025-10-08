-- tests/rhosocial/activerecord_test/feature/query/schema/users.sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER,
    balance REAL NOT NULL DEFAULT 0.00,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);