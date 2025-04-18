# Database-specific Differences

While rhosocial ActiveRecord provides a unified API for working with different database systems, there are inherent differences between these systems that developers should be aware of. This section explores the key differences and considerations when working with various database backends.

> **Note:** The implementation of data types is currently subject to significant potential adjustments.

## Contents

- [Data Type Mapping](data_type_mapping.md) - How rhosocial ActiveRecord maps data types across different database systems
- [SQL Dialect Differences](sql_dialect_differences.md) - Variations in SQL syntax and features between database systems
- [Performance Considerations](performance_considerations.md) - Database-specific performance optimizations and considerations

## Introduction

Each database system has its own unique features, limitations, and implementation details. rhosocial ActiveRecord abstracts away many of these differences, allowing you to write database-agnostic code. However, understanding the underlying differences can help you:

1. **Make informed design decisions** when choosing a database backend
2. **Optimize performance** by leveraging database-specific features
3. **Troubleshoot issues** that may arise from database-specific behaviors
4. **Ensure compatibility** when migrating between different database systems

## Key Areas of Difference

### Data Types

Different database systems support different data types, and even when they support similar concepts, the implementation details can vary significantly. rhosocial ActiveRecord provides a unified type system that maps to appropriate native types for each database backend.

It's important to note that MySQL and MariaDB, despite their common ancestry, have increasingly divergent implementations of certain data types and should be treated as separate database systems with their own specific considerations.

### SQL Dialect

Each database system has its own SQL dialect with unique syntax, functions, and features. rhosocial ActiveRecord generates the appropriate SQL for each backend, but there may be cases where you need to be aware of these differences, especially when writing raw SQL or using advanced features.

While MySQL and MariaDB share many SQL syntax elements, they have diverged in certain areas, particularly in newer versions. rhosocial ActiveRecord handles these differences internally, but developers should be aware of them when writing custom SQL or when specific database features are required.

### Performance Characteristics

Database systems have different performance characteristics and optimization techniques. What works well for one database might not be optimal for another. Understanding these differences can help you design your application for maximum performance.

### Transaction Support

Transaction isolation levels, savepoint support, and error handling can vary between database systems. rhosocial ActiveRecord provides a consistent transaction API while respecting the capabilities of each database system.

### Locking Mechanisms

Different databases implement locking mechanisms (both optimistic and pessimistic) in different ways. rhosocial ActiveRecord abstracts these differences, but understanding the underlying implementation can help prevent concurrency issues.

## Cross-Database Compatibility

When developing applications that need to work with multiple database backends or might migrate between backends in the future, consider the following best practices:

1. **Avoid database-specific features** unless necessary
2. **Use ActiveRecord's query builder** instead of raw SQL when possible
3. **Test with all target database systems** to ensure compatibility
4. **Be aware of data type limitations** across different systems
5. **Consider performance implications** of database-agnostic code

The following pages provide detailed information about specific areas of difference between supported database systems.