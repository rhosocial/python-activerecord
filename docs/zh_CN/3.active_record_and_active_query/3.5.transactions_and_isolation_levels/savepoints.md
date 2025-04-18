# 保存点

保存点提供了一种在事务内设置中间标记的方法，允许部分回滚而不必中止整个事务。rhosocial ActiveRecord提供全面的保存点支持，使你能够对事务操作进行精细控制。

## 理解保存点

保存点是事务中的一个点，你可以回滚到该点而不必回滚整个事务。这对于复杂操作特别有用，在这些操作中，如果发生错误，你可能只想重试事务的一部分。

保存点也是rhosocial ActiveRecord中实现嵌套事务的底层机制。

## 基本保存点操作

rhosocial ActiveRecord提供了三种主要的保存点操作：

1. **创建保存点**：在事务中标记一个点，你可以稍后回滚到该点
2. **释放保存点**：移除保存点（但保留自保存点创建以来所做的所有更改）
3. **回滚到保存点**：撤销自保存点创建以来所做的所有更改

## 使用保存点

要使用保存点，你需要直接访问事务管理器：

```python
# 获取事务管理器
tx_manager = User.backend().transaction_manager

# 开始事务
User.backend().begin_transaction()

try:
    # 执行一些操作
    user1 = User(name="用户1")
    user1.save()
    
    # 创建保存点
    savepoint_name = tx_manager.savepoint("after_user1")
    
    # 执行更多操作
    user2 = User(name="用户2")
    user2.save()
    
    # user2出现问题
    if some_condition:
        # 回滚到保存点（仅撤销user2的更改）
        tx_manager.rollback_to(savepoint_name)
    else:
        # 释放保存点（保留所有更改）
        tx_manager.release(savepoint_name)
    
    # 继续事务
    user3 = User(name="用户3")
    user3.save()
    
    # 提交整个事务
    User.backend().commit_transaction()
except Exception:
    # 回滚整个事务
    User.backend().rollback_transaction()
    raise
```

## 自动保存点命名

如果你在创建保存点时不提供名称，rhosocial ActiveRecord将自动生成一个：

```python
# 创建具有自动生成名称的保存点
savepoint_name = tx_manager.savepoint()
print(f"创建的保存点：{savepoint_name}")
```

自动生成的名称遵循`SP_n`模式，其中`n`是一个递增计数器。

## 保存点和嵌套事务

rhosocial ActiveRecord中的嵌套事务是使用保存点实现的。当你开始一个嵌套事务时，会自动创建一个保存点：

```python
# 开始外部事务
User.backend().begin_transaction()

# 做一些工作
user1.save()

# 开始嵌套事务（内部创建一个保存点）
User.backend().begin_transaction()

# 做更多工作
user2.save()

# 提交嵌套事务（释放保存点）
User.backend().commit_transaction()

# 提交外部事务
User.backend().commit_transaction()
```

如果嵌套事务中发生错误，将其回滚会回滚到保存点，保留外部事务中完成的工作。

## 跟踪活动保存点

事务管理器跟踪所有活动的保存点。当你回滚到一个保存点时，在该保存点之后创建的所有保存点都会自动移除：

```python
# 开始事务
User.backend().begin_transaction()

# 创建第一个保存点
sp1 = tx_manager.savepoint("sp1")

# 做一些工作
user1.save()

# 创建第二个保存点
sp2 = tx_manager.savepoint("sp2")

# 做更多工作
user2.save()

# 创建第三个保存点
sp3 = tx_manager.savepoint("sp3")

# 做更多工作
user3.save()

# 回滚到第二个保存点
tx_manager.rollback_to(sp2)
# 这会撤销user3.save()并移除sp3
# 只有sp1和sp2保持活动状态

# 继续事务
user4.save()

# 提交事务
User.backend().commit_transaction()
```

## 数据库对保存点的支持

保存点支持因数据库而异：

- **PostgreSQL**：完全支持保存点，具有所有标准操作
- **MySQL/MariaDB**：完全支持保存点
- **SQLite**：基本支持保存点

rhosocial ActiveRecord事务管理器自动适应底层数据库的功能。

## 保存点的错误处理

使用保存点时，可能会发生几种错误：

- **无活动事务**：尝试在没有活动事务的情况下创建、释放或回滚到保存点
- **无效的保存点名称**：尝试释放或回滚到不存在的保存点
- **数据库特定错误**：底层数据库操作的问题

所有这些错误都包装在`TransactionError`异常中：

```python
from rhosocial.activerecord.backend.errors import TransactionError

try:
    # 尝试在没有活动事务的情况下创建保存点
    savepoint_name = tx_manager.savepoint()
except TransactionError as e:
    print(f"保存点错误：{e}")
```

## 最佳实践

1. **使用有意义的保存点名称**：使调试更容易
2. **不要过度使用保存点**：太多保存点会使事务逻辑复杂化
3. **清理保存点**：当不再需要保存点时释放它们
4. **正确处理错误**：捕获并处理`TransactionError`异常
5. **考虑使用嵌套事务**：对于常见模式，嵌套事务提供更清晰的接口

## 下一步

- 了解[事务中的错误处理](error_handling_in_transactions.md)
- 探索[嵌套事务](nested_transactions.md)
- 返回[事务管理](transaction_management.md)