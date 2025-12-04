CREATE TABLE IF NOT EXISTS type_adapter_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    optional_name TEXT,
    optional_age INTEGER,
    last_login TEXT,
    is_premium INTEGER,
    unsupported_union TEXT,
    custom_bool TEXT,
    optional_custom_bool TEXT
);
