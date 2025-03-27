## Directory Structure

```
tests/
├── README.md - Test directory documentation
├── rhosocial/
│   └── activerecord/
│       ├── .gitignores - Git ignore rules file
│       ├── __init__.py - Package initialization file
│       ├── backend/ - Database backend related tests
│       │   ├── .gitignores
│       │   ├── sqlite/ - SQLite backend tests
│       │   │   ├── __init__.py
│       │   │   ├── test_backend_transaction.py - Tests backend transaction functionality
│       │   │   ├── test_explain.py - Tests SQL execution plan explanation
│       │   │   ├── test_pragma.py - Tests SQLite PRAGMA commands
│       │   │   ├── test_returning.py - Tests RETURNING clause
│       │   │   ├── test_transaction.py - Tests transaction functionality
│       │   │   └── test_version.py - Tests SQLite version compatibility
│       │   ├── sqlite2/ - Another SQLite backend test
│       │   │   ├── __init__.py
│       │   │   ├── conftest.py - Test configuration
│       │   │   ├── test_connection.py - Test database connection
│       │   │   ├── test_curd.py - Test basic CRUD operations
│       │   │   ├── test_execute_many.py - Test batch execution
│       │   │   ├── test_expression.py - Test SQL expressions
│       │   │   ├── test_mapping.py - Test object-relational mapping
│       │   │   └── test_transaction.py - Test transaction functionality
│       │   ├── test_helpers_datetime.py - Test datetime helper functions
│       │   ├── test_helpers_format.py - Test formatting helper functions
│       │   ├── test_helpers_json.py - Test JSON helper functions
│       │   ├── test_helpers_misc.py - Test miscellaneous helper functions
│       │   └── test_typing.py - Test type hints
│       ├── basic/ - Basic functionality tests
│       │   ├── .benchmarks/ - Performance benchmarks
│       │   ├── __init__.py
│       │   ├── conftest.py - Test configuration
│       │   ├── fixtures/ - Test fixtures
│       │   │   ├── __init__.py
│       │   │   ├── models.py - Test model definitions
│       │   │   └── schema/ - Database schema
│       │   ├── test_crud.py - Test CRUD operations
│       │   ├── test_fields.py - Test field types
│       │   └── test_validation.py - Test validation functionality
│       ├── community/ - Community feature tests
│       │   ├── __init__.py
│       │   ├── test_articles.py - Test article functionality
│       │   ├── test_comments.py - Test comment functionality
│       │   ├── test_friendships.py - Test friendship relations
│       │   ├── test_queries.py - Test query functionality
│       │   └── test_users.py - Test user functionality
│       ├── config/ - Configuration related tests
│       │   └── README.md - Configuration documentation
│       ├── events/ - Event system tests
│       │   ├── .benchmarks/
│       │   ├── __init__.py
│       │   ├── fixtures/ - Test fixtures
│       │   │   ├── models.py - Event models
│       │   │   └── schema/ - Database schema
│       │   ├── test_handlers.py - Test event handlers
│       │   └── test_lifecycle.py - Test lifecycle events
│       ├── fixtures/ - Shared test fixtures
│       │   ├── __init__.py
│       │   ├── community/ - Community related fixtures
│       │   │   ├── __init__.py
│       │   │   ├── models.py - Community models
│       │   │   ├── queries.py - Community queries
│       │   │   └── setup.py - Community setup
│       │   ├── events.py - Event fixtures
│       │   ├── mixins/ - Mixin class fixtures
│       │   │   ├── __init__.py
│       │   │   ├── models.py - Mixin models
│       │   │   └── setup.py - Mixin setup
│       │   └── storage.py - Storage fixtures
│       ├── interface/ - Interface tests
│       │   └── test_threadsafe_dict.py - Test thread-safe dictionary
│       ├── mixins/ - Mixin class tests
│       │   ├── .benchmarks/
│       │   ├── __init__.py
│       │   ├── fixtures/ - Test fixtures
│       │   │   ├── models.py - Mixin models
│       │   │   └── schema/ - Database schema
│       │   ├── test_combined_articles.py - Test combined article functionality
│       │   ├── test_optimistic_lock.py - Test optimistic locking
│       │   ├── test_soft_delete.py - Test soft deletion
│       │   └── test_timestamps.py - Test timestamps
│       ├── query/ - Query functionality tests
│       │   ├── __init__.py
│       │   ├── fixtures/ - Test fixtures
│       │   │   ├── extended_models.py - Extended models
│       │   │   ├── models.py - Basic models
│       │   │   └── schema/ - Database schema
│       │   ├── sqlite/ - SQLite specific query tests
│       │   │   ├── test_explain_arithmetic.py - Test arithmetic expression explanation
│       │   │   ├── test_explain_basic.py - Test basic query explanation
│       │   │   ├── test_explain_conditions.py - Test condition expression explanation
│       │   │   ├── test_explain_expressions.py - Test expression explanation
│       │   │   ├── test_explain_grouped_aggregate.py - Test grouped aggregate explanation
│       │   │   ├── test_explain_joins.py - Test join query explanation
│       │   │   ├── test_explain_simple_aggregate.py - Test simple aggregate explanation
│       │   │   └── test_explain_window_functions.py - Test window function explanation
│       │   ├── test_advanced_grouping.py - Test advanced grouping
│       │   ├── test_basic.py - Test basic queries
│       │   ├── test_case_expressions.py - Test CASE expressions
│       │   ├── test_conditions.py - Test conditional queries
│       │   ├── test_dict_query.py - Test dictionary queries
│       │   ├── test_expression.py - Test expressions
│       │   ├── test_function_expressions.py - Test function expressions
│       │   ├── test_grouped_aggregate.py - Test grouped aggregates
│       │   ├── test_joins.py - Test join queries
│       │   ├── test_json_expressions.py - Test JSON expressions
│       │   ├── test_relation_cache.py - Test relation caching
│       │   ├── test_relations_basic.py - Test basic relations
│       │   ├── test_relations_with.py - Test WITH clause
│       │   ├── test_relations_with_query.py - Test relations with queries
│       │   ├── test_scalar_aggregate.py - Test scalar aggregates
│       │   └── test_window_functions.py - Test window functions
│       │   └── utils.py - Query utilities
│       ├── relation/ - Relation tests
│       │   ├── conftest.py - Test configuration
│       │   ├── test_base.py - Test basic relations
│       │   ├── test_cache.py - Test relation caching
│       │   ├── test_descriptors.py - Test descriptors
│       │   ├── test_interfaces.py - Test interfaces
│       │   └── test_nested_relationship_access.py - Test nested relationship access
│       └── utils.py - Test utilities
```