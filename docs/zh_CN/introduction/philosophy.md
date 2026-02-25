# 设计哲学 (Philosophy)

`rhosocial-activerecord` 的设计不仅是为了提供一个操作数据库的工具，更是为了在现代 Python 应用开发中建立一种严谨、高效且灵活的数据交互范式。

## 为什么我们要做这个

在深入技术细节之前，让我们先回答一个根本问题：**既然 SQLAlchemy 和 Django 已经存在，为什么还要创建另一个 ORM？**

### 1. ActiveRecord 模式符合直觉

ActiveRecord 模式——一个类代表数据库表，一个实例代表一行——本质上非常直观：

```python
user = User(name="Alice")  # 创建一个实例（代表一行）
user.save()                # 持久化到数据库
user.name = "Bob"          # 修改属性
user.save()                # 在数据库中更新
```

这直接映射了开发者对数据的思考方式："我有一个用户，我保存这个用户，我修改这个用户，我再保存。" 心智模型简单且一致。

#### 历史背景：从 Fowler 到 Rails 再到我们

ActiveRecord 模式最早由 **Martin Fowler** 在他 2003 年的著作《企业应用架构模式》(*Patterns of Enterprise Application Architecture*) 中正式描述。Fowler 最初的设想非常优雅简洁：

> "一个对象，它包装数据库表或视图中的一行，封装数据库访问，并在该数据上添加领域逻辑。"

**Fowler 原始 ActiveRecord 的关键特征：**
- 单个类同时处理数据访问和领域逻辑
- 实例变量直接映射到数据库列
- 内置标准 CRUD 操作（创建、读取、更新、删除）
- 简单、直接、易于理解

**Rails (2004) 普及了 ActiveRecord** 但添加了自己的约定：
- 约定优于配置（复数化、外键命名）
- 丰富的回调系统（before_save、after_create 等）
- 通过方法链构建查询
- 与 Rails 框架紧密集成

**Yii2 (2014) 将 ActiveRecord 引入 PHP**，采用类似模式但添加了：
- 关系数据延迟加载
- 数据库无关的查询构建
- 集成到模型中的验证规则

#### 我们的改进：现代 Python 的 ActiveRecord

我们站在这些巨人的肩膀上，但针对现代 Python 生态系统做出了显著改进：

**1. 通过 Pydantic V2 实现类型安全**
- Rails 使用动态类型；我们利用 Python 的类型提示
- FieldProxy 提供了 Ruby 无法匹敌的编译时安全性
- 开箱即用的 IDE 自动补全和重构支持

**2. 真正的同步异步对等**
- Rails 很晚才添加异步支持（Rails 7+）；我们从第一天就为其设计
- 同步和异步的 API 表面相同——没有认知开销
- 原生异步实现，不是基于 greenlet 的包装器

**3. 框架独立性**
- Rails ActiveRecord 与 Rails 紧密耦合
- Yii2 ActiveRecord 需要 Yii2 框架
- **我们无处不在**：Flask、FastAPI、Django、脚本、Jupyter、CLI 工具

**4. SQL 透明性**
- Rails 的查询构建可能不透明（魔法作用域、复杂连接）
- 所有表达式以及基于表达式的查询都可以随时调用 `.to_sql()` 方法以方便调试
- Expression-Dialect 分离使 SQL 生成易于理解

**5. 表达式-方言架构与后端协议机制**

与 Rails 和 Yii2 将查询构建与其 ORM 层紧密耦合不同，我们实现了**关注点清晰分离**：

- **表达式系统（Expression System）**：定义*你想要什么*（例如 `User.c.age > 18`）
- **方言（Dialect）**：处理*如何*为不同数据库生成 SQL
- **后端协议（Backend Protocol）**：管理数据库连接和执行

**这种架构带来了：**

**a) ActiveRecord 级别的跨后端兼容性**
```python
# 相同的模型，不同的后端——只需更改配置
User.configure(sqlite_config, SQLiteBackend)   # SQLite
User.configure(mysql_config, MySQLBackend)     # MySQL  
User.configure(postgres_config, PostgresBackend)  # PostgreSQL
```

**b) 后端可扩展性**
添加对新数据库（Oracle、SQL Server 等）的支持只需要：
1. 实现一个新的 `Dialect` 子类用于 SQL 生成
2. 实现一个新的 `Backend` 子类用于连接管理
3. 无需更改 ActiveRecord、查询构建器或表达式

**c) 直接使用表达式（绕过 ActiveRecord）**
高级用户可以不通过 ActiveRecord 而直接使用表达式和后端：

```python
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# 直接创建表达式
col = Column("users", "age")
expr = col > Literal(18)

# 通过方言生成 SQL
sql, params = expr.to_sql(backend.dialect)
# SQL: "users"."age" > ?
# params: (18,)

# 直接通过后端执行（不需要 ActiveRecord）
backend.execute(sql, params)
```

**d) 框架灵活性——构建你自己的 ORM**
表达式-方言-后端堆栈是完全独立的。你可以：
- 使用它来构建**Data Mapper**模式 ORM 而不是 ActiveRecord
- 创建带有自定义查询构建器的**Repository**模式
- 实现**CQRS**（命令查询职责分离），使用不同的读/写模型
- 构建将查询转换为优化 SQL 表达式的 **GraphQL 解析器**

```python
# 示例：构建自定义 Repository 模式
class UserRepository:
    def __init__(self, backend):
        self.backend = backend
    
    def find_active(self, min_age: int):
        # 直接使用表达式系统
        expr = (User.c.active == True) & (User.c.age >= min_age)
        sql, params = expr.to_sql(self.backend.dialect)
        return self.backend.execute(sql, params)
```

**Rails 和 Yii2 无法提供这种架构级别的灵活性。** 它们的查询构建器与其 ActiveRecord 实现紧密耦合。

> 💡 **AI 提示词：** "比较 ActiveRecord 模式和 Data Mapper 模式。在简单性与灵活性方面各有什么取舍？"

**6. AI 原生设计**
- 内置对 AI 代码智能体的支持（Claude Code、OpenCode、Cursor）
- 用于自动化代码生成的技能和命令
- 帮助 AI 理解代码库的上下文文件

### 2. Python 缺乏成熟的 ActiveRecord 生态

虽然 Python 有优秀的 ORM，但生态中仍存在空白：

*   **SQLAlchemy** 遵循 Data Mapper 模式，具有复杂的多层架构（Core + ORM）。它功能强大但学习曲线陡峭。它**不是** ActiveRecord 实现。
*   **Django ORM** 与 Django Web 框架紧密耦合。你无法在独立脚本、FastAPI 应用或数据处理管道中使用它，而不 dragging in 整个 Django 生态系统。
*   **Peewee** 和 **Pony ORM** 虽然存在，但缺乏全面的功能集、异步支持，或对现代 Python 版本的积极维护。

**Python 需要一个独立的、功能完整的、现代的 ActiveRecord 实现。**

### 3. 不是包装器——而是从头实现

与那些包装 SQLAlchemy 的项目不同，**rhosocial-activerecord 是从头构建的**，只有 Pydantic 一个依赖：

```
你的代码 → rhosocial-activerecord → 数据库驱动 → 数据库
     ↑
     └── 下面没有 SQLAlchemy
     └── 没有 Django 依赖
     └── 只有 Pydantic 用于验证
```

这意味着：
- **零隐藏复杂性** —— 你控制每一层
- **完全的 SQL 透明性** —— 表达式和查询都可以调用 `.to_sql()` 方法查看生成的 SQL
- **更小的体积** —— 只有一个外部依赖
- **更简单的心智模型** —— 只需理解一层，而不是三层

> 💡 **AI 提示词：** "从头构建一个 ORM 与包装现有 ORM（如 SQLAlchemy）相比，各有什么优缺点？"

### 4. 设计上与框架无关

我们刻意**避免与任何 Web 框架耦合**：

| | rhosocial-activerecord | Django ORM |
|---|---|---|
| **依赖** | 仅 Pydantic | Django 框架 |
| **在 Flask 中使用** | ✅ 可以 | ❌ 不行（需要 Django） |
| **在 FastAPI 中使用** | ✅ 可以 | ❌ 不行（需要 Django） |
| **在脚本中使用** | ✅ 可以 | ❌ 不行（需要 Django） |
| **在 Jupyter 中使用** | ✅ 可以 | ⚠️ 困难（需要配置 settings） |

我们的目标是为所有 Python 应用提供一个**通用的 ActiveRecord 解决方案**——Web 框架、CLI 工具、数据管道、Jupyter 笔记本等。

### 5. 完整的 ActiveRecord 生态系统

我们不仅在构建一个 ORM，更是在构建一个**完整的 ActiveRecord 生态系统**：

- ✅ **查询构建器** —— ActiveQuery、CTEQuery、SetOperationQuery
- ✅ **关系** —— BelongsTo、HasOne、HasMany，支持预加载
- ✅ **企业级功能** —— 乐观锁、软删除、时间戳、UUID
- ✅ **异步支持** —— 真正的同步异步对等，不是包装器
- ✅ **多后端** —— SQLite（内置）、MySQL、PostgreSQL（计划中）
- ✅ **AI 原生设计** —— 内置对 AI 代码智能体的支持

**我们的使命：** 让 ActiveRecord 成为 Python 数据持久化的首选模式，无论用户选择什么框架都能使用。

---

我们的核心设计哲学主要体现在以下六个方面：

## 1. 显式控制优于隐式魔法

我们的框架强调显式控制而非隐式行为。所有数据库操作对用户来说都是清晰可见和可控的：
- 没有自动刷新或隐藏的数据库操作
- 没有复杂的对象状态管理及多种转换
- 没有用户无法控制的隐藏缓存机制
- 与具有自动会话管理的系统不同，我们的方法让用户完全了解数据库操作何时发生

## 2. 分层架构：Backend 与 ActiveRecord

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

> **注意**: 不同的数据库后端对功能的支持程度可能不同（例如，MySQL 从 8.0 版本开始才支持窗口函数）。请以具体后端的发行注记和文档为准。

## 3. 同步异步对等：跨范式功能等价性

`rhosocial-activerecord` 的一个基本设计原则是**同步异步对等**，这意味着同步和异步实现提供等效的功能和一致的 API。

*   **方法签名一致性**: 同步方法如 `save()`、`delete()`、`all()`、`one()` 有直接的异步对应方法，如 `async def save()`、`async def delete()`、`async def all()`、`async def one()`。
*   **接口等价性**: `ActiveRecord` 和 `AsyncActiveRecord` 都实现了等价的接口（分别是 `IActiveRecord` 和 `IAsyncActiveRecord`），确保两种范式下可用相同的操作。
*   **查询构建器对等**: `ActiveQuery` 和 `AsyncActiveQuery` 提供相同的查询构建功能，具有相同的方法链和选项，仅在执行方式上有所不同（同步 vs 异步）。
*   **功能完整性**: 同步版本中可用的每个功能在异步版本中也可用，包括关系、验证、事件和复杂查询。

这种对等性使开发人员能够在同步和异步上下文之间无缝过渡，而无需学习不同的 API 或牺牲功能。

## 4. 严格的模型-后端对应关系与同步/异步隔离

我们坚持 **"One Model - One Backend - One Table"** 的设计原则：

*   **严格一一对应**: 一个模型类对应一个特定的后端实例，进而对应数据库中的一张表（或视图）。
*   **同步与异步的严格隔离**:
    *   **不同模型**: 同步模型（继承自 `ActiveRecord`）和异步模型（继承自 `AsyncActiveRecord`）被视为完全不同的模型实体。
    *   **不可混用**: 你不能在同步模型中定义指向异步模型的关联关系，反之亦然。同步的 `ActiveQuery`、`CTEQuery` 只能用于同步模型；异步查询构建器只能用于异步模型。这种隔离确保了运行时行为的可预测性，避免了 async/await 上下文切换带来的复杂性和潜在死锁风险。

## 5. 类型安全与数据校验

我们深知良好范式对于系统稳定性和开发效率的关键性影响。因此，在数据模型层的设计上，我们做出了一个关键决定：

**让 ActiveRecord 直接继承自 `pydantic.BaseModel` (Pydantic V2)。**

我们没有选择自己实现一套验证系统，原因很简单：
*   **成熟度**: Pydantic 已经是 Python 生态中事实上的数据验证标准，极其成熟且功能强大。
*   **成本**: 自己从头实现一套达到同等水平的验证系统成本极高且容易引入 Bug。
*   **生态**: 能够直接享受 Pydantic 庞大的生态系统（如 FastAPI 集成、IDE 智能提示等）。

通过这一继承关系，每一个 ActiveRecord 模型本质上都是一个 Pydantic 模型，拥有强大的运行时类型检查和数据校验能力，确保入库数据的绝对纯净。

## 6. 强大的查询系统

ActiveRecord 不仅仅是数据模型，它还搭配了一套强大的查询体系，主要包括：

*   **ActiveQuery**: 标准的查询构建器。
*   **CTEQuery**: 通用表表达式（Common Table Expressions）查询。
*   **SetOperationQuery**: 集合操作查询（如 Union, Intersect）。

**ActiveQuery 的核心使命是实例化 ActiveRecord 实例（列表）**。当你执行 `User.query().where(...)` 时，默认返回的是经过完整校验的 `User` 对象列表。

同时，为了满足性能敏感场景的需求，`ActiveQuery` 与 `CTEQuery`、`SetOperationQuery` 一致，都提供了 **`aggregate()`** 功能。这允许你在需要时跳过模型实例化，直接获取聚合数据或原始字典结果，从而在灵活性和性能之间取得完美平衡。
