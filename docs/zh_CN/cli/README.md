# ActiveRecord 模型命令行

`rhosocial-activerecord` 是**模型**入口，与
`rhosocial-activerecord-<backend>`（例如 `rhosocial-activerecord-sqlite`）
不是同一个命令：后端命令执行 SQL、检查数据库结构，本命令通过框架 API
操作 ActiveRecord 模型类。

## 安装

CLI 随核心包发布。`table` 输出需要可选的 `[cli]` extra：

```bash
pip install "rhosocial-activerecord[cli]"
```

没有 `rich` 时，`-o table` 回退到 JSON，不会报错。

## 命令树

```text
rhosocial-activerecord
├── dml
│   ├── create
│   ├── update
│   ├── delete
│   └── bulk
│       ├── create
│       ├── update
│       └── delete
├── dql
│   ├── get
│   ├── list
│   ├── count
│   ├── exists
│   ├── aggregate
│   └── run
├── set
│   ├── union
│   ├── union-all
│   ├── intersect
│   ├── except
│   └── run
└── cte
    └── run
```

CLI 是薄适配层：DML 调用 ActiveRecord 方法，DQL 调用 `ActiveQuery`，
`set` / `cte` 执行用户提供的 `SetOperationQuery` / `CTEQuery` 对象；
CLI 不拼接 SQL。

## 模型引用

模型引用写作 `module:Class`，不是 `module.Class`：

```bash
rhosocial-activerecord dql list --model app.models:User
```

CLI 在导入模型前把当前目录和每个 `--path DIR` 加入 `sys.path`。
模型类必须是 `ActiveRecord` 或 `AsyncActiveRecord` 子类。

## 后端与连接

核心包不维护后端列表。请显式命名项目实际使用的类：

- 后端类：`--backend-class MODULE:CLASS`，否则使用模型模块自己的
  `configure()`。
- 连接配置：`--connection MODULE:CALLABLE`，或
  `--config-class MODULE:CLASS` 加 `--config KEY=VALUE`，否则使用模型模块
  自己的 `configure()`。

类引用支持 `module:Class` 或点号形式 `module.Class`。异步模型要指定异步
后端类。

```bash
# SQLite 文件，同步模型
rhosocial-activerecord dql list \
  --model app.models:User \
  --backend-class rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend \
  --config-class rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig \
  --config database=app.db \
  --where "status=active" --order-by "created_at desc" --limit 20

# 命名连接 + 显式后端类
rhosocial-activerecord dql list \
  --model app.models:User \
  --backend-class rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend \
  --connection app.connections:prod_db \
  -o json
```

如果模型模块已经调用 `configure()`，可以省略 `--backend-class` 和
`--connection` / `--config-class`；此时 `--config` 会覆盖已有配置。

## DML

```bash
# 创建单条记录
rhosocial-activerecord dml create --model app.models:User \
  --data '{"username": "alice", "email": "alice@example.com", "age": 30}'

# 按主键更新单条记录
rhosocial-activerecord dml update --model app.models:User --pk 42 \
  --data '{"age": 31}'

# 删除单条记录；非交互环境必须加 --yes
rhosocial-activerecord dml delete --model app.models:User --pk 42 --yes
```

`--data` 接受内联 JSON、`@file.json`、`@-`（stdin）或 `-`（stdin）。
`create` 和 `update` 只接受一个 JSON 对象；`update` 不能修改主键字段。

TTY 下删除会二次确认；stdin/stdout 不是终端时必须传 `--yes`，否则以退出码
5 结束。模型混入软删除行为时，输出 action 为 `soft_delete`，否则为
`delete`。`--dry-run` 只报告计划，不写库。

只读模型（`ReadOnlyMixin`、`__read_only__ = True`）会在连接前拒绝所有 DML，
退出码 6；DQL 仍可用。

### 批量 DML

```bash
# 从 JSON 数组创建
rhosocial-activerecord dml bulk create --model app.models:User \
  --data '[{"username": "a", "email": "a@example.com", "age": 20}, {"username": "b", "email": "b@example.com", "age": 30}]'

# 从 stdin 读取 JSONL
cat users.jsonl | rhosocial-activerecord dml bulk create --model app.models:User --data @-

# 批量更新；每个对象包含主键和更新字段
rhosocial-activerecord dml bulk update --model app.models:User \
  --data '[{"id": 1, "age": 21}, {"id": 2, "age": 31}]'

# 按主键批量删除
rhosocial-activerecord dml bulk delete --model app.models:User \
  --data '[1, 2]' --yes
```

批量命令调用 `Model.bulk_create()` / `bulk_update()` / `bulk_delete()`，
验证、事件、事务和软删除语义由框架保持。`bulk update` 要求所有对象包含
同一组更新字段，`--update-fields` 可显式指定；`--batch-size` 用于分批。
`bulk delete` 与单条删除使用相同的确认规则。

## DQL

```bash
# 按主键查询
rhosocial-activerecord dql get --model app.models:User --pk 42

# 等值过滤、排序、分页
rhosocial-activerecord dql list --model app.models:User \
  --where "status=active" --order-by "created_at desc" --limit 20 --offset 0

# 计数与存在性
rhosocial-activerecord dql count --model app.models:User --where "status=active" -o value
rhosocial-activerecord dql exists --model app.models:User --where "status=active" -o value

# 聚合（分组或标量）
rhosocial-activerecord dql aggregate --model app.models:User \
  --fn count --field '*' --group-by status -o json
```

`dql list` 未指定 limit 时默认注入 100，并在 stderr 提示。可用
`--no-limit`、`--limit N`、`--offset N` 或 `--page N --page-size M` 控制。

`--select id,name` 限制查询列。`--include-deleted` / `--only-deleted` 在模型
支持软删除时分别调用 `query_with_deleted()` / `query_only_deleted()`。

`dql run` 执行 `module:callable` 或 `module:Class.method` 返回的任意
`ActiveQuery` 及其派生类：

```python
# app/queries.py
from app.models import User

def active_users():
    return User.query().where(User.c.status == "active")
```

```bash
rhosocial-activerecord dql run --model app.models:User \
  --query app.queries:active_users -o json

# 或模型 classmethod
rhosocial-activerecord dql run --model app.models:User \
  --query app.models:User.active_users -o json
```

`--mode list|one|count|exists|aggregate` 选择执行方式。DQL 的判定只看返回值
类型：`ActiveQuery` 及派生类，包括业务封装和返回 `self` 的自定义
`__query_class__` 便利方法。

## SetOperation 与 CTE

简单集合操作使用两个模型查询：

```bash
rhosocial-activerecord set union \
  --left-model app.models:User --right-model app.models:Admin \
  --left-where "status=active" --right-where "status=active" -o json
```

复杂组合传入返回现有 `SetOperationQuery` / `CTEQuery` 的工厂：

```bash
rhosocial-activerecord set run --model app.models:User \
  --query app.queries:active_users_union -o json

rhosocial-activerecord cte run --model app.models:User \
  --query app.queries:org_tree -o json
```

`SetOperationQuery` / `CTEQuery` 以字典行返回结果；CLI 调用 `aggregate()`，
这两类查询不支持 `all()` 或 `limit()`。

## 输出格式

`-o table|json|jsonl|csv|tsv|value`：

- `json`：列表为数组，单条为对象。
- `jsonl`：每行一个 JSON 对象，适合管道。
- `csv` / `tsv`：带表头的行；`--no-header` 省略表头。
- `value`：`count`、`exists` 或标量聚合的裸值。
- `table`：人类可读的 Rich 表格；Rich 不可用时回退 JSON。

stdout 不是 TTY 且未指定 `-o` 时默认 `json`。机器格式只向 stdout 写数据。
`--quiet` 抑制默认分页提示等非错误 stderr。`--fields id,name` 限制输出列。

## 管道

```bash
cat user.json | rhosocial-activerecord dml create --model app.models:User --data @-

rhosocial-activerecord dql list --model app.models:User -o jsonl | jq -c 'select(.status == "active")'

rhosocial-activerecord dql count --model app.models:User -o value
```

下游管道提前关闭（如 `| head`）时不打印 traceback，以退出码 141 结束。

## 示例

每个命令组的可运行脚本在
[`docs/examples/chapter_13_cli`](../../examples/chapter_13_cli/README.md)。
脚本会创建临时 SQLite 数据库，并打印命令、stdout、stderr 和退出码。

## 日志

框架默认日志级别为 `WARNING`。排查连接或模型问题时使用
`--log-level DEBUG`。日志始终写 stderr。

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 模型、连接、验证或数据库错误 |
| 2 | 命令行用法错误（argparse） |
| 3 | 记录不存在 |
| 4 | 后端或连接配置类无法导入 |
| 5 | 非交互环境下的破坏性命令需要 `--yes` |
| 6 | 只读模型拒绝 DML |
| 141 | 下游管道关闭 |

## 同步与异步模型

CLI 自动识别模型类型。`ActiveRecord` 使用同步后端；`AsyncActiveRecord`
使用异步后端和 CLI 内部事件循环。没有 `--async` 参数，但
`--backend-class` 必须与模型匹配：异步模型用 `AsyncStorageBackend` 子类，
同步模型用 `StorageBackend` 子类。

## Python 模块形式

```bash
python -m rhosocial.activerecord.cli dql list --model app.models:User -o json
```
