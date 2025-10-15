-- tests/rhosocial/activerecord_test/feature/mixins/schema/versioned_products.sql
CREATE TABLE IF NOT EXISTS versioned_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL DEFAULT 0.0,
    version INTEGER NOT NULL DEFAULT 1
);