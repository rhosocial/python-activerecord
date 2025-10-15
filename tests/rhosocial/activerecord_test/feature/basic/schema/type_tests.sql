-- tests/rhosocial/activerecord_test/feature/basic/schema/type_tests.sql
CREATE TABLE type_tests (
    id TEXT PRIMARY KEY,
    string_field TEXT,
    int_field INTEGER,
    float_field REAL,
    decimal_field REAL,
    bool_field BOOLEAN,
    datetime_field TEXT,
    json_field TEXT,
    nullable_field TEXT
);
