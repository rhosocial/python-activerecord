# 故障排除

本节介绍 SQLite 后端的常见问题及其解决方案。

## 数据库锁定

### 症状

```
sqlite3.OperationalError: database is locked
```

### 原因

SQLite 使用文件级锁。当一个连接持有写锁时，其他连接会阻塞。如果连接持有锁的时间过长（例如在长时间运行的事务中），其他连接可能会超时。

### 解决方案

1. **启用 WAL 模式** —— 允许在写入期间并发读取：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database="my.db")
backend.connect()
backend.execute("PRAGMA journal_mode = WAL")
```

2. **设置 busy timeout** —— 在失败前等待更长时间：

```python
backend.execute("PRAGMA busy_timeout = 5000")  # 5 秒
```

3. **缩短事务** —— 尽快提交

4. **使用内存数据库进行测试** —— 不涉及文件锁：

```python
backend = SQLiteBackend(database=":memory:")
```

## WAL 模式问题

### 症状

WAL 文件（`.db-wal`）未被清理，或数据库比预期大。

### 解决方案

WAL 模式需要定期检查点。强制执行检查点：

```python
backend.execute("PRAGMA wal_checkpoint(TRUNCATE)")
```

或设置自动检查点间隔：

```python
backend.execute("PRAGMA wal_autocheckpoint = 1000")  # 每 1000 页
```

## VACUUM 限制

### 症状

```
sqlite3.OperationalError: cannot VACUUM from within a transaction
```

### 原因

VACUUM 重建整个数据库文件，不能在事务内运行。

### 解决方案

确保没有活动事务：

```python
# 错误——在事务内
with backend.transaction():
    backend.execute("VACUUM")  # 错误！

# 正确——在事务外
backend.execute("VACUUM")
```

## ALTER TABLE 限制

### 症状

```
sqlite3.OperationalError: near "ALTER": syntax error
```

### 原因

SQLite 的 ALTER TABLE 有限。您不能 ALTER COLUMN，而 RENAME/DROP COLUMN 需要特定版本。

### 解决方案

| 操作 | 最低版本 | 旧版本的解决方法 |
|------|---------|----------------|
| RENAME COLUMN | 3.25.0+ | 使用新列名重新创建表 |
| DROP COLUMN | 3.35.0+ | 不包含该列重新创建表 |
| ALTER COLUMN 类型 | 不支持 | 使用新类型重新创建表 |

对于列类型更改，请使用标准方法：

```python
# 1. 创建新表
# 2. 使用转换复制数据
# 3. 删除旧表
# 4. 重命名新表
```

## AUTOINCREMENT 问题

### 症状

ID 有间隙，或大量删除后性能下降。

### 原因

AUTOINCREMENT 阻止 rowid 重用并维护一个单独的 `sqlite_sequence` 表。删除的 ID 永远不会被重用。

### 解决方案

对于大多数情况，省略 AUTOINCREMENT。隐式 rowid 行为分配下一个可用值：

```python
# 不使用 AUTOINCREMENT——更快，允许 rowid 重用
class User(ActiveRecord):
    id: int | None = None  # INTEGER PRIMARY KEY（隐式 rowid）
    name: str
```

## 网络存储

### 症状

在 NFS/网络驱动器上频繁出现数据库锁定错误或数据损坏。

### 原因

SQLite 使用的文件锁在网络文件系统上不能可靠工作。

### 解决方案

不要在 NFS、SMB 或类似的网络存储上使用 SQLite。对于需要网络访问的数据库，请使用 MySQL、PostgreSQL 或其他客户端-服务器数据库。

## 内存数据库的内存问题

### 症状

使用 `:memory:` 数据库和多个连接时，应用程序内存增长。

### 原因

每个连接到 `:memory:` 都会创建一个独立的、隔离的数据库。它们不共享数据。

### 解决方案

- 对内存数据库使用单个连接
- 对于测试，使用带 URI 的共享内存数据库：

```python
backend = SQLiteBackend(database="file::memory:?cache=shared", uri=True)
```

## 另请参阅

- [Pragma 系统](../pragma.md) — 配置 SQLite 行为
- [事务支持](../transaction_support/README.md) — 事务管理
- [应用场景](../scenarios/README.md) — 并发和部署模式
- [核心：故障排除](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/getting_started/troubleshooting)

💡 *AI 提示*："是什么导致 SQLite 中的数据库锁定错误，如何修复它们？"
