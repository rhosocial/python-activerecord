-- tests/rhosocial/activerecord_test/basic/fixtures/schema/sqlite/type_tests.sql
CREATE TABLE type_tests (
    id TEXT PRIMARY KEY,  -- UUID类型存储为TEXT
    string_field TEXT NOT NULL,
    int_field INTEGER NOT NULL,
    float_field REAL NOT NULL,
    decimal_field TEXT NOT NULL,  -- SQLite没有DECIMAL类型,使用TEXT存储
    bool_field INTEGER NOT NULL,  -- SQLite使用INTEGER存储布尔值
    datetime_field TEXT NOT NULL, -- SQLite使用TEXT存储日期时间
    json_field TEXT,              -- JSON数据存储为TEXT
    nullable_field TEXT           -- 可空字段
);