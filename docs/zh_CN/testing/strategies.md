# 测试策略 (Testing Strategies)

rhosocial-activerecord 建议根据被测组件的不同特性（ActiveRecord 模型 vs 查询对象）采取针对性的测试策略。

## 1. ActiveRecord 测试策略

针对 `ActiveRecord` 模型本身，主要关注元数据定义、字段表达式以及持久化操作。

### 测试范围
*   **元数据**: 验证 `table_name()` 和 `primary_key()` 返回值是否正确。
*   **字段代理 (FieldProxy)**: 验证 `User.c.field` 构造的表达式生成的 SQL 和参数元组是否符合预期。
*   **持久化 (Persistence)**: 验证 `save()` (INSERT/UPDATE) 和 `delete()` 操作的实际效果。

### 示例

```python
from rhosocial.activerecord.backend.impl.dummy import DummyBackend
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

def test_user_metadata():
    """测试表名和主键"""
    assert User.table_name() == "users"
    assert User.primary_key() == "id"

def test_field_expression_sql():
    """测试字段表达式生成的 SQL (使用 DummyBackend)"""
    # 配置 DummyBackend 以支持 SQL 生成
    User.configure(None, DummyBackend)
    
    # 利用 query 构建器来验证表达式
    # 比如验证 User.c.username == 'alice'
    query = User.query().where(User.c.username == 'alice')
    sql, params = query.to_sql()
    
    assert 'WHERE "users"."username" = ?' in sql
    assert params == ('alice',)

def test_user_persistence():
    """测试保存和删除 (使用 SQLite 内存数据库)"""
    # 配置 SQLite 内存库
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    
    # 需先建表 (通常在 fixture 中完成)
    with User.connection() as conn:
        conn.execute(f"CREATE TABLE {User.table_name()} (id INTEGER PRIMARY KEY, username TEXT)")
    
    # 测试 Save
    user = User(username="bob")
    user.save()
    assert user.id is not None
    
    # 测试 Delete
    user.delete()
    assert User.query().where(User.c.id == user.id).one() is None
```

## 2. ActiveQuery 与 CTEQuery 测试策略

针对查询构建器 (`ActiveQuery`, `CTEQuery`)，主要关注 SQL 构造逻辑和查询执行结果。

### 测试范围
*   **查询条件**: 验证 `.where()`, `.select()`, `.join()` 等方法链构造的 SQL 语句和参数元组。
*   **返回值**: 验证 `.one()`, `.all()`, `.aggregate()` 在真实数据环境下的返回结果。

### 示例

```python
def test_query_construction():
    """测试查询构造 (Zero-IO)"""
    User.configure(None, DummyBackend)
    
    # 复杂查询构造
    query = User.query() \
        .where(User.c.age > 18) \
        .order_by((User.c.created_at, "DESC")) \
        .limit(10)
        
    sql, params = query.to_sql()
    
    assert 'WHERE "users"."age" > ?' in sql
    assert 'ORDER BY "users"."created_at" DESC' in sql
    assert 'LIMIT ?' in sql
    assert 18 in params
    assert 10 in params

def test_query_execution_results():
    """测试查询返回值 (Integration)"""
    # 假设已配置 SQLite 内存库并预置数据
    # User(username="alice", age=20).save()
    # User(username="bob", age=15).save()
    
    # 测试 .all()
    adults = User.query().where(User.c.age >= 18).all()
    assert len(adults) == 1
    assert adults[0].username == "alice"
    
    # 测试 .aggregate() (CTEQuery 或普通查询)
    stats = User.query().select(User.c.age).aggregate()
    # 验证返回的是字典列表而非模型
    assert isinstance(stats[0], dict)
```
