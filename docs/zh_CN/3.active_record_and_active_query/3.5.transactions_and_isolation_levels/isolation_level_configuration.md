# 隔离级别配置

事务隔离级别决定了事务之间如何相互交互，特别是当多个事务并发运行时。rhosocial ActiveRecord支持标准SQL隔离级别，并提供了灵活的配置方式。

## 理解隔离级别

隔离级别控制一个事务必须与其他事务所做的资源或数据修改隔离的程度。更高的隔离级别增加了数据一致性，但可能降低并发性和性能。

rhosocial ActiveRecord通过`IsolationLevel`枚举支持以下标准隔离级别：

| 隔离级别 | 描述 | 防止 |
|----------------|-------------|----------|
| `READ_UNCOMMITTED` | 最低隔离级别 | 无 |
| `READ_COMMITTED` | 防止脏读 | 脏读 |
| `REPEATABLE_READ` | 防止不可重复读 | 脏读、不可重复读 |
| `SERIALIZABLE` | 最高隔离级别 | 脏读、不可重复读、幻读 |

### 并发现象

- **脏读**：一个事务读取了另一个并发未提交事务写入的数据。
- **不可重复读**：一个事务重新读取之前读取过的数据，发现该数据已被另一个事务修改。
- **幻读**：一个事务重新执行返回满足搜索条件的行集的查询，发现由于另一个事务的操作，行集已经发生变化。

## 设置隔离级别

你可以通过几种方式设置事务的隔离级别：

### 为后端设置默认隔离级别

```python
from rhosocial.activerecord.backend import IsolationLevel

# 获取后端实例
backend = User.backend()

# 为未来的事务设置隔离级别
backend.transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE
```

### 为特定事务设置隔离级别

某些数据库后端允许在事务开始时设置隔离级别：

```python
# 对于PostgreSQL
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLTransactionManager

# 获取事务管理器
tx_manager = User.backend().transaction_manager

# 在开始事务前设置隔离级别
tx_manager.isolation_level = IsolationLevel.REPEATABLE_READ

# 以此隔离级别开始事务
with User.transaction():
    # 操作以REPEATABLE_READ隔离级别运行
    user = User.find(1)
    user.name = "新名称"
    user.save()
```

## 数据库特定的隔离级别支持

不同的数据库系统有不同的默认隔离级别，并且可能以不同方式实现隔离级别：

### MySQL/MariaDB

- 默认：`REPEATABLE_READ`
- 支持所有标准隔离级别
- 实现使用锁定和多版本并发控制(MVCC)的组合

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLTransactionManager
from rhosocial.activerecord.backend import IsolationLevel

# MySQL特定的事务管理器
tx_manager = User.backend().transaction_manager
assert isinstance(tx_manager, MySQLTransactionManager)

# 设置隔离级别
tx_manager.isolation_level = IsolationLevel.READ_COMMITTED
```

### PostgreSQL

- 默认：`READ_COMMITTED`
- 支持所有标准隔离级别
- 实现使用MVCC
- 独特功能：`SERIALIZABLE`事务可以是`DEFERRABLE`的

```python
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLTransactionManager
from rhosocial.activerecord.backend import IsolationLevel

# PostgreSQL特定的事务管理器
tx_manager = User.backend().transaction_manager
assert isinstance(tx_manager, PostgreSQLTransactionManager)

# 设置隔离级别
tx_manager.isolation_level = IsolationLevel.SERIALIZABLE
```

### SQLite

- 默认行为类似于`SERIALIZABLE`
- 对配置不同隔离级别的支持有限

## 更改隔离级别

重要提示：你不能更改活动事务的隔离级别。尝试这样做将引发`IsolationLevelError`：

```python
from rhosocial.activerecord.backend import IsolationLevel
from rhosocial.activerecord.backend.errors import IsolationLevelError

tx_manager = User.backend().transaction_manager

# 开始事务
User.backend().begin_transaction()

try:
    # 这将引发IsolationLevelError
    tx_manager.isolation_level = IsolationLevel.SERIALIZABLE
except IsolationLevelError as e:
    print("不能在活动事务期间更改隔离级别")
finally:
    User.backend().rollback_transaction()
```

## 检查当前隔离级别

你可以使用`isolation_level`属性检查当前隔离级别：

```python
from rhosocial.activerecord.backend import IsolationLevel

tx_manager = User.backend().transaction_manager
current_level = tx_manager.isolation_level

if current_level == IsolationLevel.SERIALIZABLE:
    print("使用最高隔离级别")
```

某些数据库后端还提供了从数据库服务器获取实际隔离级别的方法：

```python
# 对于PostgreSQL
from rhosocial.activerecord.backend.impl.pgsql import PostgreSQLTransactionManager

tx_manager = User.backend().transaction_manager
assert isinstance(tx_manager, PostgreSQLTransactionManager)

# 从服务器获取当前隔离级别
current_level = tx_manager.get_current_isolation_level()
```

## 最佳实践

1. **选择正确的隔离级别**：更高的隔离级别提供更强的保证，但可能降低性能
2. **在开始事务前设置隔离级别**：一旦事务开始，就不能更改
3. **了解数据库特定行为**：不同的数据库以不同方式实现隔离级别
4. **考虑应用需求**：在数据一致性和性能之间取得平衡
5. **使用真实工作负载进行测试**：隔离级别的选择可能显著影响应用性能

## 下一步

- 了解[嵌套事务](nested_transactions.md)
- 探索[保存点](savepoints.md)
- 理解[事务中的错误处理](error_handling_in_transactions.md)