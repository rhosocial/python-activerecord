# 模型 CRUD 命令行工具

`rhosocial-activerecord` 是面向模型 CRUD 的入口，**不是**后端 CLI
`rhosocial-activerecord-<backend>`（例如 `rhosocial-activerecord-sqlite`）。
后端 CLI 负责执行 SQL 和内省数据库；本命令负责对 ActiveRecord 模型做一次
增删改查。

## 安装

CLI 随核心包一起发布。`table` 输出需要可选的 `[cli]` extra：

```bash
pip install "rhosocial-activerecord[cli]"
```

未安装 `rich` 时，`-o table` 会自动回退为 JSON，不会报错。

## 命令结构

```text
rhosocial-activerecord
└── crud
    ├── get      --model ... --pk ...
    ├── list     --model ... [--where ...] [--order-by ...] [--limit N] [--offset N]
    ├── create   --model ... --data JSON|@file|@-
    ├── update   --model ... --pk ... --data JSON|@file|@-
    └── delete   --model ... --pk ...
```

模型引用格式是 `module:Class`，不是 `module.Class`：

```bash
rhosocial-activerecord crud list --model app.models:User
```

导入模型之前，CLI 会把当前目录和所有 `--path DIR` 加入 `sys.path`。模型类必须
是 `ActiveRecord` 或 `AsyncActiveRecord` 的子类。

## 后端与连接

核心包不维护后端清单，也不需要知道安装了哪些后端包，更不会给任何内置后端
特权。用户直接指定项目实际使用的类：

- 后端类：`--backend-class MODULE:CLASS`；省略时沿用模型模块自身的
  `configure()`。
- 连接配置：`--connection MODULE:CALLABLE`，或者
  `--config-class MODULE:CLASS` 配合 `--config KEY=VALUE`；省略时沿用模型
  模块自身的 `configure()`。

后端类和连接配置独立解析，因此命名连接可以提供凭据，而模型可以提供后端类。

类引用既接受 `module:Class`，也接受点号形式 `module.Class`。异步模型需要指定
异步后端类。

以随核心包提供的 SQLite 为例：

```bash
# SQLite 文件，同步模型
rhosocial-activerecord crud list \
  --model app.models:User \
  --backend-class rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend \
  --config-class rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig \
  --config database=app.db \
  --where "status=active" --order-by "created_at desc" --limit 20

# 命名连接 + 显式后端类
rhosocial-activerecord crud list \
  --model app.models:User \
  --backend-class rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend \
  --connection app.connections:prod_db \
  -o json
```

异步模型使用异步类，例如
`rhosocial.activerecord.backend.impl.sqlite.backend:AsyncSQLiteBackend`。

如果模型模块已经调用 `configure()`，可以同时省略 `--backend-class` 和
`--connection` / `--config-class`。此时 `--config` 会覆盖模型已有的配置。

`--config KEY=VALUE` 可重复使用。键名是配置类字段时按该字段类型转换；未知键或
`options.KEY=VALUE` 会写入 `config.options`。由于 CLI 不使用后端清单，缺少模块、
类或额外依赖时无法给出安装提示，只会报告失败的引用并以退出码 4 结束。密码不会
写入日志；生产环境建议使用命名连接或环境变量。

## CRUD 语义

| 命令 | 必需参数 | 行为 |
|------|----------|------|
| `get` | `--pk` | 按主键取一条记录；未找到退出码 3。 |
| `list` | — | 等值过滤、排序、limit/offset。默认 limit 为 100；`--limit 0` 表示不限。 |
| `create` | `--data` | 构造并保存记录，由 Pydantic 校验数据。 |
| `update` | `--pk`、`--data` | 载入记录，只应用给定字段后保存；数据中出现主键字段会报错。 |
| `delete` | `--pk` | 载入并删除记录；软删 mixin 仍按模型定义生效。 |

`update` 与 `delete` 只支持按主键操作，v1 不提供按过滤条件批量修改或删除。

`--data` 接受内联 JSON、`@file.json` 或 `@-`（标准输入），内容必须是 JSON 对象。

主键：

```bash
# 单列主键
--pk 42

# 复合主键
--pk '{"order_id": 1, "product_id": 101}'
```

`--where` 只支持等值过滤，可重复使用；多个条件按 AND 组合。
`--order-by` 接受 `field` 或 `field asc|desc`，也可重复。

## 输出格式

`-o table|json|csv|tsv`：

| 格式 | `list` | `get` / `create` / `update` | `delete` |
|------|--------|------------------------------|----------|
| `json` | 数组 | 对象 | `{"deleted": N, "pk": ...}` |
| `csv` / `tsv` | 表头 + 多行 | 表头 + 一行 | 一行摘要 |
| `table` | Rich 表格 | Rich 纵向表 | Rich 面板 |

`--fields id,name` 限制输出字段；`--rich-ascii` 使用 ASCII 边框。

机器格式的 stdout 只包含数据，日志和错误都走 stderr，因此 `-o json` 可以直接
管道给 `jq`。

## 日志

框架默认日志级别为 `WARNING`；排查连接或模型问题时使用 `--log-level DEBUG`。
日志始终输出到 stderr。

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 模型、连接、校验或数据库错误 |
| 2 | 命令行用法错误（argparse） |
| 3 | 记录未找到 |
| 4 | 后端类或连接配置类无法导入 |

## 同步与异步模型

CLI 会自动识别模型类型。`ActiveRecord` 使用同步后端；`AsyncActiveRecord` 使用
异步后端，并在 CLI 内部运行事件循环。用户不需要额外传入 `--async`，但
`--backend-class` 必须与模型匹配：异步模型使用 `AsyncStorageBackend` 子类，
同步模型使用 `StorageBackend` 子类。

## Python 模块方式

未安装 console script 时也可以直接运行：

```bash
python -m rhosocial.activerecord.cli crud list --model app.models:User -o json
```
