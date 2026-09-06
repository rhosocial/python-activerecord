# 测试

## 测试原则

SQLite 后端遵循项目范围的测试约定。这些原则确保所有后端具有一致、可维护的测试覆盖率。

### 同步/异步对等性

所有涉及 IO 操作的测试必须准备**配对的同步和异步测试**以覆盖等效场景：

```python
# 同步测试
def test_create_user():
    user = User(name="Alice").create()
    assert user.id is not None

# 异步测试——相同逻辑，异步 API
async def test_async_create_user():
    user = await AsyncUser(name="Alice").create()
    assert user.id is not None
```

如果后端仅支持同步或仅支持异步，则只需准备相应的测试。对于 SQLite，同步和异步都受支持，因此两者都应测试。

### 表达式测试——无 IO

表达式测试不涉及数据库 IO——它们只构建 SQL 并验证生成的 SQL：

```python
def test_expression_sql():
    expr = Eq(User.name, "Alice")
    assert expr.to_sql(dialect) == '"name" = ?'
    assert expr.params == ["Alice"]
```

表达式测试不需要异步对应测试，因为它们不执行 I/O。

### ActiveRecord 测试——使用 Testsuite

ActiveRecord 功能测试（模型 CRUD、关系、查询）使用 **testsuite**：

```bash
cd python-activerecord
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest \
    ../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/relation/
```

每个后端提供 **provider 实现**，将测试连接到其特定数据库。测试逻辑是共享的；只有 provider 层因后端而异。

### 测试类别总结

| 测试内容 | 方法 | 需要 IO？ | 需要异步？ |
|---------|------|----------|----------|
| 表达式类（方言 SQL 生成） | 单元测试，无数据库 | 否 | 否 |
| 类型适配器（类型转换） | 单元测试，无数据库 | 否 | 否 |
| 命名功能（表达式、过程、迁移） | CLI 脚本 | 是 | 如果支持 |
| ActiveRecord 功能（CRUD、关系、查询） | Testsuite + provider | 是 | 是 |
| SQLite 特定功能（pragma、扩展） | 项目特定测试 | 是 | 是 |

## 运行 SQLite 测试

### Provider 测试

```bash
cd python-activerecord
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest tests/rhosocial/activerecord_test/feature/basic/
```

### Testsuite 测试

```bash
cd python-activerecord
PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/pytest \
    ../python-activerecord-testsuite/src/rhosocial/activerecord/testsuite/feature/
```

### 表达式测试（无需数据库）

```bash
.venv3.14-ubuntu26.04/bin/pytest tests/ -k "expression"
```

## Provider 职责

SQLite 后端在测试中默认使用内存数据库。Provider 负责：

- 创建测试数据库（通常为 `:memory:`）
- 配置后端和方言
- 设置和清理测试数据
- 为 testsuite 提供模型类

实现细节请参阅 [核心 Testsuite Provider 指南](provider_guide.md)。

## 另请参阅

- [核心后端测试指南](backend_testing.md)
- [核心 Testsuite Provider 指南](provider_guide.md)
- [故障排除](../troubleshooting/README.md)

💡 *AI 提示*："如何为新的后端编写 provider 测试？"
