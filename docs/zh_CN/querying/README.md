# 查询接口 (Querying Interface)

`rhosocial-activerecord` 提供了流畅、类型安全的查询 API。本章详细介绍了三种核心查询对象。

*   **[ActiveQuery (模型查询)](active_query.md)**
    *   最常用的查询对象，绑定到 ActiveRecord 模型，支持过滤、排序、连接、聚合和关联加载。
*   **[CTEQuery (公用表表达式)](cte_query.md)**
    *   用于构建复杂的递归或分析查询，结果以字典形式返回。
*   **[SetOperationQuery (集合操作)](set_operation_query.md)**
    *   处理 UNION、INTERSECT 和 EXCEPT 等集合运算。
