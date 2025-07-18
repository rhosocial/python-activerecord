-- tests/rhosocial/activerecord_test/mixins/fixtures/schema/sqlite/timestamped_posts.sql
CREATE TABLE IF NOT EXISTS timestamped_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);