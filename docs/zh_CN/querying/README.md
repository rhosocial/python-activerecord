# 查询接口 (Querying Interface)

`rhosocial-activerecord` 提供了流畅、类型安全的查询 API。本章详细介绍了三种核心查询对象。

*   **[ActiveQuery (模型查询)](active_query.md)**
    *   最常用的查询对象，绑定到 ActiveRecord 模型，支持过滤、排序、连接、聚合和关联加载。
*   **[CTEQuery (公用表表达式)](cte_query.md)**
    *   用于构建复杂的递归或分析查询，结果以字典形式返回。
*   **[SetOperationQuery (集合操作)](set_operation_query.md)**
    *   处理 UNION、INTERSECT 和 EXCEPT 等集合运算。
*   **[查询速查表](cheatsheet.md)**
    *   常见查询模式速查：过滤、排序、分页和聚合。
*   **[复杂查询实战](recipes.md)**
    *   常见业务场景的查询解决方案：最近7天注册用户、Top 10客户、重复数据查找、分页实现等。

## 调试与检查 SQL

所有查询对象（`ActiveQuery`, `CTEQuery`, `SetOperationQuery`）都支持随时调用 `to_sql()` 方法。这对于调试非常有帮助，可以让你查看最终生成的 SQL 语句和参数元组，而无需实际执行查询。

```python
# 构造查询
query = User.query().where(User.c.age > 18).order_by((User.c.created_at, "DESC"))

# 查看 SQL 和参数
sql, params = query.to_sql()
print(f"SQL: {sql}")
# 输出: SQL: SELECT * FROM users WHERE age > ? ORDER BY created_at DESC
print(f"Params: {params}")
# 输出: Params: (18,)
```

> **注意**：`to_sql()` 生成的 SQL 语句格式取决于当前配置的数据库后端（Backend）。
> *   如果配置了特定的数据库（如 SQLite, PostgreSQL），生成的 SQL 将符合该数据库的方言（Dialect）。
> *   如果在未指定后端的情况下使用（通常用于测试或演示），默认可能会使用遵循 SQL 标准的 Dummy 后端，生成的 SQL 将是标准 SQL 格式。
