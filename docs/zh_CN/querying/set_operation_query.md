# SetOperationQuery (集合操作查询)

`SetOperationQuery` 是在 `ActiveQuery` 或 `CTEQuery` 上调用集合操作方法（如 `union`）后返回的对象。它代表了两个或多个查询结果的集合运算。

## 支持的操作

*   `union(other)`: 并集 (UNION)。会自动去重。
*   `intersect(other)`: 交集 (INTERSECT)。
*   `except_(other)`: 差集 (EXCEPT / MINUS)。

## 运算符重载

除了使用方法调用外，`SetOperationQuery` 还支持使用 Python 运算符进行集合操作，使代码更加简洁。

*   `|` (按位或) 对应 `union()`
*   `&` (按位与) 对应 `intersect()`
*   `-` (减法) 对应 `except_()`

**示例：**

```python
# 使用 | 运算符进行 UNION
union_query = q1 | q2

# 使用 & 运算符进行 INTERSECT
intersect_query = q1 & q2

# 使用 - 运算符进行 EXCEPT
except_query = q1 - q2
```

## 方法

### `aggregate() -> List[Dict[str, Any]]`

执行集合查询并返回所有结果（字典列表）。

> **为什么没有 `one()` 和 `all()` 方法？**
> 
> 与 `ActiveQuery` 不同，`SetOperationQuery` 不支持 `one()` 和 `all()` 方法。这是因为集合操作（UNION、INTERSECT、EXCEPT）的结果是原始数据字典，而不是模型实例。`one()` 和 `all()` 方法专门用于返回模型实例，而集合操作的结果无法保证能够映射回单一的模型类型，特别是在组合不同表的列时。

**同步异步对等**：`SetOperationQuery` 也有对应的异步版本 `AsyncSetOperationQuery`，两者具有相同的 API 和功能，唯一的区别是在异步版本中需要使用 `await` 关键字来调用 `aggregate()` 方法。

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

results = union_query.aggregate() # 返回字典列表
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
5.  **探索类成员**：如果您想了解 `SetOperationQuery` 类有哪些可用方法，可以使用 JetBrains PyCharm 或其他支持代码智能提示的 IDE。或者编写简单的脚本来检查类成员：
    ```python
    from rhosocial.activerecord.query.set_operation import SetOperationQuery
    methods = [method for method in dir(SetOperationQuery) if not method.startswith('_')]
    print("SetOperationQuery methods:", sorted(methods))
    ```
