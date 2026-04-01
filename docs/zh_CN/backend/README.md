# 9. 后端系统 (Backend System)

这是高级主题，面向希望深入了解 ORM 内部工作原理或需要支持新数据库的用户。

## 后端生态系统

rhosocial-activerecord 的设计初衷是支持多数据库后端。除了核心库中包含的 SQLite 实现，我们还提供或计划提供以下独立的后端包：

* `rhosocial-activerecord-mysql`
* `rhosocial-activerecord-postgres`
* `rhosocial-activerecord-oracle` (计划中)
* `rhosocial-activerecord-sqlserver` (计划中)
* `rhosocial-activerecord-mariadb` (计划中)

这些独立的包也可以作为您开发自定义第三方后端的范例。

## 同步与异步对等

核心库中包含的 SQLite 后端同时提供**同步**和**异步**实现，两者具有完全对等的 API：

- **同步 API**: `SQLiteBackend` — 使用标准 `sqlite3` 模块（内置）
- **异步 API**: `AsyncSQLiteBackend` — 需要安装 `aiosqlite` 包

两种实现拥有相同的方法签名、返回类型和行为，便于在需要时在同步和异步模式之间切换。

### 异步 SQLite 依赖

异步 SQLite 后端需要 `aiosqlite` 作为额外依赖。由于它不在核心依赖中，您需要手动安装：

```bash
pip install aiosqlite
```

或安装包含所有可选依赖的完整包：

```bash
pip install rhosocial-activerecord[all]
```

## 目录

* **[数据库内省 (Introspection)](introspection.md)**: 查询数据库结构元数据。
* **[查询解释接口 (Query Explain)](explain.md)**: 执行 EXPLAIN 语句，分析查询计划和索引使用情况。
* **[表达式系统 (Expression System)](expression/README.md)**: Python 对象如何变成 SQL 字符串。
* **[自定义后端 (Custom Backend)](custom_backend.md)**: 实现一个新的数据库驱动。
* **[SQLite 后端](sqlite/README.md)**: SQLite 特定功能和特性。
  * **[Pragma 系统](sqlite/pragma.md)**: SQLite PRAGMA 配置和查询。
  * **[扩展框架](sqlite/extension.md)**: 扩展检测和管理。
  * **[全文搜索 (FTS5)](sqlite/fts5.md)**: FTS5 全文搜索功能。

## 示例代码

本章的完整示例代码位于 `docs/examples/chapter_07_backend/`。
