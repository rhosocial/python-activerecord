-- tests/rhosocial/activerecord_test/feature/events/schema/event_test_models.sql
CREATE TABLE event_test_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',
    event_log TEXT,
    created_at TEXT,
    updated_at TEXT
);