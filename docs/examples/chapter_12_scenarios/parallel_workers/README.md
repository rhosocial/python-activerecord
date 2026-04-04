# 并行 Worker 场景实验

本目录包含《场景实战 — 并行 Worker》章节的完整可运行实验代码，所有示例均使用真实的 `rhosocial-activerecord` ORM，模型体系为：

```text
User --has_many--> Post --has_many--> Comment
User <--belongs_to-- Post
Post <--belongs_to-- Comment
User <--belongs_to-- Comment （评论作者）
```

每个模型提供**同步版**（继承 `ActiveRecord`）和**异步版**（继承 `AsyncActiveRecord`），方法名完全相同，异步版仅需加 `await`。

## 实验列表

| 文件 | 主题 | 类型 |
| ---- | ---- | ---- |
| `setup_db.py` | 初始化数据库和测试数据 | 工具 |
| `models.py` | 共享 ActiveRecord 模型定义（同步 + 异步） | 公共 |
| `exp1_basic_multiprocess.py` | 多进程正确用法 + 串行/并行耗时对比 | ✅ 正确示范 |
| `exp2_sqlite_wal_mode.py` | SQLite WAL 模式 vs 默认模式性能对比 | ✅ 正确示范 |
| `exp3_deadlock_wrong.py` | 无原子领取导致重复处理 | ❌ 反面教材 |
| `exp4_partition_correct.py` | 数据分区 + 原子领取（同步/异步各两种方案） | ✅ 正确示范 |
| `exp5_multithread_warning.py` | 多线程共享连接的问题 | ❌ 反面教材 |

## 快速开始

### 1. 激活虚拟环境

```bash
# 在 python-activerecord 项目根目录
source .venv3.9-examples/bin/activate   # 或对应的 .venv* 变体
```

### 2. 进入实验目录

```bash
cd docs/examples/chapter_12_scenarios/parallel_workers
```

### 3. 初始化数据库

**每次运行实验前必须先执行此步骤**（实验脚本会修改数据库状态）：

```bash
python setup_db.py          # 同步初始化（默认）
python setup_db.py --async  # 异步初始化（效果相同）
```

预期输出：

```text
已删除旧数据库：parallel_workers.db
=== 同步初始化模式 ===

建表完成，开始插入测试数据…
  User #1: user01
  ...
  共插入 20 篇文章
  共插入 60 条评论

✓ 同步初始化完成：parallel_workers.db
  用户 5 / 文章 20 / 评论 60
```

### 4. 运行实验

各实验相互独立，每次运行前先执行 `setup_db.py` 重置数据库：

```bash
python setup_db.py && python exp1_basic_multiprocess.py
python setup_db.py && python exp2_sqlite_wal_mode.py
python setup_db.py && python exp3_deadlock_wrong.py
python setup_db.py && python exp4_partition_correct.py
python setup_db.py && python exp5_multithread_warning.py
```

## 实验说明

### exp1：基础多进程用法

演示最核心的原则：**`configure()` 必须在子进程内调用**。

对比三种处理方式的耗时：

- **实验 A**：串行（单进程，同步 ActiveRecord）
- **实验 B**：4 进程并行（同步 ActiveRecord）
- **实验 C**：4 进程并行（异步 ActiveRecord，每进程内 asyncio 驱动）

同时演示 `BelongsTo` 关联遍历（`post.author()`）的正确用法。

预期输出（参考）：

```text
共找到 10 篇已发布文章

=== 实验 A：串行处理（单进程，同步 ActiveRecord）===
串行完成 10 篇，耗时 0.XXXs

=== 实验 B：4 进程并行（同步 ActiveRecord）===
  [sync PID XXXXX] 完成 X 篇文章
  ...
并行完成 10 篇，耗时 0.XXXs

=== 实验 C：4 进程并行（异步 ActiveRecord）===
  [async PID XXXXX] 完成 X 篇文章
  ...
```

> **注意**：数据量较小（10 篇文章）时，进程启动开销大于任务本身，多进程不一定更快。生产环境数据量大时效果显著。

### exp2：SQLite WAL 模式

展示在多进程并发写入场景下，WAL 模式相比默认 DELETE 模式的性能对比。提供同步和异步两个版本，验证方法名完全相同。

预期输出（参考）：

```text
=== 同步版：默认模式 vs WAL 模式 ===
  同步-默认模式: 处理 20 篇文章，耗时 X.XXXs
  同步-WAL 模式: 处理 20 篇文章，耗时 X.XXXs

=== 异步版：默认模式 vs WAL 模式 ===
  异步-默认模式: 处理 20 篇文章，耗时 X.XXXs
  异步-WAL 模式: 处理 20 篇文章，耗时 X.XXXs
```

### exp3：反面教材 — 重复处理

故意展示"读后改"模式导致多 Worker 重复领取同一批文章的竞态条件。

预期输出（参考）：

```text
=== 错误模式：无原子领取（竞态条件）===
  ⚠️  发现 X 篇文章被多个 Worker 同时处理：
     Post #1 被 Worker [0, 1, 2, 3] 同时领取
     ...
```

**重要提示**：这是反面教材，仅用于教学目的。

### exp4：正确的并行方案

提供四种生产可用的并行策略（同步/异步 × 分区/原子领取）：

- **方案 A 同步**：按 `user_id` 分区，遍历 `HasMany` 关联（`post.comments()`）统计评论数
- **方案 A 异步**：同上，加 `await`（`await post.comments()`）
- **方案 B 同步**：`with Post.transaction()` 原子领取
- **方案 B 异步**：`async with AsyncPost.transaction()` 原子领取

预期输出（参考）：

```text
=== 方案 A：数据分区（同步 ActiveRecord）===
  结果：Worker 共处理 20 篇，发布 20 篇，耗时 X.XXXs ✅ 无重复

=== 方案 A：数据分区（异步 ActiveRecord）===
  结果：Worker 共处理 20 篇，发布 20 篇，耗时 X.XXXs ✅ 无重复

=== 方案 B：原子领取（同步 ActiveRecord）===
  结果：Worker 共处理 20 篇，发布 20 篇，耗时 X.XXXs ✅ 无重复

=== 方案 B：原子领取（异步 ActiveRecord）===
  结果：Worker 共处理 20 篇，发布 20 篇，耗时 X.XXXs ✅ 无重复

总体验证：✅ 所有方案均无重复处理
```

### exp5：反面教材 — 多线程问题

展示三个多线程陷阱：

- **场景 0**：`check_same_thread=True`（默认）跨线程访问直接报错
- **场景 1**：共享 `__backend__` — 多线程共用同一连接（危险）
- **场景 2**：每线程 `configure()` — 类属性互相覆盖（无效）

预期输出（参考）：

```text
=== 场景 0：验证 check_same_thread 默认值 ===
  check_same_thread=True  → ❌ DatabaseError: SQLite objects created in a thread...
  check_same_thread=False → ✅ 无报错（但不保证线程安全）

=== 场景 2：每线程调用 configure()（❌ 无效，类属性被互相覆盖）===
  4 个线程各自 configure()，实际 backend 实例数：1（应为 4，实为 1）
```

## 关联关系访问说明

同步关联返回可调用函数，需要加 `()` 才能触发查询：

```python
# 同步 BelongsTo
author = post.author()          # ✅ 正确，返回 User 实例或 None
author = post.author            # ❌ 错误，返回函数对象

# 同步 HasMany
comments = post.comments()      # ✅ 正确，返回 list[Comment]
comments = post.comments        # ❌ 错误，返回函数对象

# 异步 BelongsTo（加 await + 括号）
author = await post.author()    # ✅ 正确
author = await post.author      # ❌ 错误

# 异步 HasMany
comments = await post.comments()  # ✅ 正确
comments = await post.comments    # ❌ 错误
```

## 常见问题

**Q: 运行实验时报 "database is locked"，怎么处理？**

A: 可能是上次实验未正常结束，数据库锁未释放。重新运行 `setup_db.py` 创建新数据库即可。

**Q: 实验 3 每次运行都出现了重复，是预期的吗？**

A: 是的。这是反面教材，4 个进程同时查询相同的 5 篇 draft 文章，竞态条件几乎必然触发。

**Q: 实验 1 的加速比看起来很低甚至小于 1，正常吗？**

A: 正常。测试数据量很小（10 篇文章），进程启动和序列化开销远大于任务本身。生产环境处理大量数据时并行效果才会显著。

**Q: `post.author` 和 `post.author()` 有什么区别？**

A: `post.author` 返回一个绑定到该实例的关联方法（函数对象），`post.author()` 才会实际查询数据库并返回关联对象。异步版本同理：`await post.author()` 才是正确写法。
