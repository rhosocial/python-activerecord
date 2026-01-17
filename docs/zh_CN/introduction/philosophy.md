# 设计哲学 (Philosophy)

`rhosocial-activerecord` 的设计不仅是为了提供一个操作数据库的工具，更是为了在现代 Python 应用开发中建立一种严谨、高效且灵活的数据交互范式。

我们的核心设计哲学主要体现在以下三个方面：

## 1. 分层架构：Backend 与 ActiveRecord

传统的 ORM 往往将数据库连接管理与模型定义紧密耦合。我们在设计上明确区分了 **Backend（后端）** 和 **ActiveRecord（活动记录）** 两部分。

*   **Backend (后端)**: 负责底层的数据库连接、SQL 执行和方言处理。它是一个完全独立的组件，不依赖于任何模型定义。
*   **ActiveRecord**: 它是 Backend 的“用户”。ActiveRecord 利用 Backend 提供的能力来完成数据的持久化和查询。

这种分离意味着 **Backend 完全可以独立工作**。你可以在不定义任何 Model 的情况下，直接使用 Backend 执行原生 SQL，管理事务，或者构建自定义的数据访问层。ActiveRecord 只是构建在这一坚实基础之上的高级抽象。

此外，**Backend 自身还提供了一套强大的“表达式-方言”系统**。这一设计使得我们可以轻松扩展对主流关系型数据库的支持。目前，我们已经提供了对 **SQLite3** 的最新支持，并计划或已提供以下扩展，致力于让用户在不同数据库间获得一致的开发体验：

*   **MySQL**
*   **PostgreSQL**
*   **Oracle** (计划中)
*   **SQL Server** (计划中)
*   **MariaDB** (计划中)

## 2. 类型安全与数据校验

我们深知良好范式对于系统稳定性和开发效率的关键性影响。因此，在数据模型层的设计上，我们做出了一个关键决定：

**让 ActiveRecord 直接继承自 `pydantic.BaseModel` (Pydantic V2)。**

我们没有选择自己实现一套验证系统，原因很简单：
*   **成熟度**: Pydantic 已经是 Python 生态中事实上的数据验证标准，极其成熟且功能强大。
*   **成本**: 自己从头实现一套达到同等水平的验证系统成本极高且容易引入 Bug。
*   **生态**: 能够直接享受 Pydantic 庞大的生态系统（如 FastAPI 集成、IDE 智能提示等）。

通过这一继承关系，每一个 ActiveRecord 模型本质上都是一个 Pydantic 模型，拥有强大的运行时类型检查和数据校验能力，确保入库数据的绝对纯净。

## 3. 强大的查询系统

ActiveRecord 不仅仅是数据模型，它还搭配了一套强大的查询体系，主要包括：

*   **ActiveQuery**: 标准的查询构建器。
*   **CTEQuery**: 通用表表达式（Common Table Expressions）查询。
*   **SetOperationQuery**: 集合操作查询（如 Union, Intersect）。

**ActiveQuery 的核心使命是实例化 ActiveRecord 实例（列表）**。当你执行 `User.query().where(...)` 时，默认返回的是经过完整校验的 `User` 对象列表。

同时，为了满足性能敏感场景的需求，`ActiveQuery` 与 `CTEQuery`、`SetOperationQuery` 一致，都提供了 **`aggregate()`** 功能。这允许你在需要时跳过模型实例化，直接获取聚合数据或原始字典结果，从而在灵活性和性能之间取得完美平衡。
