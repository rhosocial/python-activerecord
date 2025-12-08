-- tests/rhosocial/activerecord_test/feature/basic/schema/column_mapping_items.sql
CREATE TABLE column_mapping_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    item_total INTEGER NOT NULL,
    remarks INTEGER
);
