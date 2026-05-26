-- tests/rhosocial/activerecord_test/feature/basic/schema/pydantic_validated_models.sql
CREATE TABLE pydantic_validated_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    quantity INTEGER,
    price REAL,
    start_at TEXT,
    end_at TEXT,
    status TEXT,
    normalized_name TEXT,
    created_token TEXT
);
