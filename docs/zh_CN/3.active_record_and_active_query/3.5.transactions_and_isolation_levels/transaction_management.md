# 事务管理

事务管理是数据库操作中确保数据完整性和一致性的关键方面。rhosocial ActiveRecord提供了一个强大的事务管理系统，可以跨不同的数据库后端工作。

## 基本事务操作

rhosocial ActiveRecord提供了几种使用事务的方式：

### 使用上下文管理器（推荐）

使用事务最方便和推荐的方式是通过上下文管理器接口：

```python
with User.transaction():
    user1.save()
    user2.save()
    # 所有操作要么全部成功，要么全部失败
```

上下文管理器自动处理事务的开始、提交和回滚。如果在事务块内发生任何异常，事务将自动回滚。

### 使用显式事务方法

为了获得更多控制，你可以使用显式事务方法：

```python
# 获取后端实例
backend = User.backend()

# 开始事务
backend.begin_transaction()

try:
    user1.save()
    user2.save()
    # 如果所有操作成功，提交事务
    backend.commit_transaction()
except Exception:
    # 如果任何操作失败，回滚事务
    backend.rollback_transaction()
    raise
```

## 事务状态

rhosocial ActiveRecord中的事务可以处于以下状态之一：

- **INACTIVE**：无活动事务
- **ACTIVE**：事务已开始但尚未提交或回滚
- **COMMITTED**：事务已成功提交
- **ROLLED_BACK**：事务已回滚

你可以使用`in_transaction`属性检查事务是否处于活动状态：

```python
if User.backend().in_transaction:
    # 我们当前在事务中
    pass
```

## 事务管理器

在后台，rhosocial ActiveRecord使用`TransactionManager`类来处理事务操作。每个数据库后端实现自己的事务管理器，处理该数据库系统的特定功能。

事务管理器负责：

- 开始、提交和回滚事务
- 管理事务隔离级别
- 通过保存点处理嵌套事务
- 提供上下文管理器接口

## 自动提交行为

当不在事务中时，rhosocial ActiveRecord遵循以下自动提交规则：

1. 默认情况下，单个操作会自动提交
2. 批量操作也会自动提交，除非包装在事务中

这种行为可以通过各种方法中的`auto_commit`参数来控制：

```python
# 为此操作禁用自动提交
User.backend().execute_sql("UPDATE users SET status = 'active'", auto_commit=False)
```

## 数据库特定考虑因素

虽然rhosocial ActiveRecord在所有支持的数据库中提供一致的事务API，但有一些数据库特定的考虑因素：

- **SQLite**：支持基本的事务功能，但对并发事务有限制
- **MySQL/MariaDB**：提供完整的事务支持，具有各种隔离级别
- **PostgreSQL**：提供最全面的事务支持，包括可延迟约束

## 最佳实践

1. **使用上下文管理器**：`with Model.transaction():`语法更清晰、更安全
2. **保持事务简短**：长时间运行的事务可能导致性能问题
3. **正确处理异常**：始终确保在错误时回滚事务
4. **了解隔离级别**：为你的用例选择适当的隔离级别
5. **考虑使用保存点**：对于复杂操作，保存点提供额外的控制

## 下一步

- 了解[隔离级别配置](isolation_level_configuration.md)
- 探索[嵌套事务](nested_transactions.md)
- 理解[保存点](savepoints.md)
- 掌握[事务中的错误处理](error_handling_in_transactions.md)