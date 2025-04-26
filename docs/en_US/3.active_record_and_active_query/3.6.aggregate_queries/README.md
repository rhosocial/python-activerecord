# Aggregate Queries

Aggregate queries allow you to perform calculations on groups of rows in your database. rhosocial ActiveRecord provides a comprehensive set of tools for building and executing aggregate queries, from simple counts to complex statistical analysis.

## Overview

Aggregate functions operate on multiple rows and return a single value. Common examples include COUNT, SUM, AVG, MIN, and MAX. rhosocial ActiveRecord implements these functions through the `AggregateQueryMixin` class, which extends the base query functionality with aggregate capabilities.

## Contents

- [Basic Aggregate Functions](basic_aggregate_functions.md)
  - COUNT, SUM, AVG, MIN, MAX
  - Using DISTINCT with aggregate functions
  - Scalar vs. grouped aggregates

- [Group By Operations](group_by_operations.md)
  - Grouping data by columns
  - Multiple column grouping
  - Handling NULL values in grouping

- [Having Clauses](having_clauses.md)
  - Filtering grouped results
  - Combining WHERE and HAVING
  - Using aggregate functions in HAVING

- [Complex Aggregations](complex_aggregations.md)
  - Combining multiple aggregate functions
  - Subqueries in aggregations
  - Conditional aggregations

- [Window Functions](window_functions.md)
  - OVER clause basics
  - Partitioning data
  - Window frame specifications
  - Named windows
  - Common window functions (ROW_NUMBER, RANK, etc.)

- [Statistical Queries](statistical_queries.md)
  - Statistical functions
  - Percentiles and distributions
  - Correlation and regression

- [JSON Operations](json_operations.md)
  - JSON Extraction (EXTRACT)
  - JSON Text Extraction (EXTRACT_TEXT)
  - JSON Contains Check (CONTAINS)
  - JSON Path Existence Check (EXISTS)
  - JSON Type Retrieval (TYPE)
  - JSON Element Operations (REMOVE/INSERT/REPLACE/SET)

- [Custom Expressions](custom_expressions.md)
  - Arithmetic Expressions
  - Function Expressions
  - CASE Expressions
  - Conditional Expressions (COALESCE, NULLIF, etc.)
  - Subquery Expressions
  - Grouping Set Expressions (CUBE, ROLLUP, GROUPING SETS)

## Database Compatibility

Not all databases support the same aggregate features. rhosocial ActiveRecord provides a consistent API across different database backends, but some advanced features may not be available on all databases:

- **Basic aggregates** (COUNT, SUM, AVG, MIN, MAX) are supported by all databases
- **Window functions** are supported by PostgreSQL, MySQL 8.0+, MariaDB 10.2+, and SQLite 3.25+
- **JSON operations** are supported by PostgreSQL, MySQL 5.7+, MariaDB 10.2+, and SQLite 3.9+ (with varying syntax)
- **Advanced grouping** (CUBE, ROLLUP, GROUPING SETS) are fully supported by PostgreSQL, partially by MySQL/MariaDB (ROLLUP only), and not supported by SQLite

The library automatically adapts to the capabilities of your database and will raise appropriate exceptions when unsupported features are used.