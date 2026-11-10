# DQL：查询、分页与聚合

`dql` 直接调用 `ActiveQuery` 方法。CLI 没有第二套过滤语法：它把简单参数映射到
`where()`、`order_by()`、`select()`、`limit()`、`offset()`。

## 命令

| 命令 | 用途 |
|------|------|
| `dql get` | 按主键取一条记录 |
| `dql list` | 过滤、排序、分页的列表 |
| `dql count` | 匹配记录数 |
| `dql exists` | 是否存在匹配 |
| `dql aggregate` | 标量或分组聚合 |
| `dql run` | 执行用户传入的 `ActiveQuery` |

## 过滤

```bash
rhosocial-activerecord dql list --model app.models:User \
  --where "status=active" --where "age=30" \
  --order-by "created_at desc" --order-by "id asc" \
  --select id,name --limit 20 --offset 0 -o json
```

- `--where` **只支持等值**：`field=value`。可重复，多个条件按 AND 组合，值会转换成字段类型。
- 未知字段在 SQL 之前被拒绝，错误消息会列出可用字段。
- `--order-by` 接受 `field` 或 `field asc|desc`。
- `--select` 限制查询列，并校验字段名。
- 需要比较运算（`>=`、`LIKE`、`IN` 等）时，用 [`dql run`](#执行自定义查询)。

软删除模型额外提供两个可见性参数：

```bash
rhosocial-activerecord dql list --model app.models:Task --include-deleted
rhosocial-activerecord dql list --model app.models:Task --only-deleted
```

它们分别调用 `query_with_deleted()` / `query_only_deleted()`，不能同时使用。

## 分页

会应用分页的命令：`dql list`、带 `--group-by` 的 `dql aggregate`、
`dql run --mode list|aggregate`。
不会应用分页的命令：`dql get`、`dql count`、`dql exists`、
`dql run --mode one|count|exists`。

参数：

| 参数 | 作用 |
|------|------|
| `--limit N` | 最多 `N` 行 |
| `--offset N` | 跳过 `N` 行 |
| `--page N --page-size M` | 等价于 `limit M offset (N-1)*M`；两者必须同时给出且为正数 |
| `--no-limit` | 关闭自动注入 |
| `--limit 0` | 同样表示不限制 |
| `--quiet` | 不打印自动分页提示 |

### 自动分页注入

当可分页命令没有显式 limit、且查询本身也没有 limit 时，CLI 会注入
`DEFAULT_LIST_LIMIT`（100），并在 stderr 说明：

```text
Showing first 100 rows (default pagination); use --limit N or --no-limit to change.
```

分组聚合的文案不同：

```text
Showing first 100 groups (default pagination); use --limit N or --no-limit to change.
```

提示只写 **stderr**，stdout 仍是纯数据。`--quiet` 关闭提示；`--no-limit`
用于明确要求全量查询（防止误把整表读出来）。

标量聚合从不分页：`dql aggregate --fn count` 执行 `COUNT(*)`，只返回一个值。

## 计数与存在性

```bash
rhosocial-activerecord dql count --model app.models:User --where "status=active" -o value
rhosocial-activerecord dql exists --model app.models:User --where "status=active" -o value
```

`-o value` 输出 `4` 或 `true` / `false`；`-o json` 输出 JSON 标量。

## 聚合

```bash
# 标量：一个值
rhosocial-activerecord dql aggregate --model app.models:Order \
  --fn sum --field total -o value

# 分组：每组一行
rhosocial-activerecord dql aggregate --model app.models:Order \
  --fn count --field '*' --group-by status -o json
```

- `--fn` 取值：`count`、`sum`、`avg`、`min`、`max`。
- `--field '*'` 只对 `count` 有效。
- `--field` 必须是模型字段；未知字段在 SQL 之前被拒绝。
- `--group-by` 可重复，每个名称都会校验。
- `--distinct` 在聚合内部应用 `DISTINCT`。
- 分组聚合返回字典行；标量聚合返回单个值。

分组结果为空时无法推断列名，可能需要显式 `--fields`，否则报错：

```text
Error: The query returned no rows, so output fields cannot be inferred. Pass --fields explicitly.
```

## 执行自定义查询

`dql run` 执行 `module:callable` 或 `module:Class.method` 返回的 `ActiveQuery`（或子类）：

```python
# app/queries.py
from app.models import User

def active_users():
    return User.query().where(User.c.age >= 30).order_by(User.c.age.desc())
```

```bash
rhosocial-activerecord dql run --model app.models:User \
  --query app.queries:active_users -o json

# 返回查询的模型 classmethod
rhosocial-activerecord dql run --model app.models:User \
  --query app.models:User.active_users -o json
```

- 工厂函数**无参数调用**。
- 返回值必须是 `ActiveQuery` 或子类，包括返回 `self` 的业务包装和 `__query_class__`
  方法；其它类型会被拒绝，并在消息中说明期望类型。
- `--mode` 决定执行方式：

| mode | 等价调用 |
|------|----------|
| `list`（默认） | `all()` |
| `one` | `one()`；无记录时退出码 3 |
| `count` | `count()` |
| `exists` | `exists()` |
| `aggregate` | `aggregate()`，返回字典行 |

- `list` 和 `aggregate` 会应用分页（含自动注入）。
- `one`、`count`、`exists` 忽略分页参数。

## 让 AI 使用这些命令

- `--where` 只支持等值，不要尝试 `age>=30`；把比较写进查询工厂，再用 `dql run`。
- 自动分页在 stdout 上不可见，只在 stderr 提示。建议显式 `--limit N`（或 `--no-limit`），
  解析 stderr 时加 `--quiet`。
- 大批量 `dql list` 之前先用 `dql count` 估算规模。
- 需要逐行交给其它工具时用 `-o jsonl`。
- `dql run` 的工厂从 `--path` 目录导入；复杂谓词写在项目代码里，不要塞进字符串。
- 分组聚合可能为空时传 `--fields`，避免列名推断错误。
