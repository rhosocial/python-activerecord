-- tests/rhosocial/activerecord_test/feature/basic/schema/comments.sql
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_ref INTEGER NOT NULL,
    author INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    approved BOOLEAN DEFAULT FALSE
);
