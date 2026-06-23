-- tests/rhosocial/activerecord_test/feature/query/schema/nodes.sql
CREATE TABLE IF NOT EXISTS nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER DEFAULT NULL,
    value NUMERIC DEFAULT 0.00,
    created_at NUMERIC DEFAULT CURRENT_TIMESTAMP,
    updated_at NUMERIC DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES nodes(id) ON DELETE CASCADE
);