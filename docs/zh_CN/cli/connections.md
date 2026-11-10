# 连接与模型引用

CLI 操作的是模型类。执行命令前必须导入类，并取得连接配置和后端类。

## 模型引用

模型引用是 `module:Class`，不是 `module.Class`：

```bash
rhosocial-activerecord dql list --model app.models:User
```

CLI 在导入模型前会把当前工作目录和每个 `--path DIR`（可重复）加入 `sys.path`。
类必须是 `ActiveRecord` 或 `AsyncActiveRecord` 子类，否则会被明确拒绝。

## 后端与连接

核心包不保存后端注册表，所以需要显式写出项目实际使用的类：

| 参数 | 含义 |
|------|------|
| `--backend-class MODULE:CLASS` | 后端类；异步模型必须传 `AsyncStorageBackend` 子类 |
| `--config-class MODULE:CLASS` | 连接配置类 |
| `--config KEY=VALUE` | 设置配置字段；可重复 |
| `--connection MODULE:CALLABLE` | 返回 `ConnectionConfig` 的命名连接可调用对象 |

两半各自独立解析：

- **后端类**：优先 `--backend-class`，否则用模型模块自己 `configure()` 的结果。
- **连接配置**：优先 `--connection`，或 `--config-class` 配合 `--config`，否则用模型模块自己
  `configure()` 的结果。

因此可以“命名连接提供凭据、模型模块提供后端类”，也可以反过来。

`--connection` 与 `--config-class` 互斥。`--config` 在三种路径下都会覆盖解析出的配置
（命名连接、配置类、模型配置）。未知键和 `options.KEY` 会写入 `config.options`。
值会按配置字段类型转换：布尔接受 `true`/`yes`/`1`/`on`，以及整数、浮点，其余按字符串。

```bash
# 模型模块不 configure()：两半都显式传入
rhosocial-activerecord dql list \
  --model app.models:User \
  --backend-class rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend \
  --config-class rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig \
  --config database=app.db -o json

# 命名连接 + 显式后端类
rhosocial-activerecord dql list \
  --model app.models:User \
  --backend-class mypkg.backend:MyBackend \
  --connection app.connections:prod_db -o json
```

如果模型模块自己调用了 `configure()`，可以省略 `--backend-class` 和
`--connection` / `--config-class`；此时 `--config` 覆盖模型已有配置。

## 异步模型

CLI 自动识别模型类型。`ActiveRecord` 用同步后端；`AsyncActiveRecord` 用异步后端，
并在 CLI 内部运行事件循环。没有 `--async` 参数，但 `--backend-class` 必须与模型匹配：
异步模型传 `AsyncStorageBackend` 子类，同步模型传 `StorageBackend` 子类。

## Python 模块形式

```bash
python -m rhosocial.activerecord.cli dql list --model app.models:User -o json
```

安装后的控制台脚本（`rhosocial-activerecord`）是同一个入口。后端专用命令
（例如 `rhosocial-activerecord-sqlite`）是另一个工具，执行 SQL 并做数据库内省，
不认识模型类。

## 让 AI 使用这些命令

- 不要猜后端类或配置类的路径。从项目配置读取，或询问用户；路径错误会以退出码 4
  报 `Cannot import ...`。
- 模型模块已调用 `configure()` 时，只传 `--model`，让模型提供连接。
- `--path` 可重复，是不安装源码树也能导入模型的正规方式。
- 模型类必须是真正的 `ActiveRecord` / `AsyncActiveRecord` 子类；模块级函数或普通
  Pydantic 模型会被拒绝。
- 控制台脚本不在 `PATH` 时用 `python -m rhosocial.activerecord.cli`。
