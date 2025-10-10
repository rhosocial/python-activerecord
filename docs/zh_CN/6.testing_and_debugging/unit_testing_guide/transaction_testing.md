# 数据库操作测试

事务测试当前在 rhosocial ActiveRecord 的测试框架中不可用。当前实现提供基本数据库操作测试功能。

## 当前数据库测试

测试当前专注于：

- 单个CRUD操作的成功/失败
- 基本数据库连接验证
- 简单查询执行检查

## 基本数据库操作测试

```python
import unittest
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    name: str
    email: str

class TestDatabaseOperations(unittest.TestCase):
    def test_create_operation(self):
        user = User(name="测试用户", email="test@example.com")
        result = user.save()
        self.assertTrue(result)  # 或检查user.id不为None
        
    def test_retrieve_operation(self):
        user = User.find(1)  # 假设存在id=1的用户
        self.assertIsNotNone(user)
        
    def test_update_operation(self):
        user = User.find(1)
        if user:
            original_name = user.name
            user.name = "更新名称"
            result = user.save()
            self.assertTrue(result)
    
    def test_delete_operation(self):
        user = User.find(1)
        if user:
            result = user.delete()
            self.assertTrue(result)
```

## 限制

- 无事务隔离测试
- 无多操作原子性验证
- 无回滚测试
- 无并发访问测试

这些高级数据库测试功能将在事务支持实现后添加。

## 设置事务测试

### 测试数据库配置

对于事务测试，使用完全支持事务的数据库非常重要：

```python
import pytest
from rhosocial.activerecord.backend import SQLiteBackend
from your_app.models import User, Account, Transfer

@pytest.fixture
def db_connection():
    """创建测试数据库连接。"""
    connection = SQLiteBackend(":memory:")
    # 创建必要的表
    User.create_table(connection)
    Account.create_table(connection)
    Transfer.create_table(connection)
    yield connection
```

### 事务测试的测试夹具

为事务测试创建具有初始数据的夹具：

```python
@pytest.fixture
def account_fixtures(db_connection):
    """为事务测试创建测试账户。"""
    # 创建用户
    user = User(username="transaction_test", email="transaction@example.com")
    user.save()
    
    # 创建具有初始余额的账户
    account1 = Account(user_id=user.id, name="账户1", balance=1000.00)
    account1.save()
    
    account2 = Account(user_id=user.id, name="账户2", balance=500.00)
    account2.save()
    
    return {
        "user": user,
        "accounts": [account1, account2]
    }
```

## 测试基本事务功能

测试事务正确提交或回滚更改：

```python
def test_basic_transaction_commit(db_connection, account_fixtures):
    """测试成功的事务提交。"""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # 初始余额
    initial_balance1 = account1.balance
    initial_balance2 = account2.balance
    
    # 在事务内执行转账
    with db_connection.transaction():
        # 从account1扣款
        account1.balance -= 200.00
        account1.save()
        
        # 向account2存款
        account2.balance += 200.00
        account2.save()
        
        # 创建转账记录
        transfer = Transfer(
            from_account_id=account1.id,
            to_account_id=account2.id,
            amount=200.00,
            status="已完成"
        )
        transfer.save()
    
    # 重新加载账户以验证更改已提交
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    # 验证事务后的余额
    assert updated_account1.balance == initial_balance1 - 200.00
    assert updated_account2.balance == initial_balance2 + 200.00
    
    # 验证转账记录存在
    transfer = Transfer.find_by(from_account_id=account1.id, to_account_id=account2.id)
    assert transfer is not None
    assert transfer.amount == 200.00
    assert transfer.status == "已完成"

def test_transaction_rollback(db_connection, account_fixtures):
    """测试错误时的事务回滚。"""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # 初始余额
    initial_balance1 = account1.balance
    initial_balance2 = account2.balance
    
    # 尝试一个会失败的转账
    try:
        with db_connection.transaction():
            # 从account1扣款
            account1.balance -= 200.00
            account1.save()
            
            # 向account2存款
            account2.balance += 200.00
            account2.save()
            
            # 模拟错误
            raise ValueError("事务期间的模拟错误")
            
            # 这段代码不应执行
            transfer = Transfer(
                from_account_id=account1.id,
                to_account_id=account2.id,
                amount=200.00,
                status="已完成"
            )
            transfer.save()
    except ValueError:
        # 预期的异常
        pass
    
    # 重新加载账户以验证更改已回滚
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    # 验证余额未变
    assert updated_account1.balance == initial_balance1
    assert updated_account2.balance == initial_balance2
    
    # 验证没有转账记录存在
    transfer = Transfer.find_by(from_account_id=account1.id, to_account_id=account2.id)
    assert transfer is None
```

## 测试事务隔离级别

测试不同的事务隔离级别以确保它们按预期行为：

```python
def test_transaction_isolation_read_committed(db_connection, account_fixtures):
    """测试READ COMMITTED隔离级别。"""
    # 如果数据库不支持隔离级别则跳过
    if not hasattr(db_connection, "set_isolation_level"):
        pytest.skip("数据库不支持隔离级别")
    
    accounts = account_fixtures["accounts"]
    account = accounts[0]
    
    # 以READ COMMITTED隔离级别开始事务
    with db_connection.transaction(isolation_level="READ COMMITTED"):
        # 读取初始余额
        initial_balance = account.balance
        
        # 模拟另一个连接更新余额
        another_connection = SQLiteBackend(":memory:")
        another_connection.execute(
            f"UPDATE accounts SET balance = balance + 100 WHERE id = {account.id}"
        )
        
        # 在READ COMMITTED中，当我们再次读取时应该看到更新后的值
        account.refresh()  # 从数据库重新加载
        updated_balance = account.balance
        
        # 验证我们可以看到已提交的更改
        assert updated_balance == initial_balance + 100

def test_transaction_isolation_repeatable_read(db_connection, account_fixtures):
    """测试REPEATABLE READ隔离级别。"""
    # 如果数据库不支持隔离级别则跳过
    if not hasattr(db_connection, "set_isolation_level"):
        pytest.skip("数据库不支持隔离级别")
    
    accounts = account_fixtures["accounts"]
    account = accounts[0]
    
    # 以REPEATABLE READ隔离级别开始事务
    with db_connection.transaction(isolation_level="REPEATABLE READ"):
        # 读取初始余额
        initial_balance = account.balance
        
        # 模拟另一个连接更新余额
        another_connection = SQLiteBackend(":memory:")
        another_connection.execute(
            f"UPDATE accounts SET balance = balance + 100 WHERE id = {account.id}"
        )
        
        # 在REPEATABLE READ中，我们应该仍然看到原始值
        account.refresh()  # 从数据库重新加载
        updated_balance = account.balance
        
        # 验证我们仍然看到原始值
        assert updated_balance == initial_balance
```

## 测试嵌套事务

测试嵌套事务正确工作：

```python
def test_nested_transactions(db_connection, account_fixtures):
    """测试嵌套事务行为。"""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # 初始余额
    initial_balance1 = account1.balance
    initial_balance2 = account2.balance
    
    # 外部事务
    with db_connection.transaction():
        # 更新account1
        account1.balance -= 100.00
        account1.save()
        
        # 成功的内部事务
        with db_connection.transaction():
            # 更新account2
            account2.balance += 50.00
            account2.save()
        
        # 失败的内部事务
        try:
            with db_connection.transaction():
                # 再次更新account2
                account2.balance += 50.00
                account2.save()
                
                # 模拟错误
                raise ValueError("内部事务中的模拟错误")
        except ValueError:
            # 预期的异常
            pass
    
    # 重新加载账户以验证更改
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    # 验证最终余额
    # account1: 初始值 - 100
    # account2: 初始值 + 50（来自成功的内部事务）
    assert updated_account1.balance == initial_balance1 - 100.00
    assert updated_account2.balance == initial_balance2 + 50.00
```

## 测试保存点

测试事务内部分回滚的保存点：

```python
def test_savepoints(db_connection, account_fixtures):
    """测试用于部分回滚的保存点。"""
    # 如果数据库不支持保存点则跳过
    if not hasattr(db_connection, "savepoint"):
        pytest.skip("数据库不支持保存点")
    
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # 初始余额
    initial_balance1 = account1.balance
    initial_balance2 = account2.balance
    
    # 开始事务
    with db_connection.transaction() as transaction:
        # 更新account1
        account1.balance -= 200.00
        account1.save()
        
        # 创建保存点
        savepoint = transaction.savepoint("transfer_savepoint")
        
        # 更新account2
        account2.balance += 200.00
        account2.save()
        
        # 模拟问题并回滚到保存点
        transaction.rollback_to_savepoint(savepoint)
        
        # 尝试使用不同的金额再次尝试
        account2.balance += 150.00
        account2.save()
    
    # 重新加载账户以验证更改
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    # 验证最终余额
    # account1: 初始值 - 200
    # account2: 初始值 + 150（保存点回滚后）
    assert updated_account1.balance == initial_balance1 - 200.00
    assert updated_account2.balance == initial_balance2 + 150.00
```

## 测试事务中的错误处理

测试应用程序如何处理事务中的各种错误场景：

```python
def test_transaction_error_handling(db_connection, account_fixtures):
    """测试事务中的错误处理。"""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # 测试处理数据库约束违反
    try:
        with db_connection.transaction():
            # 尝试使用无效值更新account1
            account1.balance = -1000.00  # 假设不允许负余额
            account1.save()
            
            # 如果约束得到执行，这不应该执行
            account2.balance += 1000.00
            account2.save()
    except Exception as e:
        # 验证异常类型符合我们的预期
        assert "constraint" in str(e).lower() or "check" in str(e).lower()
    
    # 重新加载账户以验证没有进行更改
    updated_account1 = Account.find_by_id(account1.id)
    updated_account2 = Account.find_by_id(account2.id)
    
    assert updated_account1.balance == account1.balance
    assert updated_account2.balance == account2.balance
    
    # 测试处理死锁（如果数据库支持）
    # 这更复杂，可能需要多个线程/进程
```

## 测试事务性能

测试事务的性能影响：

```python
import time

def test_transaction_performance(db_connection, account_fixtures):
    """测试事务性能。"""
    accounts = account_fixtures["accounts"]
    account1 = accounts[0]
    account2 = accounts[1]
    
    # 测量不使用事务的操作时间
    start_time = time.time()
    for i in range(100):
        account1.balance -= 1.00
        account1.save()
        account2.balance += 1.00
        account2.save()
    no_transaction_time = time.time() - start_time
    
    # 重置账户
    account1.balance = 1000.00
    account1.save()
    account2.balance = 500.00
    account2.save()
    
    # 测量在单个事务内操作的时间
    start_time = time.time()
    with db_connection.transaction():
        for i in range(100):
            account1.balance -= 1.00
            account1.save()
            account2.balance += 1.00
            account2.save()
    transaction_time = time.time() - start_time
    
    # 验证事务方法更高效
    # 对于内存SQLite，这可能并不总是正确的
    print(f"无事务时间: {no_transaction_time}")
    print(f"事务时间: {transaction_time}")
```

## 事务测试的最佳实践

1. **测试提交和回滚**：始终测试成功提交和由于错误导致的回滚。

2. **测试隔离级别**：如果您的应用程序使用特定的隔离级别，测试它们是否按预期行为。

3. **测试嵌套事务**：如果您的应用程序使用嵌套事务，彻底测试它们的行为。

4. **测试并发访问**：使用多个线程或进程测试事务如何处理并发访问。

5. **测试错误恢复**：确保您的应用程序能够从事务错误中优雅地恢复。

6. **测试性能**：测量事务对性能的影响，特别是对于批量操作。

7. **测试真实场景**：创建模拟应用程序中真实事务场景的测试。

8. **使用特定于数据库的测试**：某些事务功能是特定于数据库的，因此为您的特定数据库创建测试。

9. **测试事务边界**：确保在应用程序代码中正确定义事务边界。

10. **测试长时间运行的事务**：如果您的应用程序使用长时间运行的事务，测试它们对数据库资源的影响。