-- tests/rhosocial/activerecord_test/basic/fixtures/schema/sqlite/type_tests.sql
CREATE TABLE type_tests (
    id TEXT PRIMARY KEY,  -- The UUID type is stored as TEXT
    string_field TEXT NOT NULL,
    int_field INTEGER NOT NULL,
    float_field REAL NOT NULL,
    decimal_field TEXT NOT NULL,  -- SQLite does not have a DECIMAL type and uses TEXT storage
    bool_field INTEGER NOT NULL,  -- SQLite uses INTEGER to store booleans
    datetime_field TEXT NOT NULL, -- SQLite uses TEXT to store the datetime
    json_field TEXT,              -- JSON data is stored as TEXT
    nullable_field TEXT           -- Nullable fields are also stored as TEXT
);