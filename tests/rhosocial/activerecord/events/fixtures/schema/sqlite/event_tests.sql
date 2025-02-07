CREATE TABLE IF NOT EXISTS event_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    revision INTEGER NOT NULL DEFAULT 1,
    content TEXT,
    created_at TEXT,
    updated_at TEXT
);