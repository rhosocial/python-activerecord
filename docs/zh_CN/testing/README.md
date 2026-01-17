# 第九章：测试 (Testing)

rhosocial-activerecord 提倡 "Zero-IO" 测试理念。通过内置的 `DummyBackend`，你可以在不依赖真实数据库环境的情况下，快速验证模型逻辑和 SQL 生成。

## 目录

*   [使用 DummyBackend (Using DummyBackend)](dummy.md): 学习如何使用虚拟后端进行高性能单元测试。

## 测试策略建议

1.  **单元测试**: 使用 `DummyBackend` 测试业务逻辑和查询构建。
2.  **集成测试**: 使用 `SQLiteBackend` (内存模式) 测试实际的数据库交互。
3.  **端到端测试**: 在真实数据库环境（如 PostgreSQL）中进行全面测试。
