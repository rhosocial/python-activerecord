<!-- TRANSLATION PENDING -->

# 测试策略 (Strategies)

## 零 IO 测试 (Zero-IO Testing)

利用 `DummyBackend`，你可以在没有数据库的情况下测试你的模型逻辑和查询构建。

```python
from rhosocial.activerecord.backend.impl.dummy import DummyBackend

def test_user_query():
    # 切换到 Dummy 后端
    User.configure(None, DummyBackend)
    
    # 执行查询（实际只是记录了 SQL，不会报错）
    User.find_one({'name': 'alice'})
    
    # 验证生成的 SQL 是否符合预期
    last_op = User.backend().get_last_operation()
    assert "SELECT" in last_op.sql
    assert "alice" in last_op.params
```

## 集成测试

使用 SQLite 内存数据库 (`:memory:`) 进行快速的端到端测试。

```python
@pytest.fixture
def db():
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    # ... 建表 ...
    yield
    # ... 清理 ...
```
