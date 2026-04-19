# 命名查询

> **重要**: 这是**后端功能**，与 ActiveRecord 模式和 ActiveQuery 无关。

## 概述

命名查询是一种将可重用的查询定义为 Python 可调用对象的机制。它提供了 CLI 接口来执行查询，而无需直接编写 SQL 字符串。

## 关键概念

- **后端功能**: 此模块属于后端系统，不是 ActiveRecord ORM 的一部分
- **基于可调用对象**: 查询定义为函数或类，`dialect` 作为第一个参数
- **类型安全**: 返回实现 `Executable` 协议的 `BaseExpression` 对象
- **CLI 友好**: 提供命令行界面来执行查询

## 与 ActiveRecord 无关

命名查询**与以下内容无关**:

- ActiveRecord 模式
- ActiveQuery
- 基于模型的查询
- 关系查询

它专门用于:
- CLI 工具
- 基于脚本的查询执行
- Python 模块中的可重用查询组织

## 安装

命名查询包含在核心 `rhosocial-activerecord` 包中。无需额外安装。

如需异步支持，安装 `aiosqlite`:

```bash
pip install aiosqlite
```

## 快速开始

### 定义命名查询

命名查询是第一个参数为 `dialect` 的函数或类:

```python
# myapp/queries.py
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import Select


def active_users(dialect, limit: int = 100):
    """获取活跃用户，可选限制数量。

    参数:
        limit: 返回的最大用户数（默认: 100）

    返回:
        Select 表达式
    """
    return Select(
        targets=[Column("id"), Column("name"), Column("email")],
        from_=Literal("users"),
        where=Column("status").eq("active"),
        limit=limit,
    )
```

或作为类:

```python
# myapp/queries.py
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import Select


class UserQueries:
    """用户查询集合。"""

    def __call__(self, dialect, status: str = "active"):
        """按状态获取用户。

        参数:
            status: 要过滤的用户状态（默认: "active"）

        返回:
            Select 表达式
        """
        return Select(
            targets=[Column("id"), Column("name")],
            from_=Literal("users"),
            where=Column("status").eq(status),
        )
```

### 通过 CLI 执行

```bash
# 执行命名查询（同步）
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.active_users \
    --db-file mydb.sqlite

# 执行命名查询（异步）
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.active_users \
    --db-file mydb.sqlite \
    --async

# 列出模块中的所有查询
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries --list

# 显示查询详情
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries --example active_users

# 预览 SQL（不执行）
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.active_users \
    --db-file mydb.sqlite \
    --param limit=50 \
    --dry-run
```

### 通过代码执行

```python
from rhosocial.activerecord.backend.named_query import NamedQueryResolver

resolver = NamedQueryResolver("myapp.queries.active_users").load()
expression = resolver.execute(dialect, {"limit": 50})
sql, params = expression.to_sql()
print(f"SQL: {sql}, Params: {params}")
```

## CLI 选项

| 选项 | 描述 |
|--------|-------------|
| `qualified_name` | 完全限定的 Python 名称（module.path.callable） |
| `-e, --example` | 显示特定查询的详细信息 |
| `--param KEY=VALUE` | 查询参数（可重复） |
| `--describe` | 显示签名而不执行 |
| `--dry-run` | 打印 SQL 而不执行 |
| `--list` | 列出模块中的所有查询 |
| `--force` | 强制执行非 SELECT 语句（DML/DDL） |
| `--explain` | 执行 EXPLAIN 并显示计划 |
| `--async` | 使用异步执行（需要 aiosqlite） |

## 发现规则

可调用对象被认为是命名查询的条件：
1. 是函数、方法或类（带 `__call__`）
2. 第一个参数（在类的 `self` 之后）名为 `dialect`
3. 返回 `BaseExpression` 对象

没有 `dialect` 作为第一个参数的函数将被忽略。

## 安全性

命名查询是类型安全的：
- 只允许实现 `Executable` 的 `BaseExpression` 对象
- 不允许直接 SQL 字符串
- 这可以防止 SQL 注入漏洞

## API 参考

### 异常

- `NamedQueryError` - 基础异常
- `NamedQueryNotFoundError` - 找不到查询
- `NamedQueryModuleNotFoundError` - 找不到模块
- `NamedQueryInvalidReturnTypeError` - 无效的返回类型
- `NamedQueryInvalidParameterError` - 无效的参数
- `NamedQueryMissingParameterError` - 缺少必需参数
- `NamedQueryNotCallableError` - 不可调用
- `NamedQueryExplainNotAllowedError` - 不允许 EXPLAIN

### 函数

- `NamedQueryResolver` - 主解析器类
- `resolve_named_query()` - 一步解析和执行
- `list_named_queries_in_module()` - 列出模块中的查询
- `validate_expression()` - 验证表达式类型
- `create_named_query_parser()` - 创建 CLI 解析器
- `handle_named_query()` - 处理 CLI 执行
- `parse_params()` - 解析 CLI 参数

## 限制

- 这是**后端功能**，不是 ActiveRecord 的一部分
- 不能与 ActiveRecord 模型一起使用
- 不能与 ActiveQuery 一起使用
- 仅适用于 CLI 和脚本使用场景

## 异步支持

命名查询同时支持同步和异步执行：

- 使用 `--async` 标志启用异步执行
- 需要 `aiosqlite` 包
- 表达式构建始终是同步的（dialect 操作）
- 只有数据库连接和查询执行是异步的