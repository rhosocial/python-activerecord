-- tests/rhosocial/activerecord_test/feature/mixins/schema/tasks.sql
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    is_completed INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT
);