# ExpressionSpec 格式参考

本文档定义序列化格式的完整规范。

## ExpressionSpec 结构

表达式序列化的目标格式：

```python
{
    "type": str,           # 必填：类名
    "module": str,         # 必填：完整模块路径
    "params": dict         # 必填：构造参数
}
```

### 字段约束

| 字段 | 类型 | 约束 |
|------|------|------|
| `type` | str | 非空，有效 Python 标识符 |
| `module` | str | 可导入的模块路径，类必须可从该模块导入 |
| `params` | dict | 键名与目标类 `__init__` 参数名一致 |

## 标记类型

### __expr__ 标记（保留键）

嵌套表达式使用 `__expr__` 包装：

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

**语义**：反序列化时，`__expr__` 的值会被递归反序列化为表达式对象。

**重要**：`__expr__` 是框架保留键，用户自定义表达式的 `get_params()` 返回值中**不得使用此键**。

### __tuple__ 标记（保留键）

元组使用 `__tuple__` 标记：

```python
{
    "type": "OrderByClause",
    "params": {
        "order_by_items": [
            {"__tuple__": [Column(...), "DESC"]}
        ]
    }
}
```

**语义**：反序列化时，`__tuple__` 数组被还原为 Python tuple。

**重要**：`__tuple__` 是框架保留键，用户自定义表达式的 `get_params()` 返回值中**不得使用此键**。

## 标量类型规则

| Python 类型 | JSON 表示 | 备注 |
|-------------|-----------|------|
| `str` | string | |
| `int` | number | |
| `float` | number | |
| `bool` | boolean | |
| `None` | null | |
| `list` | array | 递归序列化元素 |
| `dict` | object | 递归序列化值 |
| `tuple` | object | 使用 `__tuple__` 标记 |
| `BaseExpression` | object | 使用 `__expr__` 标记 |
| `set` | - | 不支持，需转为 list |
| 其他自定义对象 | - | 需在 `get_params()` 中处理 |

## 序列化流程

1. 调用 `expression.get_params()` 获取参数字典
2. 递归处理 `params` 中的值：
   - `BaseExpression` → `{"__expr__": serialize(expr)}`
   - `tuple` → `{"__tuple__": [...]}`
   - `list` → 递归处理元素
   - `dict` → 递归处理值
   - 其他 → 直接传递
3. 添加 `type`（类名）和 `module`（模块路径）

## 反序列化流程

1. 验证 `type` 和 `module` 存在
2. 通过 `ExpressionRegistry.lookup()` 查找类
3. 调用 `_reconstruct(cls, dialect, params)` 重建实例
4. 递归处理 `params` 中的嵌套结构：
   - `__expr__` → `deserialize(value, dialect)`
   - `__tuple__` → tuple(递归处理元素)
   - 其他 → 递归处理

## 版本历史

| 版本 | 变更 |
|------|------|
| dev26 | 引入 `__expr__` 标记，替代三键启发式 |
| 早期 | 使用 `type/module/params` 三键检测嵌套表达式 |

## 相关文档

- [核心文档](./serialization.md)
- [扩展指南](./extending.md)
- [迁移说明](./migration.md)