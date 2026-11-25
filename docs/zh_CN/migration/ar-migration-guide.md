# ActiveRecord 层迁移指南

> 本章节描述 ActiveRecord **自己的**迁移能力：用户编写 `up(ctx)` / `down(ctx)` 逻辑，
> 框架负责顺序、执行、dry-run 与版本记录。它区别于后端 `migrate` 命令（见
> [迁移系统](README.md)），后者属于后端运行时。

## 1. 心智模型

一个迁移由两部分组成：

```python
from rhosocial.activerecord.migration import Migration

def up(ctx):     # 应用变更
    ...

def down(ctx):   # 回滚变更
    ...

m = Migration("v001_add_users", up, down, dependencies=(), description="...")
```

**用户拥有** up/down 逻辑；**框架拥有**围绕它的一切：

| 关注点 | 归属 |
|---|---|
| 顺序（UP 按给定顺序、DOWN 逆序）、依赖检查、重复/守卫检查 | `MigrationRunner` |
| 执行 vs dry-run 渲染 | `ctx.apply()` |
| 版本记录（已应用/已回滚）| 可插拔的 `MigrationRecordStore` |
| "本数据库该怎么做这个操作？" | 后端**建议**（可选）|

## 2. 上下文 `ctx`

`ctx` 是你与数据库的桥梁：

- `ctx.apply(*expressions)` —— 执行 DDL/DML 表达式；dry-run 下只渲染到 `ctx.dry_run_sql`。
  接受单个列表/元组，因此建议的结果可直接传入。
- `ctx.backend`、`ctx.direction`、`ctx.version`、`ctx.is_up`、`ctx.is_down`。
- `ctx.suggest_partition_<x>(strategy, plan)` —— 八个"怎么做"访问器：
  `build`、`table_drop`、`table_alter`、`add`、`drop`、`split`、`merge`、`retention`。
  每个返回有序表达式链、`None`（无需动作）或 `None`（不支持——helper 把两者都折叠为
  `None`；如需区分请直接读原始建议）。

## 3. 何时使用建议

当一个操作是**单一标准动作**、跨数据库只有拼写差异时（加列/删列、重命名等），
直接用表达式-方言系统——方言会为各后端渲染正确 SQL。

当同一意图在不同数据库需要**不同的多步动作链**时才取建议——典型如分区生命周期：

- "加分区" → `ADD PARTITION`（MySQL）/ `CREATE TABLE ... PARTITION OF`（PostgreSQL）/
  `SPLIT RANGE`（SQL Server，有数据影响）/ 无操作（ClickHouse）。
- "淘汰旧分区" → DROP（MySQL/Oracle）/ DETACH→DROP（PostgreSQL）/
  MERGE RANGE（SQL Server）/ DROP PARTITION ID（ClickHouse）。

建议是**可选的**：若明确锁定某后端，直接在 `up`/`down` 里写该后端的表达式即可。

## 4. Dry-run

```python
preview = runner.run([migration], store=store, dry_run=True)
for sql, params in preview.results[0].dry_run_sql:
    print(sql)          # 已渲染，从不执行
assert preview.applied == []   # 不写任何记录
```

## 5. up / down 与版本记录

```python
runner.run([m], store=store)                       # UP，记录版本
runner.run([m], direction="down", store=store)     # DOWN，逆序 + 清除
store.get_applied()                                 # 当前已应用版本
```

DOWN 逆序执行。依赖必须出现在组内更早位置或已应用；重复应用已应用版本、回滚未应用版本都会抛出类型化错误。

## 6. 异步

`AsyncMigration` / `AsyncMigrationRunner` / `AsyncMigrationContext` 与同步 API 一一对应
（`await ctx.apply(...)`、`await runner.run(...)`），方法名相同。

## 7. 后端差异

分区在各数据库差异极大。可运行示例见 `docs/examples/ar-migration/`（每后端一个目录）
及各目录 README。概要：

| 后端 | 分区模型 |
|---|---|
| SQLite / Firebird | 无表分区——建议返回"不支持" |
| MySQL / MariaDB | 内联 `PARTITION BY`，ADD/DROP/REORGANIZE |
| PostgreSQL | 独立子表（`PARTITION OF`），DETACH→DROP，无 split/merge |
| Oracle | 内联 + INTERVAL/REFERENCE，按名 DROP，SPLIT/MERGE |
| SQL Server | 仅 RANGE；SPLIT/MERGE RANGE（有数据影响）|
| ClickHouse | `PARTITION BY <expr>` 存储子句，无 ADD，DROP PARTITION ID |

> 读取实时分区状态（`introspect partitions`）与能力探测属于**后端 CLI** 职责，不在本 API 内。

## 8. 面向用户的变更规划 API

不必自行拼装 `plan_changes` / `resolve_suggestions` / `suggest_partition_*_raw`，
上下文提供两个返回**冻结、与方言无关结果**的入口：

- `ctx.plan_schema_change(old_model, new_model) -> SchemaChangeOutcome`
  组合模型声明 diff 与建议解析。`statements` 是可执行表达式链（每条语句一个动作）；
  `supported` / `unsupported` / `no_answer` / `missing` 按状态分组保存**每一个**决策点，
  `False`（明确不支持）、`None`（无应答）与缺少协议都不会被悄悄丢弃。
- `ctx.plan_partition_change(intent, strategy, plan) -> PartitionChangeOutcome`
  先读取 `dialect.partition_capability()`，再决定是否询问后端。`capability` 为
  `NATIVE` / `AUTOMATIC` / `UNSUPPORTED` 三者之一：

  | 能力 | `state` | `operations` | 含义 |
  |---|---|---|---|
  | `NATIVE` | `actions` / `no-action` / `unsupported` / `no-protocol` | 表达式元组或 `False` | 只有此状态才调用 `suggest_partition_*_raw` |
  | `AUTOMATIC` | `engine-managed` | `False` | 引擎自行分区与管理存储，**没有可定位的分区 DDL，绝不伪造 DDL**，也不调用任何分区建议 |
  | `UNSUPPORTED` | `not-supported` | `False` | 后端完全没有分区，同样不调用任何分区建议 |

两者的 `report()` 只返回**文字描述**（说明哪些可以应用、其余各点为何不能），不含 SQL 字符串。

`ctx.apply_change(outcome, *, allow_incomplete=False, authorized_destructive=False)` 只执行
`outcome` 自带的表达式链：

- 只要还有 `unsupported` / `no_answer` / `missing` 点（分区结果 `operations is False`），
  默认拒绝执行；确认只应用已解析部分时传 `allow_incomplete=True`。
- 最后一道通用防线会拒绝破坏性 DDL（`DropTableStatement`、`DropSchemaStatement`、
  `TruncateStatement`、`DeleteStatement`，以及按渲染 SQL 识别的 `DROP TABLE` /
  `DELETE FROM` 等）和没有配对的 `SWITCH ... TO` 数据搬移；确有授权时传
  `authorized_destructive=True`。**一条语句只能承载一个动作**，多动作语句始终被拒绝。
  这只是通用兜底，不替代后端自身的安全检查。

```python
def up(ctx):
    outcome = ctx.plan_schema_change(User20261124, User)
    print(outcome.report())            # 纯文字，无 SQL
    ctx.apply_change(outcome)          # 不完整时抛错

    # 明确知道要跳过未解决点时：
    ctx.apply_change(outcome, allow_incomplete=True)

    part = ctx.plan_partition_change("add", strategy, plan)
    print(part.report())
    if part.capability.name == "NATIVE":
        ctx.apply_change(part)         # AUTOMATIC / UNSUPPORTED 时 operations is False
```

`AsyncMigrationContext` 的同名方法一一对应，应用时写 `await ctx.apply_change(outcome)`。
