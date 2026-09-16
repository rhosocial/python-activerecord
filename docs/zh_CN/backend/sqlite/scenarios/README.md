# 应用场景

## 并发特性

SQLite 是一个使用文件级锁来实现并发的嵌入式数据库。了解其并发模型对于选择正确的部署模式至关重要。

### SQLite 并发工作原理

SQLite 使用三种锁定状态：

| 锁定状态 | 描述 |
|---------|------|
| UNLOCKED | 未持有锁；连接可以读写 |
| SHARED | 读锁；多个连接可以同时读取 |
| RESERVED | 意向写入；没有其他连接可以开始写入 |
| EXCLUSIVE | 写锁；只有此连接可以读写 |

当连接获取 EXCLUSIVE 锁时，所有其他连接将阻塞，直到锁被释放。

### WAL 模式提供更好的并发性

WAL（预写日志）模式通过允许在写入期间并发读取显著提高了并发性：

```python
backend.execute("PRAGMA journal_mode = WAL")
```

| 模式 | 写入期间读取 | 读取期间写入 | 并发写入 |
|------|------------|------------|---------|
| DELETE（默认） | 否 | 否 | 否 |
| WAL | 是 | 是 | 否 |

即使在 WAL 模式下，一次也只能执行一个写入。但读取永远不会被写入阻塞。

## 部署模式

### 单进程应用

SQLite 非常适合没有网络访问的单进程应用：

```python
# 桌面应用
backend = SQLiteBackend(database="~/.myapp/data.db")
```

### 使用 WAL 的多进程

多个进程可以同时读取，但写入是串行的：

```
进程 A ──读取──→ [数据库]
进程 B ──读取──→ [数据库]
进程 C ──写入──→ [数据库]（阻塞直到完成）
```

### 不建议用于网络存储

不要在 NFS、SMB 或类似的网络文件系统上使用 SQLite。文件锁在网络上不能可靠工作，可能导致数据损坏。

| 存储类型 | 推荐 | 原因 |
|---------|------|------|
| 本地 SSD/HDD | 是 | 快速、可靠的锁 |
| USB 驱动器 | 注意 | 拔出时可能丢失数据 |
| NFS/SMB | 否 | 锁不可靠 |
| Docker 卷 | 是（本地） | 视为本地存储 |
| 云盘（EBS 等） | 注意 | 检查锁定语义 |

### 多用户 Web 应用

对于具有多个并发用户的 Web 应用，请考虑：

1. **SQLite + WAL** —— 适合读取密集型应用，写入不频繁
2. **MySQL/PostgreSQL** —— 更适合写入密集型应用或许多并发用户

```
# SQLite：适用于
- 个人博客、作品集
- 小型内部工具
- 读取密集型 API（< 10 个并发写入）

# 切换到 MySQL/PostgreSQL 用于
- 社交媒体平台
- 具有许多并发订单的电子商务
- 具有 > 10 个并发写入的应用
```

### 读副本

SQLite 不支持内置复制。对于读取密集型工作负载，您可以通过复制数据库文件实现应用级复制：

```python
import shutil

# 用于读副本的定期快照
shutil.copy2("main.db", "readonly_replica.db")
```

注意：这不是实时复制。如需真正的复制，请使用 MySQL 或 PostgreSQL。

## 性能提示

### 连接池

SQLite 是基于文件的数据库——没有传统意义上的连接池。每个连接直接打开文件。对于内存数据库，每个连接获得自己的独立数据库。

### PRAGMA 调优

```python
# 启用 WAL 以获得更好的并发性
backend.execute("PRAGMA journal_mode = WAL")

# 增加缓存大小（默认是 2000 页 ≈ 8MB）
backend.execute("PRAGMA cache_size = -64000")  # 64MB

# 大型数据库的内存映射 I/O
backend.execute("PRAGMA mmap_size = 268435456")  # 256MB

# 为 WAL 优化同步模式
backend.execute("PRAGMA synchronous = NORMAL")
```

## 另请参阅

- [故障排除](../troubleshooting/README.md) — 常见问题和解决方案
- [事务支持](../transaction_support/README.md) — 事务管理
- [核心并行工作模式](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers)

💡 *AI 提示*："我应该在什么时候使用 SQLite，什么时候使用 MySQL 或 PostgreSQL？"
