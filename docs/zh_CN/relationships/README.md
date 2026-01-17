# 4. 关联关系 (Relationships)

关联关系是将孤立的数据表连接成有意义的信息网络的桥梁。本库采用显式的、类型安全的描述符来定义关系。

在 TechBlog 系统中，我们将构建以下关系网络：
*   **User** <-> **Profile** (1:1)
*   **User** <-> **Post** (1:N)
*   **Post** <-> **Comment** (1:N)
*   **Post** <-> **Tag** (N:N, 通过 PostTag 中间表)

## 目录

*   **[基础关系 (1:1, 1:N)](definitions.md)**: 定义 `HasOne`, `BelongsTo`, `HasMany`。
*   **[多对多关系 (Many-to-Many)](many_to_many.md)**: 通过中间模型实现复杂的 N:N 关系。
*   **[加载策略 (Loading Strategies)](loading.md)**: 解决 N+1 问题，掌握预加载与延迟加载。

## 示例代码

本章的完整示例代码位于 `docs/examples/chapter_04_relationships/`。
