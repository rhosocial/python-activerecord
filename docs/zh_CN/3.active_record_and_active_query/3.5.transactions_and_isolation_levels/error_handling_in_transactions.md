# 事务中的错误处理

在使用数据库事务时，正确的错误处理至关重要。rhosocial ActiveRecord提供了多种机制来处理事务处理过程中发生的错误，确保数据完整性的同时为开发者提供错误管理的灵活性。

## 事务错误类型

rhosocial ActiveRecord定义了几种与事务相关的错误类型：

- **TransactionError**：所有事务相关错误的基类
- **IsolationLevelError**：当尝试在活动事务期间更改隔离级别时引发

这些错误定义在`rhosocial.activerecord.backend.errors`模块中：

```python
from rhosocial.activerecord.backend.errors import TransactionError, IsolationLevelError
```

## 使用上下文管理器的自动错误处理

处理事务错误的推荐方式是使用上下文管理器接口，它会在发生异常时自动回滚事务：

```python
try:
    with User.transaction():
        user1.save()
        user2.save()
        if some_condition:
            raise ValueError("演示错误")
        user3.save()
        # 如果发生任何异常，事务会自动回滚
except ValueError as e:
    # 处理特定错误
    print(f"事务失败：{e}")
```

这种方法确保即使你忘记处理特定异常，事务也会被正确回滚。

## 手动错误处理

当使用显式事务方法时，你需要手动处理错误：

```python
# 开始事务
User.backend().begin_transaction()

try:
    # 执行操作
    user1.save()
    user2.save()
    
    # 提交事务
    User.backend().commit_transaction()
except Exception as e:
    # 在任何错误上回滚事务
    User.backend().rollback_transaction()
    print(f"事务失败：{e}")
    # 根据需要重新引发或处理异常
    raise
```

## 处理特定数据库错误

不同的数据库系统可能引发不同类型的错误。rhosocial ActiveRecord尝试规范化这些错误，但在某些情况下，你可能仍需要处理数据库特定的错误：

```python
from rhosocial.activerecord.backend.errors import (
    DatabaseError,
    ConstraintViolationError,
    DeadlockError,
    LockTimeoutError
)

try:
    with User.transaction():
        # 可能导致数据库错误的操作
        user.save()
except ConstraintViolationError as e:
    # 处理约束违反（例如，唯一约束）
    print(f"约束违反：{e}")
except DeadlockError as e:
    # 处理死锁情况
    print(f"检测到死锁：{e}")
    # 可能重试事务
except LockTimeoutError as e:
    # 处理锁超时
    print(f"锁超时：{e}")
except DatabaseError as e:
    # 处理其他数据库错误
    print(f"数据库错误：{e}")
except Exception as e:
    # 处理其他异常
    print(f"其他错误：{e}")
```

## 嵌套事务中的错误处理

在使用嵌套事务时，错误处理变得更加复杂。默认情况下，嵌套事务中的错误只会回滚该嵌套事务，而不会回滚外部事务：

```python
# 开始外部事务
with User.transaction():
    user1.save()  # 外部事务的一部分
    
    try:
        # 开始嵌套事务
        with User.transaction():
            user2.save()  # 嵌套事务的一部分
            raise ValueError("嵌套事务中的错误")
            # 嵌套事务自动回滚
    except ValueError as e:
        # 处理嵌套事务中的错误
        print(f"嵌套事务错误：{e}")
    
    # 外部事务继续
    user3.save()  # 外部事务的一部分
    # 外部事务提交：user1和user3被保存，user2没有被保存
```

如果你希望嵌套事务中的错误回滚整个事务，你需要重新引发异常：

```python
# 开始外部事务
with User.transaction():
    user1.save()  # 外部事务的一部分
    
    try:
        # 开始嵌套事务
        with User.transaction():
            user2.save()  # 嵌套事务的一部分
            raise ValueError("嵌套事务中的错误")
            # 嵌套事务自动回滚
    except ValueError as e:
        # 重新引发以回滚外部事务
        raise
    
    # 如果嵌套事务中发生错误，此代码不会执行
    user3.save()
```

## 使用保存点的错误处理

使用保存点时，你可以通过回滚到特定保存点来处理错误：

```python
# 获取事务管理器
tx_manager = User.backend().transaction_manager

# 开始事务
User.backend().begin_transaction()

try:
    # 执行初始操作
    user1.save()
    
    # 创建保存点
    savepoint_name = tx_manager.savepoint("before_risky_operation")
    
    try:
        # 执行风险操作
        user2.save()
        risky_operation()
    except Exception as e:
        # 错误时回滚到保存点
        tx_manager.rollback_to(savepoint_name)
        print(f"已回滚风险操作：{e}")
    
    # 继续事务
    user3.save()
    
    # 提交事务
    User.backend().commit_transaction()
except Exception as e:
    # 其他错误时回滚整个事务
    User.backend().rollback_transaction()
    print(f"事务失败：{e}")
    raise
```

## 记录事务错误

rhosocial ActiveRecord的事务管理器包含用于事务操作和错误的内置日志记录。你可以配置日志记录器以捕获更详细的信息：

```python
import logging

# 配置日志记录器
logger = logging.getLogger('transaction')
logger.setLevel(logging.DEBUG)

# 添加处理程序
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# 在事务管理器上设置日志记录器
User.backend().transaction_manager.logger = logger
```

使用此配置，所有事务操作和错误都将以详细信息记录。

## 事务错误的重试策略

某些事务错误，如死锁或锁超时，是临时的，可以通过重试事务来解决。以下是一个简单的重试策略：

```python
from rhosocial.activerecord.backend.errors import DeadlockError, LockTimeoutError
import time

def perform_with_retry(max_retries=3, retry_delay=0.5):
    retries = 0
    while True:
        try:
            with User.transaction():
                # 执行数据库操作
                user1.save()
                user2.save()
            # 成功，退出循环
            break
        except (DeadlockError, LockTimeoutError) as e:
            retries += 1
            if retries > max_retries:
                # 超过最大重试次数，重新引发异常
                raise
            # 等待后重试
            time.sleep(retry_delay * retries)  # 指数退避
            print(f"错误后重试事务：{e}（尝试 {retries}）")
```

## 最佳实践

1. **使用上下文管理器**：它们确保在错误时正确回滚
2. **捕获特定异常**：适当处理不同类型的错误
3. **考虑重试策略**：对于死锁等暂时性错误
4. **记录事务错误**：用于调试和监控
5. **小心使用嵌套事务**：了解错误如何传播
6. **对复杂操作使用保存点**：它们提供对错误恢复的更多控制
7. **测试错误场景**：确保你的错误处理按预期工作

## 下一步

- 了解[事务管理](transaction_management.md)
- 探索[隔离级别配置](isolation_level_configuration.md)
- 理解[嵌套事务](nested_transactions.md)
- 掌握[保存点](savepoints.md)