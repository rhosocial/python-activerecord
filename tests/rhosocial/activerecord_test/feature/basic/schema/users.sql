-- tests/rhosocial/activerecord_test/feature/basic/schema/users.sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER,
    balance REAL NOT NULL DEFAULT 0.0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);
