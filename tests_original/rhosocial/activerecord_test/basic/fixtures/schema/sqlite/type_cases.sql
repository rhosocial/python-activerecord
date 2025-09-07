-- tests/rhosocial/activerecord_test/basic/fixtures/schema/sqlite/type_cases.sql
CREATE TABLE type_cases (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    tiny_int INTEGER,
    small_int INTEGER,
    big_int INTEGER,
    float_val REAL,
    double_val REAL,
    decimal_val TEXT,
    char_val TEXT,
    varchar_val TEXT,
    text_val TEXT,
    date_val TEXT,
    time_val TEXT,
    timestamp_val TEXT,
    blob_val BLOB,
    json_val TEXT,
    array_val TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);