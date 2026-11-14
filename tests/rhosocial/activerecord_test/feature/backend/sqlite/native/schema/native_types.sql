-- tests/rhosocial/activerecord_test/feature/backend/sqlite/native/schema/native_types.sql
--
-- One table per SQLite column affinity.  Every table carries the same payload
-- columns, declared with that table's affinity, so the *same* Python value can
-- be written into each of them and the stored form compared.
--
-- SQLite has no backend-specific column types; what is backend-specific is the
-- way a declared type selects an affinity and rewrites the stored value
-- (https://www.sqlite.org/datatype3.html#determination_of_column_affinity).
-- These tables therefore declare only bare affinity names.
--
-- The fixture schema must stay free of semicolons inside string literals: the
-- definition class in ``native_models.py`` splits the file on ";" into single
-- statements before the environment executes them.

-- TEXT affinity: numeric values are stored as text.
CREATE TABLE native_affinity_text (
    id INTEGER PRIMARY KEY,
    shape TEXT,
    flags TEXT,
    amount TEXT,
    payload TEXT,
    raw_bytes TEXT,
    counter TEXT,
    ratio TEXT
);

-- INTEGER affinity: numeric-looking text becomes INTEGER, REAL stays REAL
-- unless it is integral.
CREATE TABLE native_affinity_integer (
    id INTEGER PRIMARY KEY,
    shape INTEGER,
    flags INTEGER,
    amount INTEGER,
    payload INTEGER,
    raw_bytes INTEGER,
    counter INTEGER,
    ratio INTEGER
);

-- REAL affinity: every numeric value is stored as REAL.
CREATE TABLE native_affinity_real (
    id INTEGER PRIMARY KEY,
    shape REAL,
    flags REAL,
    amount REAL,
    payload REAL,
    raw_bytes REAL,
    counter REAL,
    ratio REAL
);

-- NUMERIC affinity: numeric-looking text becomes INTEGER or REAL, whichever
-- represents the value without loss.
CREATE TABLE native_affinity_numeric (
    id INTEGER PRIMARY KEY,
    shape NUMERIC,
    flags NUMERIC,
    amount NUMERIC,
    payload NUMERIC,
    raw_bytes NUMERIC,
    counter NUMERIC,
    ratio NUMERIC
);

-- BLOB affinity: no conversion at all; the value keeps the type it was bound as.
CREATE TABLE native_affinity_blob (
    id INTEGER PRIMARY KEY,
    shape BLOB,
    flags BLOB,
    amount BLOB,
    payload BLOB,
    raw_bytes BLOB,
    counter BLOB,
    ratio BLOB
);
