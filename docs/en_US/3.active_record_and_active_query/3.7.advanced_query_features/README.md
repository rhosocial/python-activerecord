# Advanced Query Features

This chapter explores the advanced query capabilities of ActiveRecord, which allow you to build sophisticated database queries, customize query behavior, and optimize performance.

## Overview

ActiveRecord provides a powerful query builder interface through the `ActiveQuery` class. While basic queries are sufficient for many use cases, more complex applications often require advanced query features to handle specialized requirements.

The advanced features covered in this chapter include:

- [Custom ActiveQuery Classes](custom_activequery_classes.md) - Creating specialized query classes for specific models
- [Query Scopes](query_scopes.md) - Defining reusable query conditions and methods
- [Dynamic Query Building](dynamic_query_building.md) - Constructing queries programmatically at runtime
- [Raw SQL Integration](raw_sql_integration.md) - Incorporating custom SQL when needed
- [Common Table Expressions](common_table_expressions.md) - Using CTEs for complex and recursive queries
- [Async Access](async_access.md) - (❌ **NOT IMPLEMENTED**) Using asynchronous database operations

## When to Use Advanced Query Features

Advanced query features are particularly useful in the following scenarios:

1. **Complex Business Logic**: When your application has sophisticated data retrieval requirements that involve multiple conditions, joins, or aggregations

2. **Code Organization**: When you want to encapsulate query logic to improve code readability and maintainability

3. **Performance Optimization**: When you need fine-grained control over query execution to optimize database performance

4. **Specialized Requirements**: When you need to leverage database-specific features or execute complex SQL operations

5. **Asynchronous Operations**: When your application benefits from non-blocking database access

The following sections will guide you through each advanced query feature with detailed explanations and practical examples.