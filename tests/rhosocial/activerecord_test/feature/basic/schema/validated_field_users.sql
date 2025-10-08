-- tests/rhosocial/activerecord_test/feature/basic/schema/validated_field_users.sql
CREATE TABLE validated_field_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER,
    balance REAL,
    credit_score INTEGER NOT NULL,
    status TEXT NOT NULL,
    is_active BOOLEAN
);
