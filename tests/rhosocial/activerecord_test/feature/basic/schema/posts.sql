-- tests/rhosocial/activerecord_test/feature/basic/schema/posts.sql
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    published_at DATETIME,
    published BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME
);
