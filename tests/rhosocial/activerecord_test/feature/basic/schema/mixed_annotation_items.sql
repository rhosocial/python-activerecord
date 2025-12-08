-- tests/rhosocial/activerecord_test/feature/basic/schema/mixed_annotation_items.sql
CREATE TABLE mixed_annotation_items (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    tags TEXT,
    meta TEXT,
    description TEXT,
    status TEXT
);
