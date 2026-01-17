# 5. Querying Interface

Querying is the core of interacting with data. `rhosocial-activerecord` provides a fluent, type-safe query API that also supports powerful SQL features.

In the TechBlog system, we will implement:

*   Find all posts by "alice".
*   Count the number of posts in each category.
*   Find the top 10 most commented posts.

## Table of Contents

*   **[Filtering & Sorting](filtering.md)**: `select`, `where`, `order_by`, `limit`.
*   **[Aggregation](aggregation.md)**: `count`, `sum`, `avg`, `group_by`.
*   **[Advanced Features](advanced.md)**: Joins, CTEs (Common Table Expressions), Window Functions.

## Example Code

Full example code for this chapter can be found at `docs/examples/chapter_05_querying/`.
