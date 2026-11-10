# DML：单条记录写入

`dml create`、`dml update`、`dml delete` 每次只操作一条记录，直接调用模型的
`save()` / `delete()`，所以事件、时间戳、乐观锁、软删除和校验都保持框架语义。

## 创建

```bash
rhosocial-activerecord dml create --model app.models:User \
  --data '{"name": "Alice", "email": "alice@example.com", "age": 30}' -o json
```

`--data` 支持：

| 形式 | 含义 |
|------|------|
| `'{"k": "v"}'` | 内联 JSON 对象 |
| `@user.json` | 从文件读取 |
| `@-` 或 `-` | 从 stdin 读取 |

载荷必须是单个 JSON 对象。构造模型时执行一次校验，`save()` 里再执行一次业务规则校验。
失败时不写库，退出码 1。详见[错误](errors.md#校验)。

## 更新

```bash
rhosocial-activerecord dml update --model app.models:User \
  --pk 42 --data '{"age": 31}' -o json
```

- `--pk` 是主键值；复合主键用 JSON 对象
  （`--pk '{"order_id": 1, "product_id": 101}'`，或 `--pk-json`）。
- 主键字段不能被更新。需要改主键时删除并新建；命令会在发出 SQL 前拒绝。
- 只修改传入的字段；命令会先读取记录。

## 删除

```bash
rhosocial-activerecord dml delete --model app.models:User --pk 42 --yes -o json
```

在 TTY 上删除会要求确认。stdin 或 stdout 不是终端时必须传 `--yes`，否则以退出码 5 结束。
`--dry-run` 只报告计划、不写库：

```bash
rhosocial-activerecord dml delete --model app.models:User --pk 42 --yes --dry-run
```

输出：

```json
{"action": "delete", "pk": 42, "affected": 1, "dry_run": true}
```

软删除模型的动作是 `soft_delete`，并带上时间戳字段：

```json
{"action": "soft_delete", "pk": 42, "affected": 1, "deleted_at_field": "deleted_at"}
```

## 只读模型

声明 `__read_only__ = True`（例如通过 `ReadOnlyMixin`）的模型会在连接前拒绝所有 DML，
退出码 6：

```text
Error: ReadOnlyUser is read-only (__read_only__ = True); 'dml create' is not allowed.
```

只读模型的 DQL 仍然可用。

## 让 AI 使用这些命令

- `dml delete` 始终加 `--yes`，提示会阻塞代理。
- 需要确认目标行和动作（`delete` 还是 `soft_delete`）时先跑 `--dry-run`。
- 有并发写入时 `dml update` 不是幂等的：版本冲突会抛 `StaleRecordError`、退出码 1，
  先用 `dql get` 重读，再重试。
- 用 `-o json` 并检查 `action`，不要假设一定是物理删除：软删除模型会保留行。
- 主键不存在时退出码 3 且不写库；把 3 当作“记录不存在”，而不是基础设施故障。
