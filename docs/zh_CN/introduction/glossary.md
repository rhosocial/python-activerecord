# 术语表

本文档解释了文档中使用的关键术语和概念。

## 核心概念

### Active Record 模式
一种设计模式，数据库表或视图被封装成一个类。因此，一个对象实例绑定到表中的一行。创建对象后，保存时会向表中添加新行。加载的任何对象都从数据库获取信息；当对象更新时，表中的对应行也会更新。

**在 rhosocial-activerecord 中：** 你的模型类（如 `User`、`Post`）继承自 `ActiveRecord` 并自动映射到数据库表。

> 💡 **AI 提示词：** "解释 Active Record 模式，并与 Repository 模式和 Data Mapper 模式进行比较。"

### Pydantic
一个使用 Python 类型提示进行数据验证的 Python 库。它确保数据在运行时符合指定的类型和约束。

**主要特性：**
- 类型安全的数据验证
- JSON 序列化/反序列化
- 自动错误信息
- 通过类型提示提供 IDE 支持

**本项目的版本要求：**
- Python 3.8/3.9: `pydantic>=2.10.6`
- Python 3.10+: `pydantic>=2.12`
- 支持 Python 3.13/3.14 自由线程版

> 💡 **AI 提示词：** "什么是 Pydantic？它与传统的 Python dataclasses 或 marshmallow 有什么区别？"

### ORM（对象关系映射）
一种让你可以使用面向对象范式而不是 SQL 来查询和操作数据库数据的技术。

**为什么要用 ORM？**
- 编写数据库无关的代码
- 使用对象而不是 SQL 字符串
- 自动数据验证和类型安全
- 更容易维护和测试

> 💡 **AI 提示词：** "使用 ORM 和编写原始 SQL 相比有什么优缺点？"

## 架构术语

### Expression-Dialect 分离
我们的核心架构原则，将**你想要什么**（Expression）与**如何为其生成 SQL**（Dialect）分离。

**好处：**
- 相同的 Python 代码适用于不同的数据库
- SQL 生成是透明且可测试的
- 易于添加新的数据库后端

> 💡 **AI 提示词：** "解释 Expression-Dialect 分离，以及为什么它比 SQL 字符串拼接更好。"

### FieldProxy
一种类型安全的方式在查询中引用模型字段。不使用容易拼错的字符串名称，而是使用 `User.c.username`，它提供 IDE 自动补全和类型检查。

**示例：**
```python
# ❌ 基于字符串（容易出错）
User.query().where("username == 'alice'")

# ✅ FieldProxy（类型安全）
User.query().where(User.c.username == "alice")
```

> 💡 **AI 提示词：** "FieldProxy 如何在 Python 中实现类型安全的查询构建？"

### ToSQLProtocol
所有表达式类都实现的协议（接口）。它要求有一个 `.to_sql()` 方法，返回 SQL 字符串和参数。

**目的：**
- 表达式和基于表达式的查询都可以在执行前显示其生成的 SQL
- 无需数据库连接即可进行测试
- 使 SQL 生成透明化

> 💡 **AI 提示词：** "Python 中的 Protocol 是什么？ToSQLProtocol 如何实现透明的 SQL 生成？"

## 设计原则

### 同步异步对等（Sync-Async Parity）
我们的设计原则，即同步和异步 API 应该具有：
- **相同的方法名**（没有 `_async` 后缀）
- **相同的功能**（只需为 async 添加 `await`）
- **相同的代码模式**

**为什么？** 使将同步代码转换为异步变得容易，无需学习新的 API。

> 💡 **AI 提示词：** "为什么这个项目要求同步和异步 API 使用相同的方法名？这样做有什么好处？"

### 渐进式 ORM（Gradual ORM）
我们的理念，即你应该能够在不同抽象级别使用 ORM：
- **高级：** 具有验证的完整 ActiveRecord 对象
- **中级：** 具有类型安全的查询构建
- **低级：** 在需要性能时使用原始 SQL

你选择适合你用例的级别。

> 💡 **AI 提示词：** "什么是'渐进式 ORM'？它与强迫你遵循其模式的传统 ORM 有什么不同？"

## 数据库术语

### Mixin
一个通过继承为其他类提供方法和字段的类。在我们的项目中，Mixin 添加通用功能，如时间戳、UUID 或软删除。

**示例：**
```python
class Post(DefaultTimestampMixin, UUIDMixin, ActiveRecord):
    # 自动获得 created_at、updated_at 和 UUID id
    title: str
```

> 💡 **AI 提示词：** "Python 中的 Mixin 模式是什么？它如何实现代码复用？"

### 后端（Backend）
数据库特定的实现，处理：
- 数据库连接
- SQL 执行
- 事务管理
- 类型适配

**可用的后端：**
- SQLite（内置）
- MySQL（单独包）
- MariaDB（单独包）
- PostgreSQL（单独包）
- SQL Server（单独包）
- Oracle（单独包）
- Firebird（单独包）
- BigQuery（单独包）
- ClickHouse（单独包）
- Snowflake（单独包）

> 💡 **AI 提示词：** "Backend 在这个架构中的作用是什么？它如何实现数据库无关性？"

### 方言（Dialect）
一个知道如何生成数据库特定 SQL 语法的组件。不同的数据库有不同的：
- 参数占位符样式（`?` vs `$1` vs `:name`）
- 函数名称和语法
- 分页方法（LIMIT vs ROW_NUMBER）

> 💡 **AI 提示词：** "Dialect 组件如何使相同的 Python 代码适用于不同的数据库？"

## 常见缩写

- **AR**: Active Record
- **ORM**: Object-Relational Mapping（对象关系映射）
- **API**: Application Programming Interface（应用程序接口）
- **SQL**: Structured Query Language（结构化查询语言）
- **DB**: Database（数据库）
- **CTE**: Common Table Expression（公用表表达式，WITH 子句）
- **CRUD**: Create, Read, Update, Delete（创建、读取、更新、删除）
- **PK**: Primary Key（主键）
- **FK**: Foreign Key（外键）

## 另请参阅

- [来自其他框架](coming_from_frameworks.md) - 如果你熟悉 Django、SQLAlchemy 或 Rails
- [AI 辅助开发](ai_assistance.md) - 如何使用 AI 解释这些概念
- [架构设计](architecture.md) - 深入系统设计
