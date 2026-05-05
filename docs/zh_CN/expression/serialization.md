# 表达式序列化

本文档介绍 SQL 表达式对象的序列化与反序列化机制，这是实现表达式缓存、分布式查询和任务调度的核心能力。

## 设计动机

为什么不直接序列化 `dialect`？原因如下：

1. **运行时注入**：dialect 与具体数据库后端紧耦合，序列化时应与表达式解耦
2. **多方言支持**：同一表达式可能在不同方言下生成不同 SQL，序列化时不应锁定方言
3. **安全隔离**：某些 dialect 实现依赖数据库连接状态，不适合跨进程传输

因此，序列化后的 `ExpressionSpec` 不包含 dialect 信息，反序列化时由调用方注入目标 dialect。

## 核心 API

### serialize()

将表达式对象序列化为字典格式：

```python
from rhosocial.activerecord.backend.expression.serialization import serialize

spec = serialize(expression)
# 返回 {"type": "Column", "module": "...", "params": {...}}
```

### deserialize()

从字典恢复表达式对象：

```python
from rhosocial.activerecord.backend.expression.serialization import deserialize

expr = deserialize(spec, dialect)
```

### ExpressionFactory

提供工厂方法创建表达式：

```python
from rhosocial.activerecord.backend.expression.serialization import ExpressionFactory

factory = ExpressionFactory(dialect)
expr = factory.create("Column", name="id", table="users")
```

## ExpressionSpec 格式

序列化后的字典包含三个必填字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | str | 表达式类名（如 `Column`、`ComparisonPredicate`） |
| `module` | str | 表达式类的完整模块路径 |
| `params` | dict | 构造参数，键名与 `__init__` 参数名一致 |

### 示例

```python
# Column("users", "id")
{
    "type": "Column",
    "module": "rhosocial.activerecord.backend.expression.core",
    "params": {"name": "id", "table": "users", "alias": null, "schema_name": null}
}
```

## 嵌套表达式

表达式参数中可能包含其他表达式对象（如 WHERE 子句中的谓词）。序列化时使用 `__expr__` 标记：

```python
# WHERE status = 'active' 的序列化结果
{
    "type": "WhereClause",
    "module": "rhosocial.activerecord.backend.expression.query_parts",
    "params": {
        "condition": {
            "__expr__": {
                "type": "ComparisonPredicate",
                "module": "rhosocial.activerecord.backend.expression.predicates",
                "params": {...}
            }
        }
    }
}
```

反序列化时，`__expr__` 标记的子字典会被自动还原为表达式对象。

## 元组标记

Python `tuple` 无法直接 JSON 序列化，使用 `__tuple__` 标记：

```python
# ORDER BY id DESC, name ASC
{
    "type": "OrderByClause",
    "params": {
        "order_by_items": [
            {"__tuple__": [Column(...), "DESC"]},
            {"__tuple__": [Column(...), "ASC"]}
        ]
    }
}
```

## 错误处理

反序列化时可能抛出以下异常：

- `ExpressionDeserializationError`：类型未注册、参数缺失、构造失败
- `TypeError`：参数类型不匹配（被包装为 `ExpressionDeserializationError`）

方言兼容性错误（如 PostgreSQL 特有语法在 MySQL 下不支持）会在 `to_sql()` 时才暴露。

## 使用场景

### 缓存查询计划

```python
# 序列化
query = query.select(...).where(...)
spec = serialize(query)

# 反序列化
restored = deserialize(spec, new_dialect)
sql = restored.to_sql()
```

### 分布式任务调度

将表达式作为任务参数传递，反序列化时注入目标环境的 dialect。

## 相关文档

- [扩展指南](./extending.md)：如何为自定义表达式实现序列化
- [格式参考](./format-reference.md)：ExpressionSpec 完整规范
- [迁移说明](./migration.md)：版本兼容性说明