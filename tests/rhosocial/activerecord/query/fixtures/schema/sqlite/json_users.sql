CREATE TABLE json_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER,
    settings TEXT,
    tags TEXT,
    profile TEXT,
    roles TEXT,
    scores TEXT,
    subscription TEXT,
    preferences TEXT,
    created_at TEXT,
    updated_at TEXT
);