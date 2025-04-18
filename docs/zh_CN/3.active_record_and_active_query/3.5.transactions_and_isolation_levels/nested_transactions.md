# 嵌套事务

嵌套事务允许你在已经运行的事务内部启动一个新的事务。rhosocial ActiveRecord通过保存点提供对嵌套事务的强大支持，使你能够对复杂的数据库操作进行更精细的控制。

## 理解嵌套事务

在rhosocial ActiveRecord中，当你在已经活动的事务内部开始一个事务时，框架会创建一个保存点，而不是启动一个新的物理事务。这种方法允许在更大的事务中进行部分回滚。

事务嵌套级别在内部进行跟踪，每个嵌套事务操作只影响当前嵌套级别：

```python
# 开始外部事务（级别1）
with User.transaction():
    user1.save()  # 外部事务的一部分
    
    # 开始嵌套事务（级别2）
    with User.transaction():
        user2.save()  # 嵌套事务的一部分
        
        # 如果这里发生异常，只有嵌套事务会回滚
        # user2的更改会回滚，但user1的更改保留
    
    # 继续外部事务
    user3.save()  # 外部事务的一部分
```

## 嵌套事务的工作原理

rhosocial ActiveRecord使用以下方法实现嵌套事务：

1. 第一次调用`begin_transaction()`开始一个真正的数据库事务
2. 后续的`begin_transaction()`调用创建保存点
3. 当嵌套事务提交时，其保存点被释放
4. 当嵌套事务回滚时，数据库回滚到其保存点
5. 只有当最外层事务提交时，整个事务才会提交到数据库

## 事务嵌套级别

事务管理器跟踪当前的嵌套级别：

```python
# 获取事务管理器
tx_manager = User.backend().transaction_manager

# 检查当前嵌套级别（如果没有活动事务，则为0）
level = tx_manager.transaction_level
print(f"当前事务级别：{level}")
```

每次调用`begin_transaction()`都会增加级别，每次调用`commit_transaction()`或`rollback_transaction()`都会减少级别。

## 嵌套事务示例

以下是嵌套事务的更详细示例：

```python
from rhosocial.activerecord.backend.errors import TransactionError

# 开始外部事务
User.backend().begin_transaction()

try:
    # 外部事务中的操作
    user1 = User(name="用户1")
    user1.save()
    
    try:
        # 开始嵌套事务
        User.backend().begin_transaction()
        
        # 嵌套事务中的操作
        user2 = User(name="用户2")
        user2.save()
        
        # 模拟错误
        if user2.name == "用户2":
            raise ValueError("演示错误")
            
        # 由于错误，这不会执行
        User.backend().commit_transaction()
    except Exception as e:
        # 只回滚嵌套事务
        User.backend().rollback_transaction()
        print(f"嵌套事务已回滚：{e}")
    
    # 继续外部事务
    user3 = User(name="用户3")
    user3.save()
    
    # 提交外部事务
    User.backend().commit_transaction()
    # 结果：user1和user3被保存，user2没有被保存
    
except Exception as e:
    # 如果外部事务失败，回滚整个事务
    User.backend().rollback_transaction()
    print(f"外部事务已回滚：{e}")
```

## 使用上下文管理器进行嵌套事务

使用嵌套事务的推荐方式是使用上下文管理器，它会自动处理嵌套：

```python
# 外部事务
with User.transaction():
    user1.save()
    
    # 嵌套事务
    try:
        with User.transaction():
            user2.save()
            raise ValueError("演示错误")
    except ValueError:
        # 嵌套事务自动回滚
        # 但外部事务继续
        pass
    
    user3.save()
    # 外部事务提交：user1和user3被保存，user2没有被保存
```

## 数据库对嵌套事务的支持

嵌套事务支持因数据库而异：

- **PostgreSQL**：通过保存点完全支持嵌套事务
- **MySQL/MariaDB**：通过保存点完全支持嵌套事务
- **SQLite**：通过保存点基本支持嵌套事务

## 限制和注意事项

1. **隔离级别影响**：最外层事务的隔离级别适用于所有嵌套事务
2. **错误处理**：嵌套事务中的错误不会自动传播到外部事务，除非未处理
3. **资源使用**：深度嵌套的事务可能消耗额外资源
4. **死锁潜力**：复杂的嵌套事务可能增加死锁潜力

## 最佳实践

1. **保持嵌套浅层**：避免深度嵌套事务
2. **使用上下文管理器**：它们确保即使发生异常也能正确清理
3. **适当处理异常**：决定错误是否应该传播到外部事务
4. **考虑直接使用保存点**：对于更复杂的场景，显式保存点提供更多控制
5. **彻底测试**：嵌套事务在不同数据库之间可能有微妙的行为差异

## 下一步

- 了解[保存点](savepoints.md)以获得更精细的控制
- 理解[事务中的错误处理](error_handling_in_transactions.md)
- 返回[事务管理](transaction_management.md)