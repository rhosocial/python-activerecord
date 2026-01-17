# SetOperationQuery (集合操作查询)

`SetOperationQuery` 是在 `ActiveQuery` 或 `CTEQuery` 上调用集合操作方法（如 `union`）后返回的对象。它代表了两个或多个查询结果的集合运算。

## 支持的操作

*   `union(other)`: 并集 (UNION)。会自动去重。
*   `intersect(other)`: 交集 (INTERSECT)。
*   `except_(other)`: 差集 (EXCEPT / MINUS)。

## 方法

### `all() -> List[Dict[str, Any]]`

执行集合查询并返回所有结果（字典列表）。

### `one() -> Optional[Dict[str, Any]]`

执行集合查询并返回第一条结果（字典）。

## 用法示例

### 合并两个查询结果 (UNION)

```python
# 查询活跃用户
q1 = User.query().where(User.c.is_active == True)

# 查询管理员用户
q2 = User.query().where(User.c.role == 'admin')

# 合并结果 (自动去重)
# SQL: SELECT * FROM users WHERE is_active = 1 UNION SELECT * FROM users WHERE role = 'admin'
union_query = q1.union(q2)

results = union_query.all() # 返回字典列表
```

## 重要限制与注意事项

1.  **返回类型**：`SetOperationQuery` 总是返回**字典列表**，即使源查询是基于 Model 的。这是因为集合操作可能组合不同表的列，无法保证结果能映射回单一 Model。

2.  **不可变性**：`SetOperationQuery` **不支持** `where`, `select`, `join`, `order_by`, `limit` 等查询构建方法。
    *   **错误做法**：`q1.union(q2).where(...)`
    *   **正确做法**：`q1.where(...).union(q2.where(...))`
    
    如果你需要对 UNION 后的结果进行过滤或排序，必须将其作为子查询或 CTE 的一部分。

3.  **列匹配**：参与集合运算的所有查询，其**列的数量**和**对应列的数据类型**必须一致。
    *   建议显式使用 `.select()` 指定列，以确保顺序和数量一致。
    
    ```python
    # 推荐做法
    q1 = User.query().select(User.c.name, User.c.email)
    q2 = Admin.query().select(Admin.c.name, Admin.c.email)
    q1.union(q2)
    ```

4.  **排序**：`SetOperationQuery` 本身不支持 `order_by`。如果需要对最终结果排序，通常需要将其包裹在另一个查询中。
