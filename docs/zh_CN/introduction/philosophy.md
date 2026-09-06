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

backend = SQLiteBackend(database=":memory:")
dialect = backend.dialect

# 直接创建表达式（方言在构造时绑定为第一个参数）
col = Column(dialect, "age", table="users")
expr = col > Literal(dialect, 18)

# 通过方言生成 SQL（to_sql() 无参数，方言在构造时已绑定）
sql, params = expr.to_sql()
# SQL: "users"."age" > ?
# params: (18,)

# 直接通过后端执行（不需要 ActiveRecord）
backend.execute(sql, params)
```

> **注意**：表达式对象在**构造时**绑定方言（`Column(dialect, ...)` 的第一个参数），`to_sql()` 本身不接受任何参数——方言已作为表达式构造的一部分被存储。这与查询时动态注入方言的 `DataType`（见[数据类型](../backend/expression/types.md)）形成对比：后者允许延后绑定，前者始终携带方言。

**d) 框架灵活性——构建你自己的 ORM**
表达式-方言-后端堆栈是完全独立的。你可以：
- 使用它来构建**Data Mapper**模式 ORM 而不是 ActiveRecord
- 创建带有自定义查询构建器的**Repository**模式
- 实现**CQRS**（命令查询职责分离），使用不同的读/写模型
- 构建将查询转换为优化 SQL 表达式的 **GraphQL 解析器**

```python
# 示例：构建自定义 Repository 模式
from rhosocial.activerecord.backend.expression import Column, Literal

class UserRepository:
    def __init__(self, backend):
        self.backend = backend
        self.dialect = backend.dialect
    
    def find_active(self, min_age: int):
        # 直接使用表达式系统（方言在构造时绑定）
        expr = (Column(self.dialect, "is_active") == Literal(self.dialect, True)) & \
               (Column(self.dialect, "age") >= Literal(self.dialect, min_age))
        sql, params = expr.to_sql()
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

### 6. Python 版本支持策略

我们对 Python 3 的支持**从 3.8 开始**。尽管 3.8~3.10 已陆续退出官方支持周期（EOL），但考虑到其在生产环境中的**广泛占有量**，我们仍然尽力支持这些版本，让存量项目无需强制升级即可使用本框架。

- **核心库**（`python-activerecord`）：支持 `>=3.8`
- **后端包**：具体支持范围**以各后端为准**，可能因驱动依赖而不同。例如 SQL Server 后端要求 `>=3.9`，ClickHouse 后端要求 `>=3.10`——请以所用后端包的 `pyproject.toml` 声明为准。

> **说明**：核心库尽力维护 3.8 兼容性，但各后端对 Python 版本的支持取决于其数据库驱动自身的支持范围，可能存在差异。部署前请确认所用后端包的实际版本要求。

---

我们的核心设计哲学主要体现在以下七个方面：

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

**后端以完整 SQL 语义覆盖为目标，而非仅满足 ActiveRecord 的使用需求。** Backend 层的职责是尽可能完整、忠实地表达目标数据库的 SQL 语义——包括 ActiveRecord 层可能永远不会用到的能力。ActiveRecord 只是 Backend 众多使用方式中的一种，它用不到某些能力，绝不意味着 Backend 可以省略这些能力。后端实现不会因为"当前没有用户用到"而偷懒简化；完整、忠实的 SQL 语义覆盖是后端实现的基本契约，也是所有后端保持一致开发体验的前提。

在"表达式-方言"系统中有一条金科玉律：**表达式绝不自行拼接 SQL 字符串**。表达式只负责描述结构与收集参数，所有 SQL 生成一律委托给方言的 `format_*` 方法，所有值一律通过参数占位符（`?`）绑定。这既是**安全由构造保证**的体现——遵循 DB-API 2.0（PEP 249）"SQL 与参数分离"的要求，从构造上杜绝 SQL 注入；也是**SQL 透明性**的保障——SQL 只有一个生成出口，任何查询都可以随时调用 `.to_sql()` 检视结果。对违反这一约定的输入（如无占位符的字符串条件），框架会显式警告（`UserWarning`）而非静默放行。

此外，表达式是**无状态且纯**的：它们只描述"你想要什么"，没有隐藏行为或自动操作；从表达式到 SQL 仅两步（构造 → `.to_sql()`），没有多层编译，也没有隐藏缓存。这种**以简单换取性能**的设计让执行行为与性能开销变得可预测。

## 3. 后端即插即用：平等、可扩展的后端生态

核心库为后端提供了完整的契约框架：**基类**（如 `StorageBackendBase`、`StorageBackend`）、**协议族**（`backend/protocols.py`、`dialect/protocols.py` 中的能力检测协议）以及**一定程度的实现**（Mixin 组合、类型适配器、事务管理等）。任何数据库后端——包括我们内置的 SQLite——都只是这套契约的一个具体实现。

*   **SQLite 是范例，而非特权**。SQLite 是随核心库内置的唯一后端，但它在架构上与其他后端完全平级，仅作为其他后端的**参照实现**。`backend/impl/README.md` 明确指出：创建自定义后端时，应以 `sqlite` 的实现为参考。
*   **无短名特权，一律使用完全限定名**。在框架代码、文档和示例中，无论内置的 SQLite 还是独立的 MySQL、PostgreSQL 后端，都通过完全限定路径引用（`rhosocial.activerecord.backend.impl.sqlite.SQLiteBackend`、`rhosocial.activerecord.backend.impl.mysql.MySQLBackend` 等）。框架不提供"短名 → 后端类"的映射注册表，也不为自家后端准备魔法字符串别名。
*   **自研与第三方完全平等**。我们自研的 MySQL、PostgreSQL 后端以独立包形式分发（`python-activerecord-mysql`、`python-activerecord-postgres`），安装后同样挂载在 `rhosocial.activerecord.backend.impl` 命名空间下。第三方开发者可以遵循相同的约定，以相同的完全限定路径接入自己的后端，与官方后端享受完全相同的待遇——没有隐藏的优先级、默认值或特殊处理。
*   **可随时扩充**。添加新后端仅需：实现 `Dialect` 与 `Backend` 子类（可复用协议族与 Mixin），放置到 `backend/impl/<name>/` 目录，无需改动核心库的任何代码。
*   **协议驱动与能力协商**。能力通过 `Protocol` 声明而非继承层次强制——`backend/protocols.py`、`dialect/protocols.py` 定义了细粒度的能力协议（如 `WindowFunctionSupport`、`JSONSupport`），`supports_*` 方法按服务器真实版本门控；后端在连接真实服务器后还会通过 `introspect_and_adapt()` 重建方言与类型适配器。后端能力因此是"与服务器版本协商的契约"，而非静态声明，用户可以在运行期检测能力并优雅降级。
*   **组合优于继承**。无论是模型还是后端，功能都以可插拔的 Mixin 组合而成——`StorageBackend` 由十余个 Mixin 组装，`ActiveRecord`/`AsyncActiveRecord` 由同一组 Mixin 平行组合。Mixin 组合避免了深继承层次的脆弱性，也让自定义后端只需按需挑选、覆写所需能力。
*   **生态级动态发现与解耦**。这一平等原则同样延伸到测试与工具链：标准化测试套件通过 `ProviderRegistry`（经环境变量动态加载）发现后端 provider，测试代码不假设任何具体后端，能力不满足的测试被**跳过而非失败**；devtools 的 inspect 与 MCP Server 则通过扫描 `rhosocial.activerecord.backend.impl` 命名空间自动发现已安装的后端。没有任何地方硬编码"哪些后端存在"。

## 4. 同步异步对等：跨范式功能等价性

`rhosocial-activerecord` 的一个基本设计原则是**同步异步对等**，这意味着同步和异步实现提供等效的功能和一致的 API。

*   **方法签名一致性**: 同步方法如 `save()`、`delete()`、`all()`、`one()` 有直接的异步对应方法，如 `async def save()`、`async def delete()`、`async def all()`、`async def one()`。
*   **接口等价性**: `ActiveRecord` 和 `AsyncActiveRecord` 都实现了等价的接口（分别是 `IActiveRecord` 和 `IAsyncActiveRecord`），确保两种范式下可用相同的操作。
*   **查询构建器对等**: `ActiveQuery` 和 `AsyncActiveQuery` 提供相同的查询构建功能，具有相同的方法链和选项，仅在执行方式上有所不同（同步 vs 异步）。
*   **功能完整性**: 同步版本中可用的每个功能在异步版本中也可用，包括关系、验证、事件和复杂查询。

这种对等性使开发人员能够在同步和异步上下文之间无缝过渡，而无需学习不同的 API 或牺牲功能。

## 5. 严格的模型-后端对应关系与同步/异步隔离

我们坚持 **"One Model - One Backend - One Table"** 的设计原则：

*   **严格一一对应**: 一个模型类对应一个特定的后端实例，进而对应数据库中的一张表（或视图）。
*   **同步与异步的严格隔离**:
    *   **不同模型**: 同步模型（继承自 `ActiveRecord`）和异步模型（继承自 `AsyncActiveRecord`）被视为完全不同的模型实体。
    *   **不可混用**: 你不能在同步模型中定义指向异步模型的关联关系，反之亦然。同步的 `ActiveQuery`、`CTEQuery` 只能用于同步模型；异步查询构建器只能用于异步模型。这种隔离确保了运行时行为的可预测性，避免了 async/await 上下文切换带来的复杂性和潜在死锁风险。

## 6. 类型安全与数据校验

我们深知良好范式对于系统稳定性和开发效率的关键性影响。因此，在数据模型层的设计上，我们做出了一个关键决定：

**让 ActiveRecord 直接继承自 `pydantic.BaseModel` (Pydantic V2)。**

我们没有选择自己实现一套验证系统，原因很简单：
*   **成熟度**: Pydantic 已经是 Python 生态中事实上的数据验证标准，极其成熟且功能强大。
*   **成本**: 自己从头实现一套达到同等水平的验证系统成本极高且容易引入 Bug。
*   **生态**: 能够直接享受 Pydantic 庞大的生态系统（如 FastAPI 集成、IDE 智能提示等）。

通过这一继承关系，每一个 ActiveRecord 模型本质上都是一个 Pydantic 模型，拥有强大的运行时类型检查和数据校验能力，确保入库数据的绝对纯净。

## 7. 强大的查询系统

ActiveRecord 不仅仅是数据模型，它还搭配了一套强大的查询体系，主要包括：

*   **ActiveQuery**: 标准的查询构建器。
*   **CTEQuery**: 通用表表达式（Common Table Expressions）查询。
*   **SetOperationQuery**: 集合操作查询（如 Union, Intersect）。

**ActiveQuery 的核心使命是实例化 ActiveRecord 实例（列表）**。当你执行 `User.query().where(...)` 时，默认返回的是经过完整校验的 `User` 对象列表。

同时，为了满足性能敏感场景的需求，`ActiveQuery` 与 `CTEQuery`、`SetOperationQuery` 一致，都提供了 **`aggregate()`** 功能。这允许你在需要时跳过模型实例化，直接获取聚合数据或原始字典结果，从而在灵活性和性能之间取得完美平衡。

这体现了一种**渐进式披露（Progressive Disclosure）**的设计哲学：默认提供安全、完整、经过校验的模型实例（严格模式），当性能敏感时，用户可以显式选择 `aggregate()` 或原始模式直接获取字典结果，绕过 Pydantic 校验以获得数量级的性能提升。用户无需为了性能放弃 ORM 的安全保障，也无需为默认的严格性付出不必要的开销——选择权始终掌握在用户手中。
