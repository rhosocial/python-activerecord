-- tests/rhosocial/activerecord_test/feature/query/schema/extended_order_items.sql
CREATE TABLE extended_order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price DECIMAL(10,2) NOT NULL,
    category TEXT DEFAULT '',
    region TEXT DEFAULT '',
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (order_id) REFERENCES extended_orders(id)
);