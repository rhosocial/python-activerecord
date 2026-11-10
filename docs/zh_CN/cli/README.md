# 模型命令行接口

`rhosocial-activerecord` 是**模型**入口，与 `rhosocial-activerecord-<backend>`
（例如 `rhosocial-activerecord-sqlite`）不是同一个命令：后端命令执行 SQL 并做数据库
内省，本命令通过框架 API 操作 ActiveRecord 模型类。

CLI 只是薄适配层，不拼接 SQL：DML 调用 ActiveRecord 方法，DQL 调用 `ActiveQuery`，
`set` / `cte` 执行用户自己构造的 `SetOperationQuery` / `CTEQuery`。

## 文档页面

| 页面 | 内容 |
|------|------|
| [DML](dml.md) | `dml create/update/delete`、dry-run、软删除、只读模型 |
| [批量 DML](bulk.md) | `dml bulk create/update/delete`、JSON/JSONL 输入、分批 |
| [DQL](dql.md) | `dql get/list/count/exists/aggregate/run`、过滤、分页、聚合 |
| [集合操作与 CTE](set-cte.md) | `set union/union-all/intersect/except`、`set run`、`cte run` |
| [连接与模型引用](connections.md) | 模型引用、后端/配置类、命名连接、异步模型 |
| [输出与管道](output.md) | 输出格式、字段、管道、日志、退出码 |
| [错误](errors.md) | 异常映射、校验语义、取消操作 |

可运行示例在
[`docs/examples/chapter_13_cli`](../../examples/chapter_13_cli/README.md)。

## 安装

CLI 随核心包提供。`table` 输出需要可选依赖 `[cli]`：

```bash
pip install "rhosocial-activerecord[cli]"
```

没有 `rich` 时 `-o table` 回退为 JSON，不会报错。

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

## 功能汇总

| 命令 | 用途 | 主要参数 | 典型输出 |
|------|------|----------|----------|
| `dml create` | 插入一条记录 | `--data` | 新建记录 |
| `dml update` | 按主键更新一条记录 | `--pk`、`--data` | 更新后的记录 |
| `dml delete` | 删除一条记录 | `--pk`、`--yes`、`--dry-run` | `action`、`pk`、`affected` |
| `dml bulk create` | 批量插入 | `--data`、`--input-format`、`--batch-size` | 新建记录列表 |
| `dml bulk update` | 批量更新 | `--data`、`--update-fields`、`--batch-size` | `action`、`affected` |
| `dml bulk delete` | 按主键批量删除 | `--data`、`--yes`、`--dry-run` | `action`、`affected` |
| `dql get` | 按主键取一条记录 | `--pk` | 一条记录 |
| `dql list` | 过滤、排序、分页查询 | `--where`、`--order-by`、`--select`、分页参数 | 记录列表 |
| `dql count` | 统计匹配数量 | `--where` | 标量 |
| `dql exists` | 判断是否存在匹配 | `--where` | 标量 |
| `dql aggregate` | 标量或分组聚合 | `--fn`、`--field`、`--group-by`、`--distinct` | 标量或行 |
| `dql run` | 执行用户传入的 `ActiveQuery` | `--query`、`--mode` | 由 `--mode` 决定 |
| `set union` 等 | 合并两个模型查询 | `--left-model`、`--right-model`、`--left-where`、`--right-where` | 行 |
| `set run` | 执行用户传入的 `SetOperationQuery` | `--query` | 行 |
| `cte run` | 执行用户传入的 `CTEQuery` | `--query` | 行 |

所有命令都遵循：

- stdout 只放数据；提示、日志、错误都写 stderr。
- `-o` 在 TTY 下默认 `table`，非 TTY 默认 `json`。
- 退出码稳定，见[输出与管道](output.md#退出码)。
- 非交互环境下的破坏性命令不会弹提示，缺少 `--yes` 时以退出码 5 结束。

## 快速开始

```bash
# 创建一条记录
rhosocial-activerecord dml create \
  --model app.models:User \
  --backend-class mypkg.backend:MyBackend \
  --config-class mypkg.config:MyConnectionConfig \
  --config database=app.db \
  --data '{"name": "Alice", "age": 30}' -o json

# 条件查询
rhosocial-activerecord dql list \
  --model app.models:User \
  --where "status=active" --order-by "created_at desc" --limit 20 -o json

# 只输出计数
rhosocial-activerecord dql count --model app.models:User -o value
```

只有模型模块自己不调用 `configure()` 时才需要连接参数，见[连接与模型引用](connections.md)。

## 让 AI 使用这些命令

- 优先 `-o json` 或 `-o jsonl`：可解析，且不会混入日志行。
- 破坏性命令始终加 `--yes`，交互提示会阻塞代理。
- 按退出码分支，不要匹配消息文本：退出码稳定，消息面向人类。
- `--where` 表达力不够时，用 `dql run` 配合项目里的小型 Python 查询工厂，避免复杂谓词的引号问题。
- 各章节末尾都有“让 AI 使用这些命令”的小节，按命令类型给出具体建议。
