-- tests/rhosocial/activerecord_test/basic/fixtures/schema/sqlite/validated_users.sql
CREATE TABLE validated_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,  -- Strings of length 3-50 can only contain letters and numbers
    email TEXT NOT NULL,     -- Valid mailbox format
    age INTEGER             -- Optional, but if supplied, it must be between 0-150 and not less than 13
);