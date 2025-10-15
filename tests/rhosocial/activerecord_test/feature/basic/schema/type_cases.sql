-- tests/rhosocial/activerecord_test/feature/basic/schema/type_cases.sql
CREATE TABLE type_cases (
    id TEXT PRIMARY KEY,
    username TEXT,
    email TEXT,
    tiny_int INTEGER,
    small_int INTEGER,
    big_int INTEGER,
    float_val REAL,
    double_val REAL,
    decimal_val REAL,
    char_val TEXT,
    varchar_val TEXT,
    text_val TEXT,
    date_val TEXT,
    time_val TEXT,
    timestamp_val TEXT,
    blob_val BLOB,
    json_val TEXT,
    array_val TEXT,
    is_active BOOLEAN
);
