# 使用 DummyBackend 进行 SQL 检查 (Inspecting SQL with DummyBackend)

`DummyBackend` 是 rhosocial-activerecord 的默认后端，也是一个特殊的 "Zero-IO" 后端。它的主要目的是在不连接真实数据库的情况下，利用标准 SQL 方言（Dialect）来验证 SQL 生成逻辑。

## 核心特性 (Key Features)

1.  **默认后端**: 当你没有配置任何具体数据库后端（如 SQLite）时，系统默认使用 `DummyBackend`（或其异步版本 `AsyncDummyBackend`）。
2.  **仅包含方言**: 它只提供了 SQL 方言实现 (`DummyDialect`)，用于支持标准 SQL 的构造。
3.  **不支持执行**: 它**不具备**任何数据库执行能力。尝试执行查询（如 `find`, `save`, `all` 等）会直接抛出错误。
4.  **不支持 Mock**: 与某些测试框架不同，它**不支持**预设返回值（Mocking responses）。

## 主要用途：SQL 生成验证

`DummyBackend` 最适合用于单元测试中，验证你的查询构建逻辑是否生成了预期的 SQL 语句和参数元组。

### 示例

```python
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __table_name__ = "users"
    id: int
    username: str
    email: str

# 无需配置任何后端，默认即为 DummyBackend

def test_user_query_generation():
    # 1. 构建查询
    query = User.query().where(User.c.username == "alice")
    
    # 2. 获取生成的 SQL 和参数 (不会触发数据库连接)
    sql, params = query.to_sql()
    
    # 3. 验证
    print(f"SQL: {sql}")
    print(f"Params: {params}")
    
    assert 'SELECT "users".* FROM "users"' in sql
    assert 'WHERE "users"."username" = ?' in sql
    assert params == ("alice",)
```

## 注意事项

如果你尝试执行查询，将会收到错误：

```python
# 这将抛出错误，因为 DummyBackend 不支持实际操作
try:
    User.query().where(User.c.id == 1).one()
except Exception as e:
    print(e) 
    # 输出: DummyBackend does not support real database operations. Did you forget to configure a concrete backend?
```

## 总结

`DummyBackend` 是一个轻量级的工具，用于确保你的代码生成了正确的 SQL 结构。如果你需要进行集成测试或需要实际的数据交互，请使用 `SQLiteBackend`（支持内存模式 `:memory:`）或其他真实数据库后端。
