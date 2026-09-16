# 其他 ORM 不具备的独有能力

本文档梳理 **rhosocial-activerecord 独有、且任何其他 Python ORM**（SQLAlchemy、
Django ORM、SQLModel、Peewee、Tortoise ORM、Prisma Client Python 等）**均不具备**
的能力。这些并非「我们做得稍好一点」的特性，而是别处找不到对等实现的架构级能力。

> **说明**：以下能力均已核实主流竞争对手不具备。若某对手在精神上提供了
> *相似* 的东西，此处会明确点出差异，以保证陈述站得住脚。

### 贯穿始终的原则：快速失败

本文档中的每项能力、乃至整个软件，都贯穿着一条设计原则：**快速失败**。当数据库
实际并不提供某个特性，或两个后端在无法无损表达的方面存在差异时，
rhosocial-activerecord 会拒绝继续——它抛出显式错误（`UnsupportedFeatureError`、
`DatabaseError` 等），而不是静默模拟后端并不提供的语义。这种「诚实语义、绝不模拟」
的立场，正是能力声明体系值得信赖的根基，也是后面各项特性共同的设计主干。

---

## 1. 表达式-方言系统：构造学保证

本文其他能力的地基，是 rhosocial-activerecord 构造 SQL 的方式。SQL 被表示为
**表达式对象组成的树**，把树渲染成文本是**一次纯读取**——SQL 字符串由简单拼接
组装而成，**完全没有二次加工**（不对产出的文本做正则匹配/替换，也不靠
`startswith`/`endswith`/`contains` 去判断）。

保证是结构性的，而非流程性的：

```python
# 每个表达式只声明一件事：渲染它的方言方法名。
@property
def format_method(self) -> str:
    return "format_cte_expression"   # 例如 CTEQuery 声明这个
```

`BaseExpression.to_sql()` **只在根部实现一次**，是唯一的渲染入口。具体表达式类
绝不复写它。渲染过程在节点自身绑定的方言上解析声明的 `format_method`，并把**当前
表达式**交给格式化器——没有重新实例化、没有副本；`dialect` setter 只影响被赋值的
节点本身（绑定是逐节点的，在构造时完成，或之后逐个重新绑定）：

```python
SQLQueryAndParams = Tuple[str, tuple]
# (sql_text, parameter_values)   —— 占位符留在文本里，参数值分开传递，
#                                   遵循 DB-API 2.0（PEP 249）的参数风格顺序。
```

这一设计直接带来三条性质：

1. **参数值绝不进入 SQL 文本。** 默认 `inline_literals=False`，字面量渲染成绑定参数
   占位符（`?`，或按方言 `%s`/`$1` 等由 `get_parameter_placeholder()` 决定），参数值
   放在独立的元组里。内联渲染是显式开启的、涉及安全的选择，仅留给完全由开发者声明、
   不暴露给终端用户的内容（例如派生出的 DDL）。
2. **无死角。** 方言要么能渲染某个表达式（提供了所需的 `format_*` 方法），要么不能——
   失败是立即的（`AttributeError` / `UnsupportedFeatureError`），绝不是半截正确字符串。
   配合 `validate()` 与能力协议（§2），每棵可构造的树要么正确渲染，要么拒绝。
3. **通用却诚实。** 同一棵树可在不同关系库*及其不同版本*间渲染，因为渲染委托给方言
   自己的 `format_*` 方法与方言 mixin——每个后端表达的恰是它真正支持的 SQL，而非
   「最小公分母」式的近似。

### 为什么竞争对手都没有

- **SQLAlchemy** 会编译到内部 AST，但它的逃生舱（`text()`、`literal_column()`）与
  广阔方言层都在鼓励基于字符串的 SQL；没有一条由构造保证的、单一结构性的
  「树渲染 + 参数分离」约束。
- **Django / Peewee / Tortoise ORM** 靠逐步拼接字符串来组装 SQL（Peewee 尤其会对
  占位符做后处理），这正是需要「第二遍」字符串加工的那类做法。
- **Prisma** 在封闭的 Rust 引擎里构造查询——安全，但 AST 既无法从 Python 内省也无法
  扩展，「实际产出什么 SQL」对应用而言是不透明的。

简言之，竞争对手最多做到*安全*、*完整*、*可移植*中的一部分；而表达式-方言系统从
一条结构性保证里同时做到了这三点。

---

## 2. 能力声明协议体系

数据库可能（或不可能）支持的每一个 SQL 特性——窗口函数、CTE、触发器、XML、JSON、
GRAPH、MERGE、QUALIFY、时态表、分区、序列、生成列、内省等约 40 项——都在方言上
对应一个专门的 **`Support` 协议**。

```python
from rhosocial.activerecord.backend.dialect.protocols import CTESupport

@runtime_checkable
class CTESupport(Protocol):
    def supports_basic_cte(self) -> bool: ...
    def supports_recursive_cte(self) -> bool: ...
    def supports_materialized_cte(self) -> bool: ...
```

方言*声明*它支持什么，每个特性开关都在运行时通过 `isinstance(dialect,
SomeSupport)` 风格检测来解析。不支持的特性会以显式的
`UnsupportedFeatureError` 快速失败，而不是静默编译出错误的 SQL，或模拟数据库
实际并不提供语义。

### 为什么竞争对手都没有

- **SQLAlchemy** 的方言只做语法翻译，特性可用性是隐式的：某个特性在后端/版本上
  是否可用取决于开发者自己判断，误用往往要等到执行期才暴露。
- **Django ORM / Peewee / Tortoise ORM** 提供的是一张固定特性面；数据库差异要么在
  运行时抛错，要么静默截断，而不是声明成一张能力矩阵。
- **Prisma** 把这一点集中到 Rust 查询引擎里，但声明是封闭的、绑定语言的，而非应用
  可以检视和扩展的协议。

### 这套声明带来的收益

- **细粒度、版本感知的门控** —— 例如 MySQL 窗口函数从 8.0 起才声明，测试与代码随之
  自动适配。
- **优雅的测试跳过** —— 能力感知的测试助手自动跳过不支持的特性，而非失败。
- **诚实的非关系型后端** —— 分析型引擎（ClickHouse、Snowflake、BigQuery）*声明*它们
  **不**提供的关系型保证并快速失败，而不是假装自己是行存 OLTP 引擎。
- **自文档化的方言** —— 能力声明本身就是该后端的特性文档。

---

## 3. 命名资源家族（"Named" 体系）

一套把配置和逻辑转变成**可发现、可引用、可 CLI 调用的命名资源**的成体系设计。
三大支柱，都使用全限定名并共享同一套解析模型：

### 3.1 命名连接（`NamedConnectionResolver`）

数据库连接以普通 Python callable 定义，运行时按全限定名解析：

```python
# myapp/connections.py
def production_db(pool_size: int = 10):
    """生产数据库配置。"""
    return MySQLConnectionConfig(host="prod.example.com", pool_size=pool_size)
```

```bash
# 从 CLI 解析并使用，显式参数会覆盖命名值
prog --named-connection myapp.connections.production_db --param pool_size=20
```

### 3.2 命名表达式与查询（`Procedure`、`ProcedureGraph`）

命名查询/表达式可以编排成可执行的过程——既可以用命令式写，也可以声明成 **DAG**：

```python
class MonthlyReportProcedure(Procedure):
    month: str              # 必需参数
    threshold: int = 100    # 可选参数，带默认值

    def run(self, ctx: ProcedureContext) -> None:
        ctx.execute("myapp.queries.orders.monthly_summary",
                    params={"month": self.month}, bind="summary")
        total = ctx.scalar("summary", "total_count")
        if total < self.threshold:
            ctx.log(f"Total {total} below threshold"); return
        for row in ctx.rows("summary"):
            ctx.execute("myapp.queries.archive.insert_record",
                        params={"order_id": row["id"], "month": self.month})
```

**`ProcedureGraph`** 形式把结构（"做什么"）与执行（"怎么做"）分离，并带来独有特性：

- **纯数据 DAG** —— `StepNode` 步骤带显式依赖，图本身不含任何 I/O。
- **单一定义、双重执行** —— 同一张图可通过同步或异步 runner 运行。
- **自动并行** —— runner 识别相互独立的步骤并并发执行。
- **可视化** —— `diagram` 模块渲染图谱。

### 3.3 命名迁移（`NamedMigration`）

迁移以命名、带版本的类实现，具备显式依赖、UP/DOWN 两个方向、dry-run 和方言校验
钩子——与其他命名资源一样通过后端 CLI 暴露。

### 为什么竞争对手都没有

- **SQLAlchemy**（经由 Alembic）有迁移，但没有命名连接或命名查询/过程体系；查询是
  内联代码，而非可发现的命名资源。
- **Django ORM** 在这一层什么都没有命名化；迁移是自动生成的，连接由 settings 驱动，
  没有过程/DAG 编排。
- **SQLModel / Peewee / Tortoise ORM** 三大支柱都不具备。
- **Prisma** 的 schema 是声明式的，但它的「命名」局限于 DSL 内；没有命名连接，也
  没有可执行的过程图。

---

## 4. 常驻 Worker 池 + 可插拔调度

一等公民级别的、基于 spawn 的**常驻进程池**——不是线程池，也不是异步任务 runner——
它在任务之间保持存活，并以三阶段（`DRAINING → STOPPING → KILLING → STOPPED`）完成
优雅停机。

```python
from rhosocial.activerecord.worker import WorkerPool, LeastTasksStrategy

pool = WorkerPool(
    target=my_worker_entry,
    num_workers=4,
    strategy=LeastTasksStrategy(),
)
pool.start()
# 任务经队列派发，调度由所选策略决定
pool.stop()  # 优雅停机：DRAINING → STOPPING → KILLING → STOPPED
```

调度是可插拔的**策略**接口，内置 `LeastTasks`、`RoundRobin`、`Random` 三种策略。

### 为什么竞争对手都没有

- ORM 普遍把 *连接/连接池* 作为自己的并发面（或干脆丢给驱动/应用）。**没有任何一个**
  会在 ORM 自身特性集里内置常驻多进程 Worker 池。
- 这是 rhosocial-activerecord 架构的刻意结果——*进程隔离* 而非连接池来应对并发场景——
  这一模式没有任何其他 Python ORM 作为一等模式采用，更遑论配合可插拔调度与分阶段
  优雅停机。

---

## 5. 内置后端命令行工具

每个后端都自带命令行工具，可通过
`python -m rhosocial.activerecord.backend.impl.<backend>` 调用，子命令高度一致：

| 子命令 | 用途 |
|--------|------|
| `query` | 直接对后端执行 SQL / 查询 |
| `introspect` | 内省 tables、views、columns、indexes、foreign keys、triggers、database |
| `status` | 服务状态概览（config / performance / storage / databases） |
| `info` | 版本与能力信息 |
| `named-connection` / `named-expression` / `named-procedure` / `named-procedure-graph` / `named-migration` | 对命名资源家族的操作 |

共享的 `output` 抽象以 `table` / `json` / `csv` / `tsv` 统一呈现结果（可选 Rich 格式化）。

### 为什么重要

- **运维面就在后端本身** —— 仅靠后端包即可得到数据库运维工具，无需应用层或额外安装
  devtools。
- **与命名资源家族打通** —— connection、expression、procedure、migration 命令正是那些
  可在程序中和 DAG 编排里使用的同名命名资源。
- **跨异构后端统一输出** —— SQLite、MySQL、MariaDB、PostgreSQL、SQL Server、Oracle、
  Firebird、ClickHouse 等都使用相同的输出格式与状态分类。

### 为什么竞争对手都没有

- **SQLAlchemy、Peewee、Tortoise ORM、SQLModel** 没有属于自己的 `__main__` 运维 CLI。
- **Django** 的 `manage.py dbshell` 只是把控制权交给原生客户端，自身不做内省或状态报告。
- **Prisma** 的 CLI 是针对其 DSL 的代码生成/迁移工具，而非与 ORM 命名系统统一的数据库
  运维面。

> 最好将其理解为命名资源家族（§3）与后端独立性（§2）的延伸：CLI 是同一套能力的
> *运维前端*。

---

## 6. 推导 DDL、DDL 锁定与版本对比（roadmap）

该能力组正在开发中，目标是让 rhosocial-activerecord 拥有业界目前三种范式之外的
**第四种迁移范式**。其构件已存在于后端（`schema/`、`expression/statements/ddl_*.py`
以及 `ddl_*` 方言 mixin）。

### 愿景

1. **从 ActiveRecord 类推导 DDL** —— 模型即真相来源，DDL 是按后端渲染的*派生产物*。
2. **跨后端且诚实** —— 推导同时面向多个后端，但通过能力声明体系（§2）尊重各后端的真实
   特性面；当差异无法无损表达时，快速失败而非模拟。
3. **发版前锁定每个版本的 DDL** —— 把 DDL 当作像代码一样的版本化产物来管理。
4. **版本间对比** —— 对比已锁定的 DDL 版本，产出**可执行的表达式实例**（例如
   `ALTER TABLE` 交换/重命名的表达式），而非给人看的文本 diff。

### 为什么这是第四种范式

| 方式 | 代表 | DDL 推导 | 可锁定快照 | diff 产物 |
|------|------|----------|------------|-----------|
| 自动检测 | Django ORM | 强，基于数据库比对 | 无（线性历史） | 可读文本 |
| 手写脚本 | Alembic（SQLAlchemy） | 弱（autogenerate 仅辅助） | 无 | 无 |
| Schema-first DSL | Prisma | 来自 DSL | migration 历史 | 文本 diff（`migrate diff`） |
| **推导 + 锁定 + diff** | **rhosocial-activerecord（规划中）** | **强（Python 类型）** | **是（版本化 DDL）** | **可执行表达式** |

### 为什么竞争对手都没有

- **Django** 能推导 DDL，但把模型当作唯一真相；DDL 是副作用，而非可锁定、可对比、版本化
  的产物。
- **Alembic** 依赖手写修订脚本；`autogenerate` 仅作辅助，没有可供对比的版本化 DDL 快照。
- **Prisma** 的 `migrate diff` 精神上最接近，但它锚定在 DSL 与自家查询引擎上，无法连接
  Python 类型体系，且产物是文本 diff 而非可复用的表达式实例。

### 为什么这些构件相互强化

这不是孤立的功能，它组合了三项 rhosocial-activerecord 已独有的能力：

- **能力声明协议（§2）** 驱动诚实的跨后端 DDL 渲染。
- **表达式-方言系统（§1）** 把 diff 转成可复用、可再序列化的表达式实例，而非死文本。
- **命名资源家族（§3）** 让这些表达式实例可作为命名迁移 / 过程 / DAG 步骤编排。

> **状态**：该组功能**正在开发中**，尚未发布。列在此处是为了让 roadmap 的动机显式化，
> 并扎根于已发布特性一以贯之的「快速失败、绝不模拟」原则。

---

## 总结

| 独有能力 | 其他 ORM 的对等物 |
|----------|-------------------|
| 表达式-方言系统（树渲染 + 参数分离、无二次加工） | ❌ 无——对手要么后处理字符串，要么隐藏 AST |
| 能力声明协议体系（约 40 个 `Support` 协议） | ❌ 无——其他靠隐式方言行为 |
| 命名资源家族（连接 / 表达式 / 迁移） | ❌ 无——没有对等的命名 + DAG 编排 + CLI |
| 常驻 Worker 池 + 可插拔调度 | ❌ 无——没有 ORM 内置进程池作为一等特性 |
| 内置后端命令行工具 | ❌ 无——没有 ORM 提供统一运维 CLI |
| 推导 DDL + DDL 锁定 + 版本对比 | ❌ 无（roadmap）——第四种迁移范式 |