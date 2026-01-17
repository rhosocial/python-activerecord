<!-- TRANSLATION PENDING -->

# 7. 后端系统 (Backend System)

这是高级主题，面向希望深入了解 ORM 内部工作原理或需要支持新数据库的用户。

## Backend Ecosystem

The design intent of `rhosocial-activerecord` is to support multiple database backends. In addition to the SQLite implementation included in the core library (where the asynchronous SQLite is primarily for testing verification), we also provide or plan to provide the following independent backend packages:

*   `rhosocial-activerecord-mysql`
*   `rhosocial-activerecord-postgres`
*   `rhosocial-activerecord-oracle` (Planned)
*   `rhosocial-activerecord-sqlserver` (Planned)
*   `rhosocial-activerecord-mariadb` (Planned)

These independent packages can also serve as examples for you to develop custom third-party backends.

## Contents

*   **[表达式系统 (Expression System)](expression.md)**: Python 对象如何变成 SQL 字符串。
*   **[自定义后端 (Custom Backend)](custom_backend.md)**: 实现一个新的数据库驱动。

## 示例代码

本章的完整示例代码位于 `docs/examples/chapter_07_backend/`。
