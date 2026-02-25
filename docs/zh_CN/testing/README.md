# 第十章：测试 (Testing)

rhosocial-activerecord 提倡 "Zero-IO" 测试理念。通过内置的 `DummyBackend`，你可以在不依赖真实数据库环境的情况下，快速验证模型逻辑和 SQL 生成。

## 目录

*   [使用 DummyBackend 进行 SQL 检查 (Inspecting SQL with DummyBackend)](dummy.md): 学习如何使用虚拟后端验证 SQL 生成逻辑。

## 测试策略建议

1.  **单元测试**: 使用 `DummyBackend` 测试业务逻辑和查询构建。
2.  **集成测试**: 使用 `SQLiteBackend` (内存模式) 测试实际的数据库交互。
3.  **端到端测试**: 在真实数据库环境（如 PostgreSQL）中进行全面测试。

## 后端提供者职责

实现使用 testsuite 的后端时，提供者必须处理：

1. **环境准备**：
   - 创建数据库 schema
   - 建立连接
   - 配置测试模型

2. **环境清理**（关键顺序）：
   ```
   正确：DROP TABLE → 关闭游标 → 断开连接
   错误：断开连接 → DROP TABLE (连接已关闭！)
   ```

3. **常见问题**：
   - 表冲突（未删除表）
   - 数据污染（未清理）
   - 连接泄漏（未正确断开）
   - 后端特定问题（如 MySQL 异步 WeakSet 迭代）

详细提供者实现指南请参阅 `python-activerecord-testsuite/docs/zh_CN/README.md`。
