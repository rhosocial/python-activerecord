-- tests/rhosocial/activerecord_test/feature/basic/schema/posts.sql
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    published_at NUMERIC,
    published NUMERIC DEFAULT FALSE,
    created_at NUMERIC NOT NULL,
    updated_at NUMERIC
);
