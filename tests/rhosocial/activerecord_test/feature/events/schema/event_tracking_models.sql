-- tests/rhosocial/activerecord_test/feature/events/schema/event_tracking_models.sql
CREATE TABLE event_tracking_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    view_count INTEGER DEFAULT 0,
    last_viewed_at TEXT
);