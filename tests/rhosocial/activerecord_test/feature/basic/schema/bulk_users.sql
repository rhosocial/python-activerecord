-- tests/rhosocial/activerecord_test/feature/basic/schema/bulk_users.sql
CREATE TABLE bulk_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER DEFAULT 0,
    email TEXT DEFAULT ''
);
