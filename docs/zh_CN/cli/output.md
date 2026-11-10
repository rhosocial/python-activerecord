# 输出、管道与退出码

机器格式只把数据写到 stdout。提示、日志和错误始终写 stderr，因此载荷可以直接管道或捕获，
无需过滤。

## 输出格式

`-o table|json|jsonl|csv|tsv|value`：

| 格式 | 用途 |
|------|------|
| `json` | 列表为数组，单条为对象，计数为标量 |
| `jsonl` | 每行一个 JSON 值，适合管道和流式处理 |
| `csv` / `tsv` | 表头 + 数据行；`--no-header` 省略表头 |
| `value` | 裸标量，用于 `count`、`exists` 或标量聚合 |
| `table` | Rich 表格；没有 Rich 时回退 JSON |

stdout 不是 TTY 且未指定 `-o` 时默认 `json`；TTY 上默认 `table`。

`--fields id,name` 限制输出列。列表结果会按模型字段（或字典键）校验名称，
未知名称会列出可用字段；标量结果会忽略 `--fields`。

`-o value` 只对标量结果有效。用于列表或单条记录时以退出码 1 报
`Error: -o value is only valid for scalar results`。

## 写操作结果

DML 删除和批量更新/删除返回摘要对象：

| 命令 | JSON | CSV/TSV 列 |
|------|------|------------|
| `dml delete` | `{"action", "pk", "affected"}`（可能含 `deleted_at_field`、`dry_run`） | `action,pk,affected`（含附加列） |
| `dml bulk update` | `{"action", "affected"}` | `action,affected` |
| `dml bulk delete` | `{"action", "affected"}` | `action,affected` |

这些命令的 `-o value` 只输出受影响行数。`dml create` 与 `dml bulk create` 返回新建记录，
因此 `json` / `jsonl` / `csv` / `tsv` 描述的是记录行，而不是摘要对象。

## 管道

```bash
cat user.json | rhosocial-activerecord dml create --model app.models:User --data @-

rhosocial-activerecord dql list --model app.models:User -o jsonl \
  | jq -c 'select(.status == "active")'

rhosocial-activerecord dql count --model app.models:User -o value
```

- `--data @-` 与 `--data -` 从 stdin 读取。
- 下游提前关闭（例如 `| head`）时不打印 traceback，退出码为 141。
- 长管道优先用 JSONL：每行都是完整值。

## 日志与提示

- 框架默认日志级别为 `WARNING`，日志写 stderr。
- `--log-level DEBUG` 输出后端和模型细节，便于排查连接或模型加载问题。
- `--quiet` 关闭自动分页提示等非错误 stderr 输出，不会屏蔽错误。

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功，包括用户取消确认 |
| 1 | 模型、连接、校验或数据库错误 |
| 2 | 命令行用法错误（argparse） |
| 3 | 记录不存在 |
| 4 | 后端或连接配置类无法导入 |
| 5 | 非交互环境下的破坏性命令需要 `--yes` |
| 6 | 只读模型拒绝 DML |
| 141 | 下游管道关闭 |

## 让 AI 使用这些命令

- 默认用 `-o json`（流式处理用 `jsonl`），不要解析 `table`。
- stdout 只有载荷；stderr 上的文本都当作诊断信息，不要当数据。
- 单独处理 141：表示消费方停止读取，不是命令失败。
- 模型字段很多时用 `--fields` 让载荷更小、更稳定。
- 需要同时收集 stderr 日志时，用 `--quiet` 配合 `-o json`；分页提示属于信息性输出，可以丢弃。
