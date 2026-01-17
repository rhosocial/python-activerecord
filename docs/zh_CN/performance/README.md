# 6. 性能与优化 (Performance & Optimization)

"渐进式 ORM" 的核心在于：你可以根据需求在开发效率与运行效率之间自由切换。

## 目录

*   **[运行模式 (Strict vs Raw)](modes.md)**: 何时使用 `.aggregate()` 绕过 Pydantic 开销。
*   **[并发控制 (Concurrency)](concurrency.md)**: 使用乐观锁处理竞态条件。
*   **[缓存机制 (Caching)](caching.md)**: 理解内部缓存以避免重复工作。

## 示例代码

本章的完整示例代码位于 `docs/examples/chapter_06_performance/`。
