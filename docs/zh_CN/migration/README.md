# 迁移 —— 后端运行时系统

> 本章介绍 ActiveRecord 的**原生迁移系统** —— 即负责随时间推移对模式变更进行排序、执行、记录与回滚的后端/运行时层。它不同于 [DDL](../modeling/ddl.md) 中描述的模型级 DDL 推导：那一层将模型当前的声明转换为语句；而这一层则将此类语句的*序列*作为带版本、可逆的迁移来管理。
>
> 范围说明：所有示例均使用内置的 SQLite 后端。其他后端在其各自的仓库中单独说明。

## 1. 两套 API，两个入口

迁移系统提供了**两套刻意相互独立的编写 API**（见 `backend/migration/functions.py:14-16`）。二者不可互换：

| | 函数式迁移（主要） | 类式迁移（兼容旧版） |
|---|---|---|
| 编写单元 | 一个由 `@migration` 装饰的函数 | 一个带有 `up()`/`down()` 的 `NamedMigration` / `AsyncNamedMigration` 子类 |
| 编排器 | `run_migration_group()` / `run_migration_group_async()` | `MigrationRunner` / `AsyncMigrationRunner` / `BatchMigrationRunner` |
| CLI | 模型 CLI 的 `migrate` 命令 | 各后端 CLI 的 `named-migration` 命令 |
| 状态 | 持续开发中，推荐使用 | 完全支持，为兼容而保留 |

两条路径共享相同的基础设施：`MigrationContext`、`MigrationDirection`、版本记录模型、类型化异常层级以及 `Procedure` 执行引擎。新工作请使用**函数式迁移**；仅在维护既有迁移类时使用类式迁移。

> 💡 **AI 提示词：** "我有一个模型，其中包含一个由 `@migration` 装饰的类方法。请演示如何使用 SQLite，先以试运行（dry run）方式执行它，再通过 JSON 版本记录真正执行它。"

## 2. 术语

- **版本（version）** —— 迁移的字符串标识符（`@migration("v001_create_users")`）。运行时会强制保证其唯一性；不带版本号的装饰器回退为函数名。
- **方向（direction）** —— 来自 `MigrationDirection` 的 `UP`（应用）或 `DOWN`（回滚）。
- **依赖（dependency）** —— 另一个必须已经应用（或在组中排在前面）的版本。依赖是**被校验的，而非自动解析的** —— 见 §4。
- **记录存储（record store）** —— 一种 `MigrationRecordStore` 策略，用于持久化哪些版本已被应用。唯一的内置实现是 `JSONFileMigrationRecordStore`；**没有内置的数据库表存储** —— 若希望将记录保存在数据库中，需自行提供。
- **试运行（dry run）** —— 渲染并收集所有语句，但不触碰数据库，也不写入记录。

## 3. 函数式迁移（主要 API）

### 3.1 编写迁移函数

```python
from typing import Annotated, Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.migration import migration, MigrationDirection


# ActiveRecord already mixes in MigrationMixin, so the statement getters
# (create_table_statement / drop_table_statement) are available on every model.
class User(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return "users"

    id: Annotated[Optional[int], UseSqlType(IntegerType())] = None
    name: Annotated[str, UseSqlType(VarCharType(length=64))]


@migration("v001_create_users", description="initial users table")
def create_users(ctx):
    if ctx.direction == MigrationDirection.UP:
        ctx.apply(User.create_table_statement(backend=ctx.backend))
    else:
        ctx.apply(User.drop_table_statement(if_exists=True, backend=ctx.backend))
```

关键规则：

- 装饰器签名为 `migration(version="", *, dependencies=(), description="", async_variant="")`。`dependencies` 必须是非空字符串组成的序列（单独传入一个字符串会被拒绝）；`async_variant` 必须为非空的 FQN。
- 迁移函数必须接收**且仅接收一个位置参数 `ctx`** —— 不得有必填的仅关键字参数，也不得有 `*args`/`**kwargs`。签名检查发生在函数引用被解析时，而非装饰时。
- 函数可以是**模块级函数**，也可以是模型的 `@classmethod`/`@staticmethod`。普通实例方法会被拒绝。拥有该类方法的模型会被记录为该函数的 `owner`。
- `ctx.apply(*expressions)` 接受语句对象（任何具有 `.to_sql() -> (sql, params)` 的对象）或由它们组成的单个 list/tuple。这是 DDL 路径。命名表达式路径为 `ctx.execute(FQN, ...)` —— 详见 [命名表达式（Named Expressions）](../backend/named_expression.md) 一章。

### 3.2 引用函数（FQN）

函数通过**完全限定名（fully qualified name）**来引用，形式为 `module:function`（首选）或 `module.Class.method`。`resolve_migration_function()` 会校验该引用、`@migration` 元数据、签名以及所有者类型，返回一个 `MigrationFunctionRef`（`fqn`、`function`、`info`、`owner`、`is_async`）。传入类的 FQN（包括 `NamedMigration` 子类）会报错，并提示改用后端的 `named-migration` 命令。

### 3.3 运行迁移组

```python
from rhosocial.activerecord.backend.migration import run_migration_group
from rhosocial.activerecord.backend.migration.record import JSONFileMigrationRecordStore

store = JSONFileMigrationRecordStore("migration_records.json")

# dry run — nothing is written
preview = run_migration_group(backend, ["app.migrations:create_users"], dry_run=True)
print(preview.dry_run_sql)        # [(label, sql, params), ...]
print(preview.dry_run_total)      # statement count

# real run
result = run_migration_group(backend, ["app.migrations:create_users"], record_store=store)
print(result.applied, result.versions, result.records_written)

# roll back
run_migration_group(backend, ["app.migrations:create_users"],
                    direction=MigrationDirection.DOWN, record_store=store)
```

`run_migration_group(backend, functions, *, direction=UP, record_store=None, dry_run=False, transaction_mode=TransactionMode.AUTO)` 接受 `MigrationFunctionRef`、FQN 字符串或已装饰的可调用对象。它返回一个 `MigrationGroupResult`（`direction`、`dry_run`、`versions`、`applied`、`rolled_back`、`dry_run_sql`、`dry_run_total`、`records_written`）。

它保证：

- **顺序由调用方决定**：UP 按给定顺序执行函数；DOWN 按相反顺序执行。迁移组**不会**进行拓扑排序 —— 依赖只做检查，不做解析（见 §4）。
- 迁移组在内部构建一个 `Procedure` 子类并通过 `ProcedureRunner` 运行它，因此每个函数看到的 `MigrationContext` 都已设置好 `ctx.version` 并应用了 `transaction_mode`。
- 运行完成后，它会调用 `backend.introspector.clear_cache()`，使后续的内省操作能看到新的模式。
- 成功时（且仅在非试运行时）为每个函数写入一条 `MigrationRecord`。失败时不写入任何记录，并抛出携带 `version`、`fqn`、`cause`、`executed` 和 `transactional_ddl` 的 `MigrationFunctionExecutionError`。

### 3.4 异步变体

`run_migration_group_async()` 与同步 API 一一对应。异步运行使用 `select_async_functions()` 将每个函数替换为其 `@migration(async_variant="...")` 指定的伙伴函数：异步函数必须声明**相同的版本**，并且版本记录以**同步 FQN** 作为规范键，因此以同步方式应用的版本与以异步方式应用的版本绝不会冲突。未声明 `async_variant` 的同步函数不能用于异步运行。

## 4. 顺序、依赖与校验

这是函数式 API 中最容易被误解的部分：

- **不自动排序。** 与旧版 `BatchMigrationRunner`（会执行真正的拓扑排序）不同，`run_migration_group` 对 UP 原样使用你提供的列表顺序，对 DOWN 使用其逆序。
- **依赖会被校验**：对于 UP，依赖必须要么在组中排在更前面，要么已经在记录存储中记为已应用；否则抛出 `MigrationDependencyError`。同一组中出现重复版本会抛出 `MigrationError`；某个版本以不同的 FQN 被记录会抛出 `MigrationVersionConflictError`；重复应用已应用的版本（UP）或回滚未应用的版本（DOWN）会分别抛出 `MigrationAlreadyAppliedError` / `MigrationNotAppliedError`。
- 因此，**提供正确的执行顺序是你的责任**；依赖只是一种安全校验，而非调度器。

## 5. 版本记录

`MigrationRecord`（`backend/migration/record.py`）包含 `version`、`migration_fqn`、`direction`、`applied_at`（带时区信息的 UTC 时间）、`success` 以及可选的 `error_message`。

`MigrationRecordStore` 是一个抽象策略，提供 `get_applied()`、`record()` 和 `is_applied()`。没有内置的数据库存储；`JSONFileMigrationRecordStore(path)` 是唯一的具体实现。它的 `get_applied()` 计算方式为**成功应用的 UP 版本减去成功回滚的 DOWN 版本**，因此在一次干净的回滚之后，某个版本会从"已应用"中消失。

## 6. 试运行 —— 两条捕获路径

试运行会渲染所有语句，但绝不触碰数据库或记录。迁移产生语句的方式有两种，两者都会被捕获：

1. **`ctx.apply(...)`** —— 语句由上下文记录，并带有标签 `"<version> <ExpressionClass>"`，最终进入 `ctx.dry_run_sql`。
2. **直接写入模型**，例如 `User.create_table(backend=ctx.backend)` —— 这些调用会直接访问后端。迁移组会将后端包装在一个 `DryRunBackend` 中，并临时把每个所有者模型的 `__backend__` 指向该代理，因此即使是直接写入也会被记录（记为 `backend.execute`），且不会执行任何真实 SQL。所有状态都会在 `finally` 块中恢复。

CLI 将试运行显示上限设为 100 条语句（`--dry-run` 会打印渲染后的 SQL，并附上 "N statement(s) rendered; no changes written" 的汇总信息）。

> ⚠️ **旧版运行器注意事项（仅限类式 API）**：在 `MigrationRunner` 路径中，`ctx.apply()` 生成的 SQL 会进入 `ctx.dry_run_sql`，但 `MigrationRunner.run()` 构造其返回的 `dry_run_sql` 时仅使用命名表达式回调。函数式的 `run_migration_group` 路径则能正确捕获两者。

## 7. `migrate` CLI（函数式 API）

模型 CLI 提供顶层 `migrate` 命令：

```bash
python -m rhosocial.activerecord.cli migrate app.migrations:create_users \
    --model app.models:User --record-store records.json --dry-run
python -m rhosocial.activerecord.cli migrate --list --model app.models:User
python -m rhosocial.activerecord.cli migrate --plan --model app.models:User
python -m rhosocial.activerecord.cli migrate app.migrations:create_users \
    --model app.models:User --record-store records.json --direction down -o json
```

参数：一个或多个函数 FQN；`--direction up|down`；`--record-store PATH|module:Class`；`--dry-run`；`--list`；`--plan`；`--async`；`-o text|json`；`--model MODULE:CLASS`；以及通用的连接选项。`--list`/`--plan` 会在**建立连接之前**打印并退出。连接来源要么由 `--model`（模型配置的后端）提供，要么由显式的 `--backend-class`/`--config-class` 提供。

JSON 模式会输出一个 `{"command": "migrate", ...}` 载荷；失败信息包含 `migration_version`、`migration_fqn`、`executed`、`transactional_ddl` 和 `rolled_back`。

## 8. 类式迁移（兼容旧版）

编写一个带有 `up(ctx)`/`down(ctx)` 的 `NamedMigration` 子类（或使用带异步方法的 `AsyncNamedMigration`）。`MigrationRunner(migration_fqn).run(backend, direction, ...)` 执行单个迁移，并执行依赖检查、重复保护、版本记录写入，并返回一个 `MigrationResult`。`BatchMigrationRunner(module_name)` 会发现某个模块中所有 `NamedMigration` 子类，并按**依赖的拓扑顺序**运行它们（这是唯一会自动排序的组件），提供 `migrate_up()`/`migrate_down()`、`status()` 和 `pending_versions()`。DOWN 会反转拓扑顺序；`single_transaction=True` 会将整批操作包在一个事务中，并仅在最终提交后写入记录。

每个后端 CLI 还提供一个 `named-migration` 命令，委托给这些辅助类。其解析器接受一个**限定名（qualified name）**，以及 `--direction up|down`、`--record-store`、`--dry-run`、`--describe`、`--list`、`--param KEY=VALUE`、`--all` 和 `--single-transaction`。

> 旧版类式系统仍完全受支持，但不是新工作的推荐路径。现有的可运行示例位于 `src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/`。

## 9. 异常层级

全部位于 `MigrationError`（继承自 `ProcedureError`）之下：`MigrationDependencyError`、`MigrationAlreadyAppliedError`、`MigrationNotAppliedError`、`MigrationVersionConflictError`、`MigrationDialectError`（当某方言在 DDL 期间抛出了 `ProtocolNotImplementedError`/`UnsupportedFeatureError`）以及 `MigrationFunctionExecutionError`（封装一个执行失败的函数及其上下文）。`MigrationFunctionError` 则是独立的 —— 它在解析阶段表示 FQN、签名或所有权有误。

## 10. API 快速参考

| 关注点 | API | 模块 |
|---|---|---|
| 装饰器 / 解析器 | `migration`, `resolve_migration_function`, `MigrationInfo`, `MigrationFunctionRef` | `backend.migration.functions` |
| 执行上下文 | `MigrationContext.apply`, `AsyncMigrationContext.apply` | `backend.migration.context` |
| 函数组 | `run_migration_group`, `run_migration_group_async`, `select_async_functions` | `backend.migration.group` |
| 类式运行器 | `MigrationRunner`, `AsyncMigrationRunner`, `BatchMigrationRunner` | `backend.migration.{runner,async_runner,batch_runner}` |
| 类式基类 | `NamedMigration`, `AsyncNamedMigration`, `MigrationDirection` | `backend.migration.core` |
| 记录 | `MigrationRecord`, `MigrationRecordStore`, `JSONFileMigrationRecordStore` | `backend.migration.record` |
| 异常 | `MigrationError` 及其子类, `MigrationFunctionError` | `backend.migration.exceptions`, `functions` |
| 模型 DDL | `MigrationMixin`, `AsyncMigrationMixin` | `base.migration_mixin` |
| CLI | `migrate`（模型 CLI）, `named-migration`（后端 CLI） | `cli`, `backend.migration.cli` |
