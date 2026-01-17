# 使用 DummyBackend 进行测试 (Testing with DummyBackend)

rhosocial-activerecord 提供了一个特殊的 `DummyBackend`，允许你在不连接真实数据库的情况下进行模型和业务逻辑的测试。这被称为 "Zero-IO" 测试，速度极快且无需清理环境。

## 什么是 DummyBackend？

`DummyBackend` 是一个不执行任何 SQL 的存储后端。它会记录所有的 SQL 操作，并允许你预设查询返回值。

## 启用 DummyBackend

在测试开始时配置模型使用 `DummyBackend`。

```python
from rhosocial.activerecord.backend.impl.dummy import DummyBackend, DummyConnectionConfig

# 配置所有模型使用 DummyBackend
User.configure(DummyConnectionConfig(), DummyBackend)
```

## 预设返回值 (Mocking Responses)

你可以拦截特定的 SQL 模式并返回预设数据。

```python
backend = User.backend()

# 当查询 users 表时，返回特定的用户数据
backend.add_response(
    pattern="SELECT .* FROM users",
    data=[
        {"id": 1, "username": "test_user", "email": "test@example.com"}
    ]
)

# 现在执行查询，不会访问数据库，而是直接返回预设数据
user = User.find(1)
assert user.username == "test_user"
```

## 验证执行的 SQL

你可以检查后端执行了哪些 SQL 语句，以验证你的查询逻辑是否正确。

```python
# 执行一些操作
User.find(1)

# 获取最后执行的 SQL
last_sql = backend.last_sql
print(last_sql)
# SELECT "users"."id", "users"."username", ... FROM "users" WHERE "users"."id" = ? LIMIT ?

# 获取执行历史
history = backend.execution_history
assert len(history) == 1
```

## 优势

1.  **速度极快**: 没有任何网络或磁盘 IO。
2.  **无需 Fixtures**: 不需要准备数据库环境。
3.  **确定性**: 每次运行结果完全一致。
4.  **SQL 验证**: 可以精确验证生成的 SQL 是否符合预期。
