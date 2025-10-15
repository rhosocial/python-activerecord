-- tests/rhosocial/activerecord_test/feature/query/schema/extended_orders.sql
CREATE TABLE extended_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    order_number TEXT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    region TEXT DEFAULT 'default',
    category TEXT DEFAULT '',
    product TEXT DEFAULT '',
    department TEXT DEFAULT '',
    year TEXT DEFAULT '',
    quarter TEXT DEFAULT '',
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);