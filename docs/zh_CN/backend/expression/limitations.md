# 表达式系统限制与注意事项

## 重要说明：表达式系统的职责范围

rhosocial-activerecord 的表达式系统是一个强大而灵活的工具，用于构建 SQL 查询。然而，重要的是要理解其职责范围和限制：

### 1. 表达式系统不进行语义验证

表达式系统忠实按照用户的意图构建 SQL，但**不会验证**生成的 SQL 是否符合 SQL 标准或能够在目标数据库中成功执行。

#### 示例：集合运算的类型一致性

根据 SQL 标准，在执行 UNION、INTERSECT 或 EXCEPT 等集合运算时，参与运算的所有查询必须具有相同数量的列，并且相应位置的列必须具有兼容的数据类型。

```python
# 以下代码在表达式系统中是有效的，但可能在数据库执行时失败
from rhosocial.activerecord.backend.expression import (
    Column, Literal, QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.query_sources import SetOperationExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

dialect = DummyDialect()

# 第一个查询返回整数 ID 和文本名称
query1 = QueryExpression(
    dialect,
    select=[Column(dialect, "id"), Column(dialect, "name")],
    from_=TableExpression(dialect, "users")
)

# 第二个查询返回文本 email 和整数年龄
query2 = QueryExpression(
    dialect,
    select=[Column(dialect, "email"), Column(dialect, "age")],
    from_=TableExpression(dialect, "customers")
)

# 表达式系统会成功构建此 UNION，但数据库执行时会报错
union_query = SetOperationExpression(
    dialect,
    left=query1,
    right=query2,
    operation="UNION"
)
```

尽管上述代码在表达式系统层面是有效的，但在数据库执行时会因为列类型不匹配而失败。

### 2. 数据库特定约束

表达式系统不会验证以下数据库特定的约束：
- 列类型兼容性
- 索引限制
- 触发器影响
- 外键约束
- 特定数据库的语法限制

### 3. 依赖数据库引擎验证

表达式系统的职责是：
- 正确构建 SQL 语句
- 处理参数绑定
- 适应不同数据库的语法差异

而**数据库引擎**负责：
- 验证 SQL 语义
- 执行类型检查
- 确保约束满足
- 处理执行计划优化

### 4. 最佳实践建议

1. **在生产环境中进行充分测试**：确保在目标数据库上测试所有复杂的查询
2. **理解 SQL 标准**：熟悉您正在使用的 SQL 操作的语义要求
3. **使用适当的错误处理**：捕获并处理可能的数据库执行错误
4. **利用数据库特性**：了解目标数据库的特定功能和限制

这种设计是有意为之的，因为它允许表达式系统保持通用性，同时让数据库引擎发挥其专业验证功能。

### 5. 显式优于隐式

我们的表达式系统遵循显式控制优于隐式行为的原则：
- 没有隐藏的状态管理或对象生命周期跟踪
- 没有自动查询编译或缓存机制
- 没有复杂的对象状态转换
- 用户对 SQL 生成有完全的可见性和控制权
- 与具有复杂多阶段编译的系统不同，我们的方法直接且可预测