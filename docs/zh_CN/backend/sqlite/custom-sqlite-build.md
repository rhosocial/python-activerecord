# 自定义 SQLite 编译用于测试

## 背景

Ubuntu 26.04 自带 SQLite 3.46.1，但未启用 `SQLITE_ENABLE_GEOPOLY`。
Geopoly 是 `rhosocial-activerecord` 支持的 SQLite 扩展之一，需要自定义 SQLite 编译以测试它。

Python 3.14 的 `_sqlite3` 模块**动态链接**到系统 `libsqlite3.so.0`，
因此可以通过 `LD_PRELOAD` 替换运行时加载的库，无需重新编译 Python。

## 编译自定义 libsqlite3.so

### 1. 下载合并源码

```bash
wget https://www.sqlite.org/2025/sqlite-amalgamation-3490100.zip
unzip sqlite-amalgamation-3490100.zip
```

### 2. 编译

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

### 3. 安装

```bash
mkdir -p /path/to/project/.sqlite-custom
cp libsqlite3_custom.so /path/to/project/.sqlite-custom/
```

### 4. 使用

```bash
LD_PRELOAD=.sqlite-custom/libsqlite3_custom.so pytest tests/...
LD_PRELOAD=.sqlite-custom/libsqlite3_custom.so python examples/...
```

## 工作原理

```
Python _sqlite3.cpython-314-x86_64-linux-gnu.so
  └─ libsqlite3.so.0 → /usr/lib/x86_64-linux-gnu/libsqlite3.so.0 (3.46.1)

使用 LD_PRELOAD 后：
  └─ libsqlite3_custom.so (3.49.1, +GEOPOLY)  ← 优先加载
  └─ libsqlite3.so.0 (3.46.1)                  ← 被忽略
```

## 当前编译产物

- 位置：`.sqlite-custom/libsqlite3_custom.so`
- 版本：SQLite 3.49.1
- 启用扩展：FTS5, R-Tree, Geopoly, JSON1, Math Functions

## 注意事项

- `LD_PRELOAD` 仅影响当前 shell 会话
- `sqlite3` 命令行工具等系统工具不受影响
- 升级方式：下载新版 amalgamation，重复编译步骤即可
- 体积优化：`strip libsqlite3_custom.so` 可将 ~1.7 MB 降至 ~800 KB