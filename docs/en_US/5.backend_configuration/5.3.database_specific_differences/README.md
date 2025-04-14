# Database-specific Differences

While Python ActiveRecord provides a unified API for working with different database systems, there are inherent differences between these systems that developers should be aware of. This section explores the key differences and considerations when working with various database backends.

## Contents

- [Data Type Mapping](data_type_mapping.md) - How Python ActiveRecord maps data types across different database systems
- [SQL Dialect Differences](sql_dialect_differences.md) - Variations in SQL syntax and features between database systems
- [Performance Considerations](performance_considerations.md) - Database-specific performance optimizations and considerations

## Introduction

Each database system has its own unique features, limitations, and implementation details. Python ActiveRecord abstracts away many of these differences, allowing you to write database-agnostic code. However, understanding the underlying differences can help you:

1. **Make informed design decisions** when choosing a database backend
2. **Optimize performance** by leveraging database-specific features
3. **Troubleshoot issues** that may arise from database-specific behaviors
4. **Ensure compatibility** when migrating between different database systems

## Key Areas of Difference

### Data Types

Different database systems support different data types, and even when they support similar concepts, the implementation details can vary significantly. Python ActiveRecord provides a unified type system that maps to appropriate native types for each database backend.

### SQL Dialect

Each database system has its own SQL dialect with unique syntax, functions, and features. Python ActiveRecord generates the appropriate SQL for each backend, but there may be cases where you need to be aware of these differences, especially when writing raw SQL or using advanced features.

### Performance Characteristics

Database systems have different performance characteristics and optimization techniques. What works well for one database might not be optimal for another. Understanding these differences can help you design your application for maximum performance.

### Transaction Support

Transaction isolation levels, savepoint support, and error handling can vary between database systems. Python ActiveRecord provides a consistent transaction API while respecting the capabilities of each database system.

### Locking Mechanisms

Different databases implement locking mechanisms (both optimistic and pessimistic) in different ways. Python ActiveRecord abstracts these differences, but understanding the underlying implementation can help prevent concurrency issues.

## Cross-Database Compatibility

When developing applications that need to work with multiple database backends or might migrate between backends in the future, consider the following best practices:

1. **Avoid database-specific features** unless necessary
2. **Use ActiveRecord's query builder** instead of raw SQL when possible
3. **Test with all target database systems** to ensure compatibility
4. **Be aware of data type limitations** across different systems
5. **Consider performance implications** of database-agnostic code

The following pages provide detailed information about specific areas of difference between supported database systems.