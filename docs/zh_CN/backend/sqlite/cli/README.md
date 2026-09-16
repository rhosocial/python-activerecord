# 命令行界面

## 概述

SQLite 后端包含用于数据库操作的命令行界面。CLI 提供了查询、检查和管理 SQLite 数据库的命令，无需编写 Python 代码。

CLI 命令分为两类：

1. **SQLite 特定命令** —— SQLite 独有的操作（query、introspect、info）
2. **核心继承命令** —— 所有后端共享（named-expression、named-procedure、named-migration、named-connection）

## 调用

安装包时，CLI 会注册为 `rhosocial-activerecord-sqlite`：

```bash
pip install rhosocial-activerecord
```

然后直接调用命令：

```bash
rhosocial-activerecord-sqlite <command> [options]
```

此命令在 `pyproject.toml` 中注册，等同于 `python -m rhosocial.activerecord.backend.impl.sqlite`。

## 输出格式

CLI 通过 `-o` / `--output` 选项支持多种输出格式：

| 格式 | 描述 | 需要 Rich |
|------|------|----------|
| `table` | 带边框的人类可读表格（默认） | 是 |
| `json` | JSON 对象数组 | 否 |
| `csv` | 逗号分隔值 | 否 |
| `tsv` | 制表符分隔值 | 否 |

安装 Rich 时，`table` 格式提供带彩色边框的美化输出。未安装 Rich 时，CLI 自动回退到 `json` 格式。

### Rich 集成

CLI 与 [Rich](https://github.com/Textualize/rich) 库集成，提供增强的终端输出：

- **彩色边框**：Unicode 制表字符用于表格边框
- **ASCII 回退**：使用 `--rich-ascii` 强制 ASCII 边框（`+`、`-`、`|`）
- **自动检测**：如果未安装 Rich，自动回退到 JSON 输出

```bash
# 默认表格输出（Unicode 边框）
rhosocial-activerecord-sqlite query "SELECT * FROM users;"

# ASCII 边框（用于不支持 Unicode 的终端）
rhosocial-activerecord-sqlite query --rich-ascii "SELECT * FROM users;"

# 强制 JSON 输出
rhosocial-activerecord-sqlite query -o json "SELECT * FROM users;"
```

### 输出示例

**表格格式（默认）：**
```
┌─────┬─────────┬───────┐
│ id  │ name    │ email │
├─────┼─────────┼───────┤
│ 1   │ Alice   │ a@x   │
│ 2   │ Bob     │ b@x   │
└─────┴─────────┴───────┘
```

**JSON 格式：**
```json
[
  {"id": 1, "name": "Alice", "email": "a@x"},
  {"id": 2, "name": "Bob", "email": "b@x"}
]
```

**CSV 格式：**
```csv
id,name,email
1,Alice,a@x
2,Bob,b@x
```

**TSV 格式：**
```tsv
id	name	email
1	Alice	a@x
2	Bob	b@x
```

## SQLite 特定命令

### info

无需数据库连接即可显示环境信息：

```bash
rhosocial-activerecord-sqlite info
```

输出包括：
- SQLite 版本号
- 扩展支持（FTS5、JSON1、R-Tree 等）
- Pragma 系统类别计数
- 协议实现状态

### query

直接执行 SQL 查询：

```bash
# 简单查询
rhosocial-activerecord-sqlite query "SELECT sqlite_version();"

# 从数据库文件查询
rhosocial-activerecord-sqlite query --db-file my.db "SELECT * FROM users;"

# 从文件执行 SQL
rhosocial-activerecord-sqlite query --file script.sql

# 执行多语句脚本
rhosocial-activerecord-sqlite query --executescript --file dump.sql

# JSON 输出
rhosocial-activerecord-sqlite query -o json "SELECT * FROM users;"
```

### introspect

检查数据库元数据：

```bash
# 列出所有表
rhosocial-activerecord-sqlite introspect tables --db-file my.db

# 列出所有视图
rhosocial-activerecord-sqlite introspect views --db-file my.db

# 获取数据库信息
rhosocial-activerecord-sqlite introspect database --db-file my.db

# 包括系统表
rhosocial-activerecord-sqlite introspect tables --db-file my.db --include-system

# 获取完整表信息（列、索引、外键）
rhosocial-activerecord-sqlite introspect table users --db-file my.db

# 查询特定详细信息
rhosocial-activerecord-sqlite introspect columns users --db-file my.db
rhosocial-activerecord-sqlite introspect indexes users --db-file my.db
rhosocial-activerecord-sqlite introspect foreign-keys posts --db-file my.db
```

#### 自省类型

| 类型 | 描述 | 需要表名 |
|------|------|---------|
| `tables` | 列出所有表 | 否 |
| `views` | 列出所有视图 | 否 |
| `database` | 数据库信息 | 否 |
| `table` | 完整表详情（列、索引、外键） | 是 |
| `columns` | 列信息 | 是 |
| `indexes` | 索引信息 | 是 |
| `foreign-keys` | 外键信息 | 是 |
| `triggers` | 触发器信息 | 可选 |

## 核心继承命令

这些命令**从核心 `python-activerecord` 库继承**，在所有后端中工作方式相同：

| 命令 | 源模块 | 描述 |
|------|--------|------|
| `named-expression` | `backend.named_expression` | 执行在 Python 中定义的类型安全参数化 SQL |
| `named-procedure` | `backend.named_expression.procedure` | 执行带事务支持的多查询编排 |
| `named-procedure-graph` | `backend.named_expression.procedure` | 执行过程图（DAG 工作流） |
| `named-migration` | `backend.migration` | 执行带依赖跟踪的版本化 schema 变更 |
| `named-connection` | `backend.named_connection` | 管理和测试命名连接配置 |

### 为什么使用命名功能？

命名功能让您可以**将复杂配置编码为单个名称**，避免冗长的命令行参数，并启用无法通过 CLI 标志表达的参数组合。

**命名连接** —— 封装所有连接参数：

```bash
# 不使用命名连接：长参数列表
rhosocial-activerecord-sqlite query \
    --db-file /path/to/production.db \
    --conn-param journal_mode=WAL \
    --conn-param synchronous=FULL \
    --conn-param foreign_keys=1 \
    "SELECT * FROM users"

# 使用命名连接：一个名称包含所有内容
rhosocial-activerecord-sqlite query \
    --named-connection myapp.connections.prod_db \
    "SELECT * FROM users"
```

**命名表达式** —— 封装复杂查询逻辑：

```bash
# 不使用命名表达式：难以 shell 转义的复杂 SQL
rhosocial-activerecord-sqlite query \
    "SELECT u.name, COUNT(o.id) as order_count FROM users u LEFT JOIN orders o ON u.id = o.user_id WHERE o.created_at >= '2026-01-01' GROUP BY u.id HAVING COUNT(o.id) > 5 ORDER BY order_count DESC LIMIT 20"

# 使用命名表达式：一个名称，类型安全参数
rhosocial-activerecord-sqlite named-expression \
    myapp.queries.high_value_customers \
    --param since=2026-01-01 --param min_orders=5
```

**命名过程** —— 封装多步骤工作流：

```bash
# 不使用命名过程：多个顺序命令
rhosocial-activerecord-sqlite query "BEGIN TRANSACTION; ..."
rhosocial-activerecord-sqlite query "UPDATE inventory ..."
rhosocial-activerecord-sqlite query "INSERT INTO orders ..."
rhosocial-activerecord-sqlite query "COMMIT;"

# 使用命名过程：一个命令，事务管理
rhosocial-activerecord-sqlite named-procedure \
    myapp.workflows.place_order \
    --param user_id=42 --param product_id=100 --param quantity=3
```

| 功能 | 好处 |
|------|------|
| 命名连接 | 在可版本化的 Python 代码中存储连接配置；跨脚本共享 |
| 命名表达式 | 封装复杂 SQL；类型安全参数；跨工具重用 |
| 命名过程 | 带事务管理的多查询工作流；并行执行 |
| 命名迁移 | 带依赖跟踪的版本化 schema 变更；上/下支持 |

### named-expression

执行命名表达式（在 Python 模块中定义的参数化 SQL）：

```bash
rhosocial-activerecord-sqlite named-expression \
    myapp.queries.orders_by_status \
    --db-file mydb.sqlite \
    --param status=pending
```

### named-procedure

执行命名过程：

```bash
rhosocial-activerecord-sqlite named-procedure \
    myapp.procedures.sync_users \
    --db-file mydb.sqlite
```

### named-migration

执行命名迁移：

```bash
# 运行迁移 up
rhosocial-activerecord-sqlite named-migration up add_users_table \
    --db-file mydb.sqlite

# 运行迁移 down
rhosocial-activerecord-sqlite named-migration down add_users_table \
    --db-file mydb.sqlite
```

### named-connection

管理和测试命名连接配置：

```bash
rhosocial-activerecord-sqlite named-connection my_connection \
    --params database=mydb.sqlite
```

## 连接参数

SQLite 使用基于文件的连接，因此连接参数与客户端-服务器数据库不同：

| 参数 | 描述 |
|------|------|
| `--db-file` | SQLite 数据库文件路径 |
| `--file` | 要执行的 SQL 文件 |
| `--named-connection` | 使用命名连接配置 |
| `--conn-param` | 附加连接参数 |
| `--async` | 使用异步后端 |
| `--log-level` | 设置日志级别（DEBUG、INFO、WARNING、ERROR） |

## 全局选项

| 选项 | 描述 |
|------|------|
| `-h`, `--help` | 显示帮助消息并退出 |
| `--log-level` | 设置日志级别（DEBUG、INFO、WARNING、ERROR） |

## 架构

CLI 遵循一致的架构：

```
backend/impl/sqlite/
├── __main__.py          # 入口点，构建解析器，分派到处理程序
└── cli/
    ├── __init__.py      # COMMAND_NAMES 列表，register_commands()
    ├── connection.py    # 连接参数解析和后端创建
    ├── output.py        # 输出格式提供者（Rich/JSON/CSV/TSV）
    │
    │   # SQLite 特定命令
    ├── info.py          # 'info' 命令处理程序
    ├── query.py         # 'query' 命令处理程序
    ├── introspect.py    # 'introspect' 命令处理程序
    │
    │   # 核心继承命令（薄适配器）
    ├── named_expression.py      # 委托到核心 named_expression.cli
    ├── named_procedure.py       # 委托到核心 named_expression.procedure.cli
    ├── named_migration.py       # 委托到核心 migration.cli
    └── named_connection.py      # 委托到核心 named_connection.cli
```

## 另请参阅

- [安装与配置](../installation_and_configuration/README.md) — 安装说明
- [Pragma 系统](../backend_specific_features/README.md) — PRAGMA 配置
- [核心命名功能](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US) — 命名连接、表达式、过程、迁移文档

💡 *AI 提示*："如何从命令行列出 SQLite 数据库中的所有表？"
