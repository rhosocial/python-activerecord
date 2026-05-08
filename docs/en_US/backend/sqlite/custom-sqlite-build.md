# Custom SQLite Build for Testing

## Background

Ubuntu 26.04 ships with SQLite 3.46.1, which lacks `SQLITE_ENABLE_GEOPOLY`.
The Geopoly extension is one of the SQLite extensions that `rhosocial-activerecord`
supports, so a custom SQLite build is needed to test it.

Python 3.14's `_sqlite3` module is **dynamically linked** to the system
`libsqlite3.so.0`, so we can replace the runtime library via `LD_PRELOAD`
without recompiling Python.

## Build Custom libsqlite3.so

### 1. Download Amalgamation

```bash
wget https://www.sqlite.org/2025/sqlite-amalgamation-3490100.zip
unzip sqlite-amalgamation-3490100.zip
```

### 2. Compile

```bash
cd sqlite-amalgamation-3490100
gcc -shared -fPIC -o libsqlite3_custom.so sqlite3.c \
    -DSQLITE_ENABLE_FTS5 \
    -DSQLITE_ENABLE_RTREE \
    -DSQLITE_ENABLE_GEOPOLY \
    -DSQLITE_ENABLE_JSON1 \
    -DSQLITE_ENABLE_COLUMN_METADATA \
    -DSQLITE_ENABLE_UNLOCK_NOTIFY \
    -DSQLITE_ENABLE_DBSTAT_VTAB \
    -DSQLITE_ENABLE_MATH_FUNCTIONS \
    -DSQLITE_ENABLE_STMT_SCANSTATUS \
    -lpthread -lm -ldl
```

### 3. Install

```bash
mkdir -p /path/to/project/.sqlite-custom
cp libsqlite3_custom.so /path/to/project/.sqlite-custom/
```

### 4. Use

```bash
LD_PRELOAD=.sqlite-custom/libsqlite3_custom.so pytest tests/...
LD_PRELOAD=.sqlite-custom/libsqlite3_custom.so python examples/...
```

## How It Works

```
Python _sqlite3.cpython-314-x86_64-linux-gnu.so
  └─ libsqlite3.so.0 → /usr/lib/x86_64-linux-gnu/libsqlite3.so.0 (3.46.1)

With LD_PRELOAD:
  └─ libsqlite3_custom.so (3.49.1, +GEOPOLY)  ← loaded first
  └─ libsqlite3.so.0 (3.46.1)                  ← ignored
```

## Current Build

- Location: `.sqlite-custom/libsqlite3_custom.so`
- Version: SQLite 3.49.1
- Enabled: FTS5, R-Tree, Geopoly, JSON1, Math Functions

## Notes

- `LD_PRELOAD` only affects the current shell session
- System tools like the `sqlite3` CLI are unaffected
- To upgrade: re-download a newer amalgamation and repeat step 2
- To reduce file size: `strip libsqlite3_custom.so` (~1.7 MB → ~800 KB)