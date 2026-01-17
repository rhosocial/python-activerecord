# 5. 查询接口 (Querying Interface)

查询是与数据交互的核心。`rhosocial-activerecord` 提供了一套流畅的、类型安全的查询 API，同时支持强大的 SQL 特性。

在 TechBlog 中，我们需要实现：
*   查找 "alice" 的所有文章。
*   统计每个分类下的文章数。
*   找出评论最多的前 10 篇文章。

## 目录

*   **[基础过滤 (Filtering & Sorting)](filtering.md)**: `select`, `where`, `order_by`, `limit`。
*   **[聚合统计 (Aggregation)](aggregation.md)**: `count`, `sum`, `avg`, `group_by`。
*   **[高级查询 (Advanced Features)](advanced.md)**: Join 连接、CTE 公用表表达式、窗口函数。

## 示例代码

本章的完整示例代码位于 `docs/examples/chapter_05_querying/`。
