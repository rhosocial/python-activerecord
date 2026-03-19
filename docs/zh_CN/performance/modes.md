# 架构决定性能

## 通过简洁实现性能

我们的框架通过架构简洁性而非复杂的优化机制来实现卓越性能：

- **直接架构**: 从表达式到 SQL 只需 2 步，避免了增加开销的多层编译
- **无隐藏缓存**: 与需要特殊查询缓存机制的系统不同，我们的方法天生高效
- **无状态表达式**: 查询构建期间没有对象状态管理开销
- **可预测性能**: 性能直接随表达式数量缩放，没有隐藏因素

## 两种查询模式

### 严格模式（默认）

返回经过 Pydantic 验证的模型实例：

```python
# 返回 User 实例列表，经过完整验证
users = User.query().all()

# 返回单个 User 实例
user = User.query().where(User.c.id == 1).one()
```

**适用场景**：需要模型方法、验证、关联加载的业务逻辑。

### 原始模式（高性能）

返回原始字典，绕过 Pydantic 验证：

```python
# 使用 aggregate() 获取原始字典列表
users = User.query().select(User.c.id, User.c.name).aggregate()
# 返回: [{'id': 1, 'name': 'Alice'}, ...]

# 使用 aggregate() + 聚合函数
from rhosocial.activerecord.backend.expression import sum_, avg
stats = User.query().aggregate(
    total=sum_(User.c.score),
    avg_score=avg(User.c.score)
)
# 返回: {'total': 1000, 'avg_score': 85.5}
```

**适用场景**：

- 只读列表展示
- 大数据导出
- 中间层数据处理
- 统计分析

### 性能对比

| 操作 | 严格模式 | 原始模式 | 提升 |
|------|---------|---------|------|
| 10,000 条查询 | ~500ms | ~50ms | 10x |
| 验证开销 | 有 | 无 | - |
| 关联加载 | 支持 | 不支持 | - |
| 类型适配 | 支持 | 不支持 | - |

> 💡 **AI提示词示例**: "aggregate() 和 all() 有什么区别？什么时候应该用哪个？"

## 重要注意事项

1. **类型适配器不生效**：`.aggregate()` 模式下，自定义类型适配器（`UseAdapter`）不会执行，你将直接获得数据库驱动返回的原始数据。

2. **关联加载不可用**：`.aggregate()` 不支持 `.with_()` 预加载，因为结果不是模型实例。

3. **CTEQuery 和 SetOperationQuery**：这两种查询类型只支持 `.aggregate()`，不支持 `.all()` 和 `.one()`。
