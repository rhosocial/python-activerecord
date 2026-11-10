# 批量 DML

批量命令调用 `Model.bulk_create()`、`bulk_update()`、`bulk_delete()`，校验、事件、
事务、分批和软删除都保持框架语义；CLI 只负责解析载荷。

## 输入

`--data` 支持 JSON 数组、单个对象、`@file`、stdin（`@-` / `-`）以及 JSONL（每行一个对象）。
自动识别有歧义时可用 `--input-format json|jsonl` 强制指定：

```bash
# JSON 数组
rhosocial-activerecord dml bulk create --model app.models:User \
  --data '[{"name": "A"}, {"name": "B"}]' -o json

# 从 stdin 读取 JSONL
cat users.jsonl | rhosocial-activerecord dml bulk create --model app.models:User \
  --data @- --input-format jsonl -o json
```

自动识别看第一个非空白字符：`[` 为 JSON 数组，`{` 为单个对象或 JSONL 流，其它按 JSONL 解析。

## 批量创建

```bash
rhosocial-activerecord dml bulk create --model app.models:User \
  --data '[{"name": "Grace", "age": 26}, {"name": "Heidi", "age": 33}]' \
  --batch-size 2 -o json
```

- 输出按输入顺序排列的新建记录列表。
- `--batch-size N` 按 `N` 条一组分批执行。
- 校验失败会指出第几条：

```text
Error: Invalid data for User (item 2): name: String should have at least 2 characters
```

任意一条校验失败，整批都不会写库。

## 批量更新

```bash
rhosocial-activerecord dml bulk update --model app.models:User \
  --data '[{"id": 1, "age": 31}, {"id": 2, "age": 26}]' \
  --update-fields age -o json
```

- 每个对象都要带主键和更新字段。
- 不传 `--update-fields` 时，所有对象的非主键字段集合必须一致；否则命令拒绝并要求显式指定。
- `--update-fields a,b` 会在发出 SQL 前校验字段是否属于模型。
- 记录缺失会让整批失败，并指出条目和主键：

```text
Error: User bulk update item 2 with pk=2 was not found
```

- 校验失败会指出条目和主键：

```text
Error: Bulk update failed at item 2 (pk=2): age: Input should be <= 100
```

- 输出：`{"action": "update", "affected": 2}`。

## 批量删除

```bash
rhosocial-activerecord dml bulk delete --model app.models:User \
  --data '[1, 2]' --yes -o json
```

- `--data` 放主键：标量、复合主键的 JSON 对象，或 JSONL。
- 确认规则与单条删除一致：非交互必须 `--yes`，`--dry-run` 可预览。
- 软删除模型报告 `soft_delete`。

## 输出形态

| 命令 | JSON 输出 |
|------|-----------|
| `bulk create` | 新建记录数组 |
| `bulk update` | `{"action": "update", "affected": N}` |
| `bulk delete` | `{"action": "delete"\|"soft_delete", "affected": N}` |

`-o csv` / `-o tsv` 会输出带表头的摘要行（`action,affected`），`--no-header` 省略表头。
更新和删除的 `-o value` 只输出受影响行数。

## 让 AI 使用这些命令

- 大批量用 `--batch-size`（例如 100–500 条）分块发送，CLI 会按块保留框架校验。
- 创建用 `-o json`（需要数据库生成的主键）；更新/删除只看影响行数时用 `-o value`。
- 载荷在 SQL 之前整体校验，失败即“没有写入”，不要尝试补偿删除。
- `bulk update` 要求所有对象字段一致；数据不齐时显式传 `--update-fields`。
- 大载荷通过 stdin 传 JSONL，避免命令行长度限制。
