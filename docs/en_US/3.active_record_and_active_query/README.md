# ActiveRecord & ActiveQuery

This section covers the core components of the rhosocial ActiveRecord framework: ActiveRecord models and ActiveQuery functionality.

## Overview

The ActiveRecord pattern is an architectural pattern that maps database tables to classes and rows to objects. It encapsulates database access and adds domain logic to the data. rhosocial ActiveRecord implements this pattern with modern Python features, leveraging Pydantic for data validation and type safety.

ActiveQuery is the query builder component that provides a fluent interface for constructing database queries. It allows you to build complex queries in a readable and maintainable way, without writing raw SQL in most cases.

## Contents

- [Defining Models](3.1.defining_models/README.md) - Learn how to define your data models
  - Table Schema Definition
  - Field Validation Rules
  - Lifecycle Hooks
  - Inheritance and Polymorphism
  - Composition Patterns and Mixins

- [CRUD Operations](3.2.crud_operations/README.md)
  - [Create/Read/Update/Delete](3.2.crud_operations/create_read_update_delete.md)
  - [Batch Operations](3.2.crud_operations/batch_operations.md)
  - [Transaction Basics](3.2.crud_operations/transaction_basics.md)

- [Predefined Fields and Features](3.3.predefined_fields_and_features/README.md)
  - [Primary Key Configuration](3.3.predefined_fields_and_features/primary_key_configuration.md)
  - [Timestamp Fields (Created/Updated)](3.3.predefined_fields_and_features/timestamp_fields.md)
  - [Soft Delete Mechanism](3.3.predefined_fields_and_features/soft_delete_mechanism.md)
  - [Version Control and Optimistic Locking](3.3.predefined_fields_and_features/version_control_and_optimistic_locking.md)
  - [Pessimistic Locking Strategies](3.3.predefined_fields_and_features/pessimistic_locking_strategies.md)
  - [Custom Fields](3.3.predefined_fields_and_features/custom_fields.md)

- [Relationships](3.4.relationships/README.md)
  - [One-to-One Relationships](3.4.relationships/one_to_one_relationships.md)
  - [One-to-Many Relationships](3.4.relationships/one_to_many_relationships.md)
  - [Many-to-Many Relationships](3.4.relationships/many_to_many_relationships.md)
  - [Polymorphic Relationships](3.4.relationships/polymorphic_relationships.md)
  - [Self-referential Relationships](3.4.relationships/self_referential_relationships.md)
  - [Relationship Loading Strategies](3.4.relationships/relationship_loading_strategies.md)
  - [Eager Loading and Lazy Loading](3.4.relationships/eager_and_lazy_loading.md)
  - [Cross-database Relationships](3.4.relationships/cross_database_relationships.md)

- [Transactions & Isolation Levels](3.5.transactions_and_isolation_levels/README.md)
  - [Transaction Management](3.5.transactions_and_isolation_levels/transaction_management.md)
  - [Isolation Level Configuration](3.5.transactions_and_isolation_levels/isolation_level_configuration.md)
  - [Nested Transactions](3.5.transactions_and_isolation_levels/nested_transactions.md)
  - [Savepoints](3.5.transactions_and_isolation_levels/savepoints.md)
  - [Error Handling in Transactions](3.5.transactions_and_isolation_levels/error_handling_in_transactions.md)

- [Aggregate Queries](3.6.aggregate_queries/README.md)
  - [Count, Sum, Average, Min, Max](3.6.aggregate_queries/basic_aggregate_functions.md)
  - [Group By Operations](3.6.aggregate_queries/group_by_operations.md)
  - [Having Clauses](3.6.aggregate_queries/having_clauses.md)
  - [Complex Aggregations](3.6.aggregate_queries/complex_aggregations.md)
  - [Window Functions](3.6.aggregate_queries/window_functions.md)
  - [Statistical Queries](3.6.aggregate_queries/statistical_queries.md)
  - [JSON Operations](3.6.aggregate_queries/json_operations.md)
  - [Custom Expressions](3.6.aggregate_queries/custom_expressions.md)

- [Advanced Query Features](3.7.advanced_query_features/README.md)
  - [Custom ActiveQuery Classes](3.7.advanced_query_features/custom_activequery_classes.md)
  - [Query Scopes](3.7.advanced_query_features/query_scopes.md)
  - [Dynamic Query Building](3.7.advanced_query_features/dynamic_query_building.md)
  - [Raw SQL Integration](3.7.advanced_query_features/raw_sql_integration.md)
  - [Common Table Expressions](3.7.advanced_query_features/common_table_expressions.md)
  - [Async Access](3.7.advanced_query_features/async_access.md)

## Key Concepts

- **Models as Classes**: Each database table is represented by a model class that inherits from ActiveRecord
- **Records as Objects**: Each row in the database is represented by an instance of the model class
- **Validation**: Data validation is performed using Pydantic's validation system
- **Query Building**: Queries are built using method chaining on ActiveQuery objects
- **Relationships**: Models can define relationships with other models
- **Events**: Models support lifecycle events for custom behavior

This section will guide you through all aspects of working with ActiveRecord models and queries, from basic CRUD operations to advanced features like custom query scopes and relationship management.