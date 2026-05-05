# 迁移说明

本文档说明序列化格式的版本变更及迁移策略。

## dev26 变更：引入 `__expr__` 标记

### 变更内容

从 dev26 起，嵌套表达式使用 `__expr__` 显式标记，而非原来的三键启发式检测：

**旧格式（已废弃）**：
```python
{
    "type": "WhereClause",
    "params": {
        "condition": {
            "type": "ComparisonPredicate",
            "module": "...",
            "params": {...}
        }
    }
}
```

**新格式**：
```python
{
    "type": "WhereClause",
    "params": {
        "condition": {
            "__expr__": {
                "type": "ComparisonPredicate",
                "module": "...",
                "params": {...}
            }
        }
    }
}
```

### 影响范围

- **内存中的表达式对象**：无需迁移，序列化自动使用新格式
- **已持久化的 ExpressionSpec**（如缓存、日志、数据库字段）：需要迁移
- **传输中的 JSON 消息**：需要迁移（取决于接收方是否已升级）

### 迁移策略

#### 方案一：版本字段

在 ExpressionSpec 中添加 `spec_version` 字段：

```python
{
    "spec_version": "1.0",
    "type": "...",
    "module": "...",
    "params": {...}
}
```

反序列化时根据版本选择解析方式。

#### 方案二：自动转换

在反序列化入口处增加兼容逻辑：

```python
def deserialize(spec: dict, dialect):
    # 检测旧格式（有三键但无 __expr__）
    if "type" in spec.get("params", {}) and "module" in spec.get("params", {}):
        # 包装为新格式
        for key, value in spec["params"].items():
            if isinstance(value, dict) and "type" in value and "module" in value:
                spec["params"][key] = {"__expr__": value}
    return _deserialize_impl(spec, dialect)
```

#### 方案三：重新序列化

如果旧 ExpressionSpec 来源可控（如内部缓存），可在运行时自动重新序列化：

```python
# 检测到旧格式时
expr = legacy_deserialize(spec, dialect)
new_spec = serialize(expr)  # 自动转为新格式
```

## 推荐实践

1. **新项目**：直接使用 dev26+ 版本，无需关注迁移
2. **已有项目**：规划缓存清理或迁移脚本
3. **长期兼容**：建议在 ExpressionSpec 中预留 `spec_version` 字段

## 相关文档

- [核心文档](./serialization.md)
- [格式参考](./format-reference.md)