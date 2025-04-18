# 事务与隔离级别

事务是数据库管理系统中的基本概念，通过将一组操作组合成单个逻辑单元来确保数据完整性。rhosocial ActiveRecord提供全面的事务支持，具有各种隔离级别，以满足不同的应用需求。

## 目录

- [事务管理](transaction_management.md) - 学习如何管理数据库事务
- [隔离级别配置](isolation_level_configuration.md) - 配置事务隔离级别
- [嵌套事务](nested_transactions.md) - 在事务内部使用事务
- [保存点](savepoints.md) - 在事务中创建和管理保存点
- [事务中的错误处理](error_handling_in_transactions.md) - 处理事务中的错误和异常

## 概述

rhosocial ActiveRecord中的事务遵循ACID属性：

- **原子性（Atomicity）**：事务中的所有操作要么全部成功，要么全部失败
- **一致性（Consistency）**：事务将数据库从一个有效状态转变为另一个有效状态
- **隔离性（Isolation）**：并发事务不会相互干扰
- **持久性（Durability）**：一旦事务提交，其更改将永久保存

框架提供了通过方法调用进行显式事务管理和通过上下文管理器接口进行事务块管理的便捷方式。

```python
# 使用上下文管理器（推荐）
with User.transaction():
    user1.save()
    user2.save()
    # 两个用户要么都保存，要么都不保存

# 使用显式事务管理
User.backend().begin_transaction()
try:
    user1.save()
    user2.save()
    User.backend().commit_transaction()
except Exception:
    User.backend().rollback_transaction()
    raise
```

rhosocial ActiveRecord中的事务系统设计为数据库无关的，同时仍允许在需要时访问特定数据库的功能。