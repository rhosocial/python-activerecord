# rhosocial ActiveRecord Documentation Outline (English Version)

> **⚠️ Development Stage Notice:** This project is currently in the development stage. Features may be added or removed at any time, and there may be defects or inconsistencies with the actual implementation. Therefore, the documentation content may be adjusted at any time and is currently for reference only.
>
> **📝 Documentation Notation:** Throughout the documentation, you may see labels such as "Not Yet Implemented", "Partially Implemented", or "Subject to Change". These labels indicate that the related features are not fully implemented or may differ from the actual implementation. Please refer to the actual code for the most accurate information.

> **🔄 Implementation Status:** As of the latest review, the core ActiveRecord functionality is stable with basic CRUD operations, relationship management, and query building implemented. Advanced features like asynchronous operations, cross-database queries, and batch operations are in various stages of development. Please see individual documentation sections for specific implementation status.

## [1. Introduction](1.introduction/README.md)
- [Overview](1.introduction/introduction.md)
- [Features](1.introduction/features.md)
- [Requirements](1.introduction/README.md#requirements)
- [Philosophy](1.introduction/philosophy.md)
- [Pydantic Integration](1.introduction/pydantic-integration.md)
- [Asynchronous Support](1.introduction/async-support.md)
- [Relationships](1.introduction/relationships.md)
- [Aggregation](1.introduction/aggregation.md)
- [Performance](1.introduction/performance.md)
- [Learning Curve](1.introduction/learning-curve.md)
- [Community](1.introduction/community.md)
- [When to Choose](1.introduction/when-to-choose.md)
- [Code Comparison](1.introduction/code-comparison.md)
- [Conclusion](1.introduction/conclusion.md)

## [2. Quick Start (SQLite Example)](2.quick_start/README.md)
- [Installation](2.quick_start/installation.md)
- [Basic Configuration](2.quick_start/basic_configuration.md)
- [First Model Example](2.quick_start/first_model_example.md)
- [Frequently Asked Questions](2.quick_start/faq.md)

## [3. ActiveRecord & ActiveQuery](3.active_record_and_active_query/README.md)
### [3.1 Defining Models](3.active_record_and_active_query/3.1.defining_models/README.md)
- [Table Schema Definition](3.active_record_and_active_query/3.1.defining_models/table_schema_definition.md)
- [Field Validation Rules](3.active_record_and_active_query/3.1.defining_models/field_validation_rules.md)
- [Lifecycle Hooks](3.active_record_and_active_query/3.1.defining_models/lifecycle_hooks.md)
- [Inheritance and Polymorphism](3.active_record_and_active_query/3.1.defining_models/inheritance_and_polymorphism.md)
- [Composition Patterns and Mixins](3.active_record_and_active_query/3.1.defining_models/composition_patterns_and_mixins.md)

### [3.2 CRUD Operations](3.active_record_and_active_query/3.2.crud_operations/README.md)
- [Create/Read/Update/Delete](3.active_record_and_active_query/3.2.crud_operations/create_read_update_delete.md)
- [Batch Operations](3.active_record_and_active_query/3.2.crud_operations/batch_operations.md)
- [Transaction Basics](3.active_record_and_active_query/3.2.crud_operations/transaction_basics.md)

### [3.3 Predefined Fields and Features](3.active_record_and_active_query/3.3.predefined_fields_and_features/README.md)
- [Primary Key Configuration](3.active_record_and_active_query/3.3.predefined_fields_and_features/primary_key_configuration.md)
- [Timestamp Fields (Created/Updated)](3.active_record_and_active_query/3.3.predefined_fields_and_features/timestamp_fields.md)
- [Soft Delete Mechanism](3.active_record_and_active_query/3.3.predefined_fields_and_features/soft_delete_mechanism.md)
- [Version Control and Optimistic Locking](3.active_record_and_active_query/3.3.predefined_fields_and_features/version_control_and_optimistic_locking.md)
- [Pessimistic Locking Strategies](3.active_record_and_active_query/3.3.predefined_fields_and_features/pessimistic_locking_strategies.md)
- [Custom Fields](3.active_record_and_active_query/3.3.predefined_fields_and_features/custom_fields.md)

### [3.4 Relationships](3.active_record_and_active_query/3.4.relationships/README.md)
- [One-to-One Relationships](3.active_record_and_active_query/3.4.relationships/one_to_one_relationships.md)
- [One-to-Many Relationships](3.active_record_and_active_query/3.4.relationships/one_to_many_relationships.md)
- [Many-to-Many Relationships](3.active_record_and_active_query/3.4.relationships/many_to_many_relationships.md)
- [Polymorphic Relationships](3.active_record_and_active_query/3.4.relationships/polymorphic_relationships.md)
- [Self-referential Relationships](3.active_record_and_active_query/3.4.relationships/self_referential_relationships.md)
- [Relationship Loading Strategies](3.active_record_and_active_query/3.4.relationships/relationship_loading_strategies.md)
- [Eager Loading and Lazy Loading](3.active_record_and_active_query/3.4.relationships/eager_and_lazy_loading.md)
- [Cross-database Relationships](3.active_record_and_active_query/3.4.relationships/cross_database_relationships.md)

### [3.5 Transactions & Isolation Levels](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/README.md)
- [Transaction Management](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/transaction_management.md)
- [Isolation Level Configuration](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/isolation_level_configuration.md)
- [Nested Transactions](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/nested_transactions.md)
- [Savepoints](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/savepoints.md)
- [Error Handling in Transactions](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/error_handling_in_transactions.md)

### [3.6 Aggregate Queries](3.active_record_and_active_query/3.6.aggregate_queries/README.md)
- [Count, Sum, Average, Min, Max](3.active_record_and_active_query/3.6.aggregate_queries/basic_aggregate_functions.md)
- [Group By Operations](3.active_record_and_active_query/3.6.aggregate_queries/group_by_operations.md)
- [Having Clauses](3.active_record_and_active_query/3.6.aggregate_queries/having_clauses.md)
- [Complex Aggregations](3.active_record_and_active_query/3.6.aggregate_queries/complex_aggregations.md)
- [Window Functions](3.active_record_and_active_query/3.6.aggregate_queries/window_functions.md)
- [Statistical Queries](3.active_record_and_active_query/3.6.aggregate_queries/statistical_queries.md)
- [JSON Operations](3.active_record_and_active_query/3.6.aggregate_queries/json_operations.md)
  - JSON Extraction (EXTRACT)
  - JSON Text Extraction (EXTRACT_TEXT)
  - JSON Contains Check (CONTAINS)
  - JSON Path Existence Check (EXISTS)
  - JSON Type Retrieval (TYPE)
  - JSON Element Operations (REMOVE/INSERT/REPLACE/SET)
- [Custom Expressions](3.active_record_and_active_query/3.6.aggregate_queries/custom_expressions.md)
  - Arithmetic Expressions
  - Function Expressions
  - CASE Expressions
  - Conditional Expressions (COALESCE, NULLIF, etc.)
  - Subquery Expressions
  - Grouping Set Expressions (CUBE, ROLLUP, GROUPING SETS)

### [3.7 Advanced Query Features](3.active_record_and_active_query/3.7.advanced_query_features/README.md)
- [Custom ActiveQuery Classes](3.active_record_and_active_query/3.7.advanced_query_features/custom_activequery_classes.md)
- [Query Scopes](3.active_record_and_active_query/3.7.advanced_query_features/query_scopes.md)
- [Dynamic Query Building](3.active_record_and_active_query/3.7.advanced_query_features/dynamic_query_building.md)
- [Raw SQL Integration](3.active_record_and_active_query/3.7.advanced_query_features/raw_sql_integration.md)
- [Async Access](3.active_record_and_active_query/3.7.advanced_query_features/async_access.md)

## [4. Performance Optimization](4.performance_optimization/README.md)
- [Query Optimization Techniques](4.performance_optimization/query_optimization_techniques.md)
- [Caching Strategies](4.performance_optimization/caching_strategies.md)
  - [Model-level Caching](4.performance_optimization/caching_strategies/model_level_caching.md)
  - [Query Result Caching](4.performance_optimization/caching_strategies/query_result_caching.md)
  - [Relationship Caching](4.performance_optimization/caching_strategies/relationship_caching.md)
- [Large Dataset Handling](4.performance_optimization/large_dataset_handling.md)
- [Batch Operation Best Practices](4.performance_optimization/batch_operation_best_practices.md)
- [Performance Analysis and Monitoring](4.performance_optimization/performance_analysis_and_monitoring.md)

## [5. Backend Configuration](5.backend_configuration/README.md)
### 5.1 Supported Databases
- [MySQL](5.backend_configuration/5.1.supported_databases/mysql.md)
- [MariaDB](5.backend_configuration/5.1.supported_databases/mariadb.md)
- [PostgreSQL](5.backend_configuration/5.1.supported_databases/postgresql.md)
- [Oracle](5.backend_configuration/5.1.supported_databases/oracle.md)
- [SQL Server](5.backend_configuration/5.1.supported_databases/sql_server.md)
- [SQLite](5.backend_configuration/5.1.supported_databases/sqlite.md)

### 5.2 Cross-database Queries
- [Cross-database Connection Configuration](5.backend_configuration/5.2.cross_database_queries/connection_configuration.md)
- [Heterogeneous Data Source Integration](5.backend_configuration/5.2.cross_database_queries/heterogeneous_data_source_integration.md)
- [Data Synchronization Strategies](5.backend_configuration/5.2.cross_database_queries/data_synchronization_strategies.md)
- [Cross-database Transaction Handling](5.backend_configuration/5.2.cross_database_queries/cross_database_transaction_handling.md)

### 5.3 Database-specific Differences
- [Data Type Mapping](5.backend_configuration/5.3.database_specific_differences/data_type_mapping.md)
- [SQL Dialect Differences](5.backend_configuration/5.3.database_specific_differences/sql_dialect_differences.md)
- [Performance Considerations](5.backend_configuration/5.3.database_specific_differences/performance_considerations.md)

### 5.4 Custom Backends
- [Implementing Custom Database Backends](5.backend_configuration/5.4.custom_backends/implementing_custom_backends.md)
- [Extending Existing Backends](5.backend_configuration/5.4.custom_backends/extending_existing_backends.md)

## [6. Testing and Debugging](6.testing_and_debugging/README.md)
- [Unit Testing Guide](6.testing_and_debugging/unit_testing_guide/README.md)
  - [Model Testing](6.testing_and_debugging/unit_testing_guide/model_testing.md)
  - [Relationship Testing](6.testing_and_debugging/unit_testing_guide/relationship_testing.md)
  - [Transaction Testing](6.testing_and_debugging/unit_testing_guide/transaction_testing.md)
- [Debugging Techniques](6.testing_and_debugging/debugging_techniques.md)
- [Logging and Analysis](6.testing_and_debugging/logging_and_analysis.md)
- [Performance Profiling Tools](6.testing_and_debugging/performance_profiling_tools.md)

## [7. Version Migration and Upgrades](7.version_migration_and_upgrades/README.md)
- [Schema Change Management](7.version_migration_and_upgrades/schema_change_management.md)
- [Data Migration Strategies](7.version_migration_and_upgrades/data_migration_strategies.md)
- [Migrating from Other ORMs to ActiveRecord](7.version_migration_and_upgrades/migrating_from_other_orms.md)

## [8. Security Considerations](8.security_considerations/README.md)
- [SQL Injection Protection](8.security_considerations/sql_injection_protection.md)
- [Sensitive Data Handling](8.security_considerations/sensitive_data_handling.md)
- [Access Control and Permissions](8.security_considerations/access_control_and_permissions.md)

## [9. Application Scenarios](9.application_scenarios/README.md)
### 9.1 Web Application Development
- [Web API Backend Development](9.application_scenarios/9.1.web_application_development/web_api_backend_development.md)
- [Integration with Various Web Frameworks](9.application_scenarios/9.1.web_application_development/integration_with_web_frameworks.md)

### 9.2 Data Analysis Applications
- [Report Generation](9.application_scenarios/9.2.data_analysis_applications/report_generation.md)
- [Data Transformation Processing](9.application_scenarios/9.2.data_analysis_applications/data_transformation_processing.md)

### 9.3 Enterprise Application Development
- [Applications in Microservice Architecture](9.application_scenarios/9.3.enterprise_application_development/applications_in_microservice_architecture.md)
- [Enterprise Database Integration](9.application_scenarios/9.3.enterprise_application_development/enterprise_database_integration.md)

### 9.4 Command-line Tool Development
- [Data Processing Scripts](9.application_scenarios/9.4.command_line_tool_development/data_processing_scripts.md)
- [ETL Process Implementation](9.application_scenarios/9.4.command_line_tool_development/etl_process_implementation.md)

## [10. Complete Usage Examples](10.complete_examples/README.md)
- Web Application Example
- Data Analysis Example
- Microservice Example
- Command-line Tool Example

## [11. Contributing](11.contributing/README.md)
- [Ideas & Feature Requests](11.contributing/ideas_and_feature_requests.md)
- [Development Process](11.contributing/development_process.md)
- [Bug Fixes](11.contributing/bug_fixes.md)
- [Documentation Contributions](11.contributing/documentation_contributions.md)
- [Sponsorship](11.contributing/sponsorship.md)

## [12. API Reference](12.api_reference/README.md)
- Complete Class/Method Documentation