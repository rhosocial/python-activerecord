# 事务基础

本文档涵盖了rhosocial ActiveRecord中数据库事务的基础知识。事务确保一系列数据库操作以原子方式执行，这意味着它们要么全部成功，要么全部失败。

## 理解事务

事务对于维护应用程序中的数据完整性至关重要。它们提供以下保证（通常称为ACID属性）：

- **原子性（Atomicity）**：事务中的所有操作被视为单个单元。要么全部成功，要么全部失败。
- **一致性（Consistency）**：事务将数据库从一个有效状态转换到另一个有效状态。
- **隔离性（Isolation）**：事务彼此隔离，直到它们完成。
- **持久性（Durability）**：一旦事务提交，其效果是永久的。

## 基本事务用法

### 使用事务上下文管理器

使用事务的最简单方法是使用`Transaction`上下文管理器：

```python
from rhosocial.activerecord.backend.transaction import Transaction

# 使用上下文管理器的事务
with Transaction():
    user = User(username="johndoe", email="john@example.com")
    user.save()
    
    profile = Profile(user_id=user.id, bio="新用户")
    profile.save()
    
    # 如果任何操作失败，所有更改将被回滚
    # 如果所有操作成功，更改将被提交
```

### 手动事务控制

您也可以手动控制事务：

```python
from rhosocial.activerecord.backend.transaction import Transaction

# 手动事务控制
transaction = Transaction()
try:
    transaction.begin()
    
    user = User(username="janedoe", email="jane@example.com")
    user.save()
    
    profile = Profile(user_id=user.id, bio="另一个新用户")
    profile.save()
    
    transaction.commit()
except Exception as e:
    transaction.rollback()
    print(f"事务失败：{e}")
```

## 事务中的错误处理

当事务中发生错误时，所有更改会自动回滚：

```python
try:
    with Transaction():
        user = User(username="testuser", email="test@example.com")
        user.save()
        
        # 这将引发异常
        invalid_profile = Profile(user_id=user.id, bio="" * 1000)  # 太长
        invalid_profile.save()
        
        # 我们永远不会到达这一点
        print("事务成功")
except Exception as e:
    # 事务自动回滚
    print(f"事务失败：{e}")
    
    # 验证用户未被保存
    saved_user = User.find_one({"username": "testuser"})
    print(f"用户存在：{saved_user is not None}")  # 应该打印False
```

## 嵌套事务

rhosocial ActiveRecord支持嵌套事务。行为取决于数据库后端，但通常遵循嵌套事务创建保存点的模式：

```python
with Transaction() as outer_transaction:
    user = User(username="outer", email="outer@example.com")
    user.save()
    
    try:
        with Transaction() as inner_transaction:
            # 这创建了一个保存点
            invalid_user = User(username="inner", email="invalid-email")
            invalid_user.save()  # 这将失败
    except Exception as e:
        print(f"内部事务失败：{e}")
        # 只有内部事务回滚到保存点
    
    # 外部事务仍然可以继续
    another_user = User(username="another", email="another@example.com")
    another_user.save()
    
    # 当外部事务完成时，所有成功的更改都会被提交
```

## 事务隔离级别

您可以为事务指定隔离级别。可用的隔离级别取决于数据库后端：

```python
from rhosocial.activerecord.backend.transaction import Transaction, IsolationLevel

# 使用特定的隔离级别
with Transaction(isolation_level=IsolationLevel.SERIALIZABLE):
    # 使用最高隔离级别的操作
    user = User.find_one_for_update(1)  # 锁定行
    user.balance += 100
    user.save()
```

常见的隔离级别包括：

- `READ_UNCOMMITTED`：最低隔离级别，允许脏读
- `READ_COMMITTED`：防止脏读
- `REPEATABLE_READ`：防止脏读和不可重复读
- `SERIALIZABLE`：最高隔离级别，防止所有并发问题

## 事务和异常

您可以控制哪些异常触发回滚：

```python
class CustomException(Exception):
    pass

# 只有特定异常会触发回滚
with Transaction(rollback_exceptions=[CustomException, ValueError]):
    # 这将触发回滚
    raise ValueError("这会触发回滚")
    
# 所有异常都会触发回滚（默认行为）
with Transaction():
    # 任何异常都会触发回滚
    raise Exception("这也会触发回滚")
```

## 最佳实践

1. **保持事务简短**：长时间运行的事务可能导致性能问题和死锁。

2. **正确处理异常**：始终捕获异常并适当处理它们。

3. **使用适当的隔离级别**：更高的隔离级别提供更多一致性，但可能降低并发性。

4. **注意连接管理**：事务与数据库连接相关联。在多线程环境中，确保正确的连接处理。

5. **考虑对复杂操作使用保存点**：对于可能需要部分回滚的复杂操作。

```python
with Transaction() as transaction:
    # 创建保存点
    savepoint = transaction.savepoint("before_risky_operation")
    
    try:
        # 执行风险操作
        risky_operation()
    except Exception as e:
        # 回滚到保存点，而不是整个事务
        transaction.rollback_to_savepoint(savepoint)
        print(f"风险操作失败：{e}")
    
    # 继续事务
    safe_operation()
```

## 总结

事务是rhosocial ActiveRecord中的一个强大功能，有助于维护数据完整性。通过理解和正确使用事务，您可以确保您的数据库操作是可靠和一致的，即使在出现错误或并发访问的情况下也是如此。