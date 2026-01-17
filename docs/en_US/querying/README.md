# Querying Interface

`rhosocial-activerecord` provides a fluent, type-safe query API. This chapter details the three core query objects.

*   **[ActiveQuery (Model Query)](active_query.md)**
    *   The most commonly used query object, bound to ActiveRecord models, supporting filtering, sorting, joining, aggregation, and eager loading.
*   **[CTEQuery (Common Table Expressions)](cte_query.md)**
    *   Used for building complex recursive or analytical queries, returning results as dictionaries.
*   **[SetOperationQuery (Set Operations)](set_operation_query.md)**
    *   Handles UNION, INTERSECT, and EXCEPT set operations.
