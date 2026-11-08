# 分区维护契约

分区维护由各后端自己实现。PostgreSQL 拥有递归的分区树和异构子分区策略；
Oracle 只有表级统一的子分区策略；SQL Server 是分区函数加分区的方案；
MySQL 和 MariaDB 使用调用方持有的一组扁平定义；ClickHouse 使用服务器分配的
分区 id，且只支持 `DROP` / `DETACH` / `ATTACH`。core 不为任何一家定义计划语法。

core 定义的是**返回结果的形状**，以及调用方可以在执行器上探测的**动词**，
这样调用方不必知道结果来自哪种引擎也能读取报告。

## 值对象

三者都在 `rhosocial.activerecord.backend.partition` 中。

### PartitionInfo

目录报告的一行分区记录。

| 字段 | 含义 |
|---|---|
| `name` | 服务器拼写的分区或子分区名 |
| `parent` | 所属对象；位于目标顶层的行为 `None` |
| `level` | 嵌套深度：`0` 根、`1` 一级分区、`2` 子分区 |
| `method` | 服务器报告的策略词（`RANGE`、`LIST`、`HASH`、`KEY`） |
| `bound` | 原样保留的边界文本，不解析 |
| `schema` | 引擎有 schema 时的所属 schema |
| `row_count` | 目录能提供时的行数 |
| `size_bytes` | 目录能提供时的磁盘占用字节数 |
| `is_partitioned` | 该行自身是否还有子行 |
| `extras` | 只有一种引擎才会有的信息 |

`extras` 刻意使用映射而不是不断加字段：SQL Server 的分区号、Oracle 的子分区
数量、ClickHouse 的分区 id、MySQL 的子分区名，都只属于一家。

### PartitionOperation

执行器已经执行、或在 dry run 下将会执行的一条语句。

| 字段 | 含义 |
|---|---|
| `action` | 后端自己的动词拼写（`create`、`drop`、`split`、`merge`、`detach` 等） |
| `name` | 语句作用的对象 |
| `parent` | 语句有上级对象时的所属对象 |
| `sql` | 后端选择记录时的渲染 SQL |
| `level` | 受影响对象有层级时的嵌套深度 |

动词保持自由字符串是有意的：把 `split` 和 `merge` 都归并成 `alter`，会丢掉
运维人员真正需要区分的动作。

### PartitionReport

目录状态与操作结果共用的一个报告信封。

| 字段 | 含义 |
|---|---|
| `target` | 作用范围：父表、单表，或分区函数/方案名 |
| `engine` | 执行器记录时的后端名 |
| `extras` | 引擎独有的报告级信息，例如 SQL Server 的函数/方案/表集合 |
| `partitions` | 后端读取到的目录行，保持读取顺序 |
| `missing` | 计划期望但目录中没有的 `(parent, name)` |
| `orphans` | 已存在但计划未描述的分区 |
| `issues` | 只读发现：空隙、重叠、策略不匹配 |
| `operations` | 执行器已执行或将会执行的语句 |
| `added` | 按名称报告结果的后端新建的名称 |
| `dropped` | 已删除的名称 |
| `skipped` | 被有意拒绝的工作，`(name, reason)` |
| `errors` | 非事务 DDL 引擎的逐语句失败 |
| `dry_run` | 报告描述的是否为未执行的工作 |

便捷方法：

- `children_of(name)`：某一行的直接子行。
- `partition_names`：位于目标顶层的分区名，不含目标行本身。
- `tree`：按父名分组的直接子行。扁平报告返回 `{}`，表示没有树可展示，
  而不是虚构一棵树。
- `leaves`：没有被其它行当作父行的行。扁平报告里每一行都是叶子。
- `has_errors`：`errors` 是否非空。

## 批量报告与成对报告

`PartitionBatchReport` 包装多个目标的报告，并给出调用方声明为“必须成对”的两个
目标之间的漂移。它不会压平各目标的报告：每个目标仍保留自己的 `missing` 和
`orphans`。

| 字段 | 含义 |
|---|---|
| `reports` | `target -> PartitionReport`，各目标各自的原始报告 |
| `pairs` | 调用方声明的成对名称，按声明顺序；独立批量时为空 |
| `differences` | 成对目标中只在一侧存在的一级分区 |
| `issues` | 无法比较的原因：计划不兼容、边界不一致等 |

`PairedDifference` 描述 `differences` 中的一行：

| 字段 | 含义 |
|---|---|
| `pair` | 调用方给这对目标起的名字，如 `log_tables` |
| `key` | 比较两侧所用的归一化 bucket，如 `2026_01` |
| `present_in` | 持有该行的一侧：`left` 或 `right` |
| `left_partition` | 左侧目录报告的名称，不存在时为 `None` |
| `right_partition` | 右侧目录报告的名称，不存在时为 `None` |

`differences` 的 B 语义比两个报告 `missing` 集合的对称差更窄：

- 只列出“一侧实际持有、另一侧没有”的一级分区，`present_in` 指明持有侧。
- 两边都不存在的 bucket 不算差异，留在各自报告的 `missing` 中，因为它属于
  单个目标的事实。
- 两边都存在但边界文本不一致的 bucket 也不算差异，进入 `issues`，因为这对
  目标在结构上不可比较。
- 计划本身不兼容（method、columns、interval 或显式 bounds 不一致）同样进入
  `issues`，不输出任何差异。
- 差异按 `(pair, key)` 排序，因此看到相同漂移的两个后端会给出相同顺序。

`extras` 只用于临时或单一引擎独有的信息。稳定、共享的形状不放进 `extras`：
要么给 core 对象增加字段，要么在后端子类化并写明新增字段，绝不要引入一个让
其它后端不得不模仿的私有键。

## 协议

每个动词都是独立协议。一个声明了全部动词的协议会承诺过多：MySQL 没有
`validate`，ClickHouse 没有 `ensure`，SQL Server 用合并边界替代按范围删除。

| 动词 | 同步协议 | 异步协议 | 提供该能力的后端 |
|---|---|---|---|
| 读取分区状态 | `PartitionInventory` | `AsyncPartitionInventory` | PostgreSQL、Oracle、SQL Server、MySQL、MariaDB |
| 补齐缺失分区 | `PartitionEnsurer` | `AsyncPartitionEnsurer` | PostgreSQL、Oracle、SQL Server、MySQL、MariaDB |
| 按截止点删除 | `PartitionRetention` | `AsyncPartitionRetention` | PostgreSQL、Oracle、MySQL、MariaDB |
| 只报告问题 | `PartitionValidator` | `AsyncPartitionValidator` | PostgreSQL、Oracle、SQL Server |

ClickHouse 有意不在表中。它的维护面是 `DROP` / `DETACH` / `ATTACH` 加服务器
分配的分区 id，没有计划、没有报告，也没有 `ensure`；把这些行包装进本契约的
信封只会增加无人需要的翻译。ClickHouse 的服务保留自己的内省行和自己的测试。
SQL Server 不在 `PartitionRetention` 中也是同一个道理：它用 `drop_or_merge`
合并边界，而不是按范围删除；那不是同一个动词换了个名字。

用 `isinstance` 探测：

```python
from rhosocial.activerecord.backend.partition import PartitionRetention

if isinstance(executor, PartitionRetention):
    report = executor.drop_before(plan, cutoff, dry_run=True)
```

runtime-checkable 协议的 `isinstance` 只检查方法是否存在。它无法区分同步与
异步执行器，因为按项目的对等规则两者方法名完全相同；调用方本来就持有具体的
同步或异步后端对象。

## 仍归后端所有的部分

- 计划与策略类，包括树的深度、子分区策略、命名、边界方向、文件组和服务器
  分配的分区 id。
- 破坏性动词：按边界 `drop_before`、SQL Server 的 `drop_or_merge`、
  Oracle 的 `drop_partition(name)`、ClickHouse 的 `detach` / `attach`。
- 事务语义。PostgreSQL 和 MySQL 可以把一个工作单元包进事务；Oracle 逐语句
  提交，并把部分失败记录在 `errors` 中。
- “需要先换一个动词”的原因，例如 MySQL 的 `REORGANIZE PARTITION` 要求、
  Oracle 的 `MAXVALUE` 终止分区。
