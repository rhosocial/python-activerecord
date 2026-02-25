# 9. 后端系统 (Backend System)

这是高级主题，面向希望深入了解 ORM 内部工作原理或需要支持新数据库的用户。

## 后端生态系统

rhosocial-activerecord 的设计初衷是支持多数据库后端。除了核心库中包含的 SQLite 实现（其中异步 SQLite 主要用于测试验证），我们还提供或计划提供以下独立的后端包：

*   `rhosocial-activerecord-mysql`
*   `rhosocial-activerecord-postgres`
*   `rhosocial-activerecord-oracle` (计划中)
*   `rhosocial-activerecord-sqlserver` (计划中)
*   `rhosocial-activerecord-mariadb` (计划中)

这些独立的包也可以作为您开发自定义第三方后端的范例。

## 目录

*   **[表达式系统 (Expression System)](expression/README.md)**: Python 对象如何变成 SQL 字符串。
*   **[自定义后端 (Custom Backend)](custom_backend.md)**: 实现一个新的数据库驱动。

## 示例代码

本章的完整示例代码位于 `docs/examples/chapter_07_backend/`。
