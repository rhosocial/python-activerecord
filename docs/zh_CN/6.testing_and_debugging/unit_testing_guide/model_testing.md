# 模型测试

rhosocial ActiveRecord 中的模型测试当前专注于基本模型功能和简单验证检查。

## 基本模型测试

当前测试功能包括：

- 测试模型属性分配和检索
- 通过Pydantic验证系统进行基本验证
- 简单CRUD操作验证

## 设置模型测试

测试模型的基本方法：

1. 使用测试数据创建模型实例
2. 验证属性值
3. 测试保存和删除操作
4. 验证基本验证规则

## 示例模型测试

```python
import unittest
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    name: str
    email: str

class TestUserModel(unittest.TestCase):
    def test_attribute_assignment(self):
        user = User(name="张三", email="zhangsan@example.com")
        self.assertEqual(user.name, "张三")
        self.assertEqual(user.email, "zhangsan@example.com")
    
    def test_model_persistence(self):
        user = User(name="李四", email="lisi@example.com")
        result = user.save()
        self.assertIsNotNone(user.id)  # 假设成功保存会分配ID
```

## 当前限制

当前模型测试方法仅限于基本功能。测试框架中暂不包含高级测试功能，如关系验证、复杂查询测试和事务验证。

## 设置测试环境

### 测试数据库配置

对于模型测试，使用专用的测试数据库非常重要：

```python
# 测试数据库配置示例
from rhosocial.activerecord.backend import SQLiteBackend

test_db = SQLiteBackend(":memory:")  # 使用内存SQLite进行测试
```

使用内存SQLite数据库进行测试有几个优势：
- 测试运行更快，没有磁盘I/O
- 每个测试都从干净的数据库状态开始
- 测试后无需清理

### 测试夹具（Fixtures）

夹具提供一致的测试数据集。rhosocial ActiveRecord与pytest夹具配合良好：

```python
import pytest
from rhosocial.activerecord.backend import SQLiteBackend
from your_app.models import User

@pytest.fixture
def db_connection():
    """创建测试数据库连接。"""
    connection = SQLiteBackend(":memory:")
    # 创建必要的表
    User.create_table(connection)
    yield connection
    # 内存数据库不需要清理

@pytest.fixture
def user_fixture(db_connection):
    """创建测试用户。"""
    user = User(
        username="test_user",
        email="test@example.com",
        age=30
    )
    user.save()
    return user
```

## 测试模型验证

验证规则确保数据完整性。测试有效和无效的场景：

```python
def test_user_validation(db_connection):
    """测试用户模型验证规则。"""
    # 测试有效用户
    valid_user = User(
        username="valid_user",
        email="valid@example.com",
        age=25
    )
    assert valid_user.validate() == True
    
    # 测试无效用户（缺少必填字段）
    invalid_user = User(
        username="",  # 空用户名
        email="invalid@example.com",
        age=25
    )
    assert invalid_user.validate() == False
    assert "username" in invalid_user.errors
    
    # 测试无效的电子邮件格式
    invalid_email_user = User(
        username="user2",
        email="not-an-email",  # 无效的电子邮件格式
        age=25
    )
    assert invalid_email_user.validate() == False
    assert "email" in invalid_email_user.errors
```

## 测试模型持久化

测试保存、更新和删除模型：

```python
def test_user_persistence(db_connection):
    """测试用户模型持久化操作。"""
    # 测试创建用户
    user = User(
        username="persistence_test",
        email="persist@example.com",
        age=35
    )
    assert user.is_new_record == True
    assert user.save() == True
    assert user.is_new_record == False
    assert user.id is not None
    
    # 测试更新用户
    user.username = "updated_username"
    assert user.save() == True
    
    # 通过重新加载验证更新
    reloaded_user = User.find_by_id(user.id)
    assert reloaded_user.username == "updated_username"
    
    # 测试删除用户
    assert user.delete() == True
    assert User.find_by_id(user.id) is None
```

## 测试模型查询

测试各种查询方法以确保它们返回预期结果：

```python
def test_user_queries(db_connection):
    """测试用户模型查询方法。"""
    # 创建测试数据
    User(username="user1", email="user1@example.com", age=20).save()
    User(username="user2", email="user2@example.com", age=30).save()
    User(username="user3", email="user3@example.com", age=40).save()
    
    # 测试find_by_id
    user = User.find_by_id(1)
    assert user is not None
    assert user.username == "user1"
    
    # 测试find_by
    user = User.find_by(username="user2")
    assert user is not None
    assert user.email == "user2@example.com"
    
    # 测试where子句
    users = User.where("age > ?", [25]).all()
    assert len(users) == 2
    assert users[0].username in ["user2", "user3"]
    assert users[1].username in ["user2", "user3"]
    
    # 测试排序
    users = User.order("age DESC").all()
    assert len(users) == 3
    assert users[0].username == "user3"
    assert users[2].username == "user1"
    
    # 测试限制和偏移
    users = User.order("age ASC").limit(1).offset(1).all()
    assert len(users) == 1
    assert users[0].username == "user2"
```

## 测试自定义模型方法

测试您添加到模型中的任何自定义方法：

```python
def test_custom_user_methods(db_connection, user_fixture):
    """测试自定义用户模型方法。"""
    # 假设User有一个自定义方法full_name
    user_fixture.first_name = "John"
    user_fixture.last_name = "Doe"
    assert user_fixture.full_name() == "John Doe"
    
    # 测试另一个自定义方法（例如，is_adult）
    assert user_fixture.is_adult() == True  # 从fixture中的年龄为30
```

## 测试模型事件

测试生命周期钩子和事件回调：

```python
def test_user_lifecycle_events(db_connection):
    """测试用户模型生命周期事件。"""
    # 创建带有回调计数器的用户
    user = User(username="event_test", email="event@example.com", age=25)
    user.before_save_called = 0
    user.after_save_called = 0
    
    # 覆盖生命周期方法进行测试
    original_before_save = User.before_save
    original_after_save = User.after_save
    
    def test_before_save(self):
        self.before_save_called += 1
        return original_before_save(self)
        
    def test_after_save(self):
        self.after_save_called += 1
        return original_after_save(self)
    
    # 为测试进行猴子补丁
    User.before_save = test_before_save
    User.after_save = test_after_save
    
    # 测试保存触发事件
    user.save()
    assert user.before_save_called == 1
    assert user.after_save_called == 1
    
    # 测试更新触发事件
    user.username = "updated_event_test"
    user.save()
    assert user.before_save_called == 2
    assert user.after_save_called == 2
    
    # 恢复原始方法
    User.before_save = original_before_save
    User.after_save = original_after_save
```

## 最佳实践

1. **隔离测试**：每个测试应该是独立的，不依赖于其他测试的状态。

2. **使用事务**：将测试包装在事务中以自动回滚更改：
   ```python
   def test_with_transaction(db_connection):
       with db_connection.transaction():
           # 测试代码在这里
           # 事务将自动回滚
   ```

3. **测试边缘情况**：测试边界条件、空值和其他边缘情况。

4. **模拟外部依赖**：使用模拟来隔离模型测试与外部服务。

5. **测试性能**：对于关键模型，包括性能测试以确保查询保持高效。

6. **使用描述性测试名称**：清晰地命名测试，描述它们测试的内容和预期行为。

7. **保持测试DRY**：使用夹具和辅助方法避免测试中的重复。

8. **测试失败情况**：通过测试失败场景确保您的代码优雅地处理错误。