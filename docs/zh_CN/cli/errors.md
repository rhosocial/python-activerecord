# 错误与校验

CLI 把模型层和后端异常翻译成命令级错误，不改变框架语义：模型仍在构造时校验，
`save()` 仍会重新执行业务规则校验。

## 消息与退出码映射

| 场景 | 消息开头 | 退出码 |
|---|---|---|
| 记录数据不合法 | `Invalid data for Model ...` | 1 |
| 约束冲突 | `Integrity constraint failed ...` | 1 |
| 记录不存在 | `Model with pk=... was not found` | 3 |
| 只读模型 | `... is read-only ...` | 6 |
| 需要确认 | `... Pass --yes ...` | 5 |
| 版本冲突 | `Record version mismatch ...` | 1 |
| 锁或死锁 | `Record is locked ...` / `Deadlock detected ...` | 1 |
| 连接失败 | `Database connection failed ...` | 1 |
| 其它数据库错误 | `Database error ...` | 1 |
| 后端或配置类缺失 | `Cannot import the ...` | 4 |
| 未知异常 | `Unexpected error (TypeName): ...` | 1 |

完整退出码见[输出与管道](output.md#退出码)。

## 模型异常与 CLI 错误

查询无结果时模型层抛 `backend.errors.RecordNotFound`；CLI 层抛自己的
`CliNotFoundError` 并映射为退出码 3。两者刻意保持独立：

- `RecordNotFound` 描述查询结果，不带退出码；
- `CliNotFoundError` 描述命令结果。

命令处理层用 `raise ... from exc` 翻译，所以原始异常仍在异常链里，便于排查。

## 校验

校验发生在两个时点：

1. 构造模型实例时（`dml create`、`bulk create`，以及 `dml update` 加载的数据）；
2. `save()` 内部：`model_validate(model_dump())` 加上 `validate_record()` 业务规则。

失败不写库，退出码 1。`dml update` 的消息会带模型和主键：

```text
Error: Invalid data for User pk=42: age: Input should be less than or equal to 100
```

批量操作会指出条目（已知时也指出主键）：

```text
Error: Invalid data for User (item 2): name: String should have at least 2 characters
Error: Bulk update failed at item 2 (pk=2): age: Input should be <= 100
```

批量命令在发出 SQL 前校验整批，失败时表数据保持不变。

## 取消操作

拒绝确认不算错误：

- 退出码 0；
- stderr 输出 `Operation cancelled.`，不带 `Error:` 前缀；
- 不写库。

非交互环境不会弹出提示：破坏性命令缺少 `--yes` 时以退出码 5 结束，并提示补 `--yes`。

## 未知异常

已知异常按上表映射；其余只输出一行：

```text
Unexpected error (ValueError): ...
```

不打印 traceback。需要完整堆栈时用 `--log-level DEBUG`，细节会进入日志流（stderr）。

## 让 AI 使用这些命令

- 按退出码分支：3 表示“不存在”，5 表示“需要确认”，6 表示“只读”，
  4 表示“导入路径错误”，1 是普通失败。
- 阅读库代码时区分 `RecordNotFound`（模型层）与 `CliNotFoundError`（CLI 层）：
  命令返回的是后者。
- 校验失败意味着没有写入，不要发起补偿删除。
- 单独收集 stderr：错误行以 `Error:` 开头（未知异常为 `Unexpected error (...)`），不是合法 JSON。
- 只在排查时加 `--log-level DEBUG`，它会在 stderr 产生大量输出。
