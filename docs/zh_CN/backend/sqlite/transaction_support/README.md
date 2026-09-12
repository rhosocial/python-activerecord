# 事务支持

## 概述

SQLite 后端通过事务管理器提供完整的事务管理，该管理器封装了 SQLite 的事务语义。SQLite 默认支持具有 SERIALIZABLE 隔离级别的事务。

## 事务管理器

### 同步

```python
# 使用事务管理器
with User.transaction():
    user = User(username='alice')
    user.save()
    # 事务在成功退出时提交
    # 事务在异常时回滚
```

### 异步

```python
# 使用异步事务管理器
async with User.transaction():
    user = User(username='alice')
    await user.save()
    # 事务在成功退出时提交
    # 事务在异常时回滚
```

事务管理器有同步和异步两种变体：
- `SQLiteTransactionManager` — 同步
- `AsyncSQLiteTransactionManager` — 异步

API 是相同的——唯一的区别是 `async with` 与 `with`。

### 手动事务控制

```python
# 通过后端手动事务
backend = SQLiteBackend(database=":memory:")
backend.connect()

with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
    # 成功退出时提交

# 带显式回滚的事务
try:
    with backend.transaction():
        backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
        raise ValueError("Something went wrong")  # 回滚
except ValueError:
    pass  # Alice 未被插入
```

## Savepoints

SQLite 支持用于嵌套事务的 savepoints。每个嵌套的 `transaction()` 调用创建一个 savepoint，允许在较大事务内进行部分回滚。

```python
with backend.transaction():          # 外部事务
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    
    with backend.transaction():      # 创建 savepoint
        backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
        # 异常时回滚到 savepoint，外部事务继续
    
    # Alice 仍然被提交（如果外部事务成功）
```

### Savepoint 行为

| 场景 | 结果 |
|------|------|
| 内部事务成功 | Savepoint 释放，外部事务继续 |
| 内部事务引发异常 | 回滚到 savepoint，外部事务继续 |
| 外部事务成功 | 所有更改提交 |
| 外部事务引发异常 | 所有内容回滚 |

## 隔离级别

SQLite 默认使用 SERIALIZABLE 隔离级别，这是最严格的隔离级别。这可以防止脏读、不可重复读和幻读。

### SQLite 隔离特性

| 隔离级别 | 行为 |
|---------|------|
| SERIALIZABLE（默认） | 完全隔离；事务看起来串行执行 |
| DEFERRED | 在第一次读取时获取锁（`BEGIN` 的默认值） |
| IMMEDIATE | 启动时获取 RESERVED 锁 |
| EXCLUSIVE | 启动时获取 EXCLUSIVE 锁 |

### BEGIN 语句变体

SQLite 支持三种 BEGIN 模式：

```python
# DEFERRED（默认）——在第一次读/写之前不获取锁
BEGIN DEFERRED TRANSACTION

# IMMEDIATE —— 立即获取 RESERVED 锁
BEGIN IMMEDIATE TRANSACTION

# EXCLUSIVE —— 立即获取 EXCLUSIVE 锁
BEGIN EXCLUSIVE TRANSACTION
```

在 rhosocial-activerecord 中，事务管理器默认使用 `BEGIN DEFERRED`。锁在第一次数据库操作时延迟获取。

### 并发访问

SQLite 使用文件级锁来实现并发。当一个连接持有写锁时，其他连接会阻塞，直到锁被释放。

```python
# 连接 A
with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    # 持有写锁直到提交

# 连接 B —— 阻塞直到连接 A 提交
with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
```

为了更好的并发性，考虑使用 WAL 模式（请参阅 [Pragma 系统](../pragma.md)）。

## 另请参阅

- [Pragma 系统](../pragma.md) — 配置日志模式和锁定行为
- [故障排除](../troubleshooting/README.md) — 数据库锁定错误
- [核心：并行工作模式](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers)

💡 *AI 提示*："如何在 SQLite 中处理并发写入导致的数据库锁定错误？"
