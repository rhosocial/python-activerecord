-- tests/rhosocial/activerecord_test/feature/basic/schema/validated_users.sql
CREATE TABLE validated_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    age INTEGER
);