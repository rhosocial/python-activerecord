# SQL Dialect Differences

This document explores the differences in SQL dialects between the database systems supported by rhosocial ActiveRecord and how these differences are handled by the framework.

## Contents

- [Introduction to SQL Dialects](#introduction-to-sql-dialects)
- [How rhosocial ActiveRecord Handles Dialect Differences](#how-python-activerecord-handles-dialect-differences)
- [Key Dialect Differences](#key-dialect-differences)
  - [Query Syntax](#query-syntax)
  - [Function Names and Behavior](#function-names-and-behavior)
  - [Pagination and Limiting](#pagination-and-limiting)
  - [Joins and Table References](#joins-and-table-references)
  - [Transaction Control](#transaction-control)
  - [Locking Mechanisms](#locking-mechanisms)
  - [Returning Clauses](#returning-clauses)
  - [JSON Operations](#json-operations)
  - [Window Functions](#window-functions)
  - [Common Table Expressions (CTEs)](#common-table-expressions-ctes)
  - [Identifier Quoting](#identifier-quoting)
  - [Case Sensitivity](#case-sensitivity)
- [Database-Specific SQL Features](#database-specific-sql-features)
  - [SQLite](#sqlite)
  - [MySQL](#mysql)
  - [MariaDB](#mariadb)
  - [PostgreSQL](#postgresql)
  - [Oracle](#oracle)
  - [SQL Server](#sql-server)
- [Writing Portable SQL](#writing-portable-sql)
- [Using Raw SQL Safely](#using-raw-sql-safely)

## Introduction to SQL Dialects

While SQL is a standardized language, each database system implements its own dialect with unique syntax, functions, and features. These differences can range from minor variations in function names to significant differences in how complex operations are performed.

SQL dialects differ in several key areas:

- **Syntax**: The exact syntax for common operations
- **Functions**: Available functions and their names
- **Features**: Advanced features that may be available in some systems but not others
- **Limitations**: Constraints and limitations specific to each system
- **Extensions**: Vendor-specific extensions to the SQL standard

## How rhosocial ActiveRecord Handles Dialect Differences

rhosocial ActiveRecord abstracts away many dialect differences through its query builder and SQL generation system. The framework uses a layered approach:

1. **Unified Query Interface**: ActiveRecord and ActiveQuery provide a database-agnostic API for building queries
2. **SQL Dialect Classes**: Each database backend implements a `SQLDialectBase` subclass that handles dialect-specific SQL generation
3. **SQL Builders**: Database-specific SQL builder classes generate the appropriate SQL syntax for each operation

This architecture allows you to write code that works across different database systems without worrying about the underlying SQL dialect differences.

## Key Dialect Differences

### Query Syntax

#### Placeholder Styles

Different databases use different placeholder styles for parameterized queries:

| Database      | Placeholder Style | Example                      |
|---------------|-------------------|------------------------------|
| SQLite        | `?`               | `SELECT * FROM users WHERE id = ?` |
| MySQL         | `?`               | `SELECT * FROM users WHERE id = ?` |
| MariaDB       | `?`               | `SELECT * FROM users WHERE id = ?` |
| PostgreSQL    | `$n`              | `SELECT * FROM users WHERE id = $1` |
| Oracle        | `:name`           | `SELECT * FROM users WHERE id = :id` |
| SQL Server    | `@name`           | `SELECT * FROM users WHERE id = @id` |

rhosocial ActiveRecord handles these differences by converting placeholders to the appropriate style for each database backend.

### Function Names and Behavior

Common functions often have different names or behavior across database systems:

| Function          | SQLite                | MySQL                | MariaDB              | PostgreSQL            | Oracle                | SQL Server            |
|-------------------|------------------------|----------------------|----------------------|------------------------|------------------------|------------------------|
| String Concat     | `||` or `concat()`    | `concat()`           | `concat()`           | `||` or `concat()`    | `||` or `concat()`    | `+` or `concat()`     |
| Substring         | `substr()`            | `substring()`        | `substring()`        | `substring()`         | `substr()`            | `substring()`         |
| Current Date      | `date('now')`         | `curdate()`          | `curdate()`          | `current_date`        | `sysdate`             | `getdate()`           |
| Current Timestamp | `datetime('now')`     | `now()`              | `now()`              | `current_timestamp`   | `systimestamp`        | `getdate()`           |
| IFNULL            | `ifnull()`            | `ifnull()`           | `ifnull()`           | `coalesce()`          | `nvl()`               | `isnull()`            |
| Random Value      | `random()`            | `rand()`             | `rand()`             | `random()`            | `dbms_random.value`   | `rand()`              |

rhosocial ActiveRecord's SQL dialect classes map these functions to their appropriate equivalents for each database system.

### Pagination and Limiting

Different databases have different syntax for pagination:

| Database      | Pagination Syntax                                      |
|---------------|--------------------------------------------------------|
| SQLite        | `LIMIT [limit] OFFSET [offset]`                        |
| MySQL         | `LIMIT [offset], [limit]` or `LIMIT [limit] OFFSET [offset]` |
| MariaDB       | `LIMIT [offset], [limit]` or `LIMIT [limit] OFFSET [offset]` |
| PostgreSQL    | `LIMIT [limit] OFFSET [offset]`                        |
| Oracle        | `OFFSET [offset] ROWS FETCH NEXT [limit] ROWS ONLY` (12c+) or subquery with `ROWNUM` |
| SQL Server    | `OFFSET [offset] ROWS FETCH NEXT [limit] ROWS ONLY` (2012+) or `TOP` with subquery |

### Joins and Table References

While most databases support standard JOIN syntax, there are differences in how tables can be referenced and joined:

- **Cross-Database Joins**: Some databases allow joining tables from different databases or schemas, while others don't
- **Self-Joins**: The syntax for self-joins can vary
- **Lateral Joins**: Support for lateral joins (allowing subqueries to reference columns from preceding FROM items) varies

### Transaction Control

Transaction control statements have some variations:

| Operation           | Standard SQL         | Variations                                      |
|---------------------|----------------------|-------------------------------------------------|
| Begin Transaction   | `BEGIN TRANSACTION`  | `START TRANSACTION` (MySQL/MariaDB), `BEGIN` (PostgreSQL) |
| Commit Transaction  | `COMMIT`             | Generally consistent                            |
| Rollback Transaction| `ROLLBACK`           | Generally consistent                            |
| Savepoint          | `SAVEPOINT [name]`   | Generally consistent                            |
| Release Savepoint   | `RELEASE SAVEPOINT [name]` | Not supported in all databases              |
| Rollback to Savepoint | `ROLLBACK TO SAVEPOINT [name]` | `ROLLBACK TO [name]` (PostgreSQL)     |

### Locking Mechanisms

Row-level locking syntax varies significantly:

| Database      | Pessimistic Lock Syntax                               |
|---------------|-------------------------------------------------------|
| SQLite        | Limited support via `BEGIN IMMEDIATE`                 |
| MySQL         | `SELECT ... FOR UPDATE` or `SELECT ... LOCK IN SHARE MODE` |
| MariaDB       | `SELECT ... FOR UPDATE` or `SELECT ... LOCK IN SHARE MODE` |
| PostgreSQL    | `SELECT ... FOR UPDATE` or `SELECT ... FOR SHARE`     |
| Oracle        | `SELECT ... FOR UPDATE` or `SELECT ... FOR UPDATE NOWAIT` |
| SQL Server    | `SELECT ... WITH (UPDLOCK)` or `SELECT ... WITH (HOLDLOCK)` |

### Returning Clauses

The ability to return affected rows from INSERT, UPDATE, or DELETE operations varies:

| Database      | Support for RETURNING                                 |
|---------------|-------------------------------------------------------|
| SQLite        | Supported via `RETURNING` (in newer versions)         |
| MySQL         | Not directly supported (requires separate query)      |
| MariaDB       | Not directly supported (requires separate query)      |
| PostgreSQL    | Fully supported via `RETURNING`                       |
| Oracle        | Supported via `RETURNING ... INTO`                    |
| SQL Server    | Supported via `OUTPUT`                                |

### JSON Operations

Support for JSON operations varies widely:

| Database      | Native JSON Support | JSON Path Syntax                    |
|---------------|---------------------|------------------------------------|  
| SQLite        | Limited            | JSON functions with path arguments  |
| MySQL         | Yes (5.7+)         | `->` and `->>` operators           |
| MariaDB       | Yes (10.2+)        | `->` and `->>` operators           |
| PostgreSQL    | Yes (JSONB type)    | `->` and `->>` operators, `@>` contains |
| Oracle        | Yes (21c+)          | JSON_VALUE, JSON_QUERY functions   |
| SQL Server    | Yes (2016+)         | JSON_VALUE, JSON_QUERY functions   |

### Window Functions

Window functions (OVER clause) support varies:

| Database      | Window Function Support                              |
|---------------|-----------------------------------------------------|
| SQLite        | Limited support in newer versions                   |
| MySQL         | Supported in MySQL 8.0+                             |
| MariaDB       | Supported in MariaDB 10.2+                          |
| PostgreSQL    | Comprehensive support                               |
| Oracle        | Comprehensive support                               |
| SQL Server    | Comprehensive support                               |

### Common Table Expressions (CTEs)

Support for CTEs and recursive queries:

| Database      | CTE Support                                          |
|---------------|-----------------------------------------------------|
| SQLite        | Supported (including recursive)                      |
| MySQL         | Supported in MySQL 8.0+ (including recursive)        |
| MariaDB       | Supported in MariaDB 10.2+ (including recursive)     |
| PostgreSQL    | Comprehensive support (including recursive)          |
| Oracle        | Comprehensive support (including recursive)          |
| SQL Server    | Comprehensive support (including recursive)          |

### Identifier Quoting

Different databases use different characters to quote identifiers:

| Database      | Identifier Quoting                                   |
|---------------|-----------------------------------------------------|
| SQLite        | Double quotes or backticks                          |
| MySQL         | Backticks                                           |
| MariaDB       | Backticks                                           |
| PostgreSQL    | Double quotes                                       |
| Oracle        | Double quotes                                       |
| SQL Server    | Square brackets or double quotes                    |

### Case Sensitivity

Databases differ in how they handle case sensitivity in identifiers and string comparisons:

| Database      | Identifier Case Sensitivity | String Comparison Case Sensitivity |
|---------------|-----------------------------|---------------------------------|
| SQLite        | Case-insensitive by default | Case-sensitive by default       |
| MySQL         | Depends on OS and configuration | Depends on collation (often case-insensitive) |
| MariaDB       | Depends on OS and configuration | Depends on collation (often case-insensitive) |
| PostgreSQL    | Case-sensitive by default   | Case-sensitive by default       |
| Oracle        | Case-insensitive by default | Case-sensitive by default       |
| SQL Server    | Case-insensitive by default | Depends on collation (often case-insensitive) |

## Database-Specific SQL Features

Each database system has unique features that aren't available in other systems:

### SQLite

- **Virtual Tables**: FTS (Full-Text Search), R-Tree, etc.
- **JSON1 Extension**: JSON functions for working with JSON data
- **Window Functions**: Limited support in newer versions
- **Simple and Portable**: File-based database with no server required

### MySQL

- **Storage Engines**: InnoDB, MyISAM, Memory, etc.
- **Full-Text Search**: Built-in full-text search capabilities
- **JSON Functions**: Comprehensive JSON support in MySQL 5.7+
- **Geographic Functions**: Spatial data types and functions
- **Window Functions**: Comprehensive support in MySQL 8.0+
- **Document Store**: X DevAPI for document store functionality in MySQL 8.0+

### MariaDB

- **Storage Engines**: InnoDB, MyISAM, Memory, Aria, etc.
- **Full-Text Search**: Built-in full-text search capabilities
- **JSON Functions**: Comprehensive JSON support in MariaDB 10.2+
- **Geographic Functions**: Spatial data types and functions
- **Columnar Storage**: ColumnStore engine for analytical workloads
- **Temporal Tables**: System-versioned tables for point-in-time queries

### PostgreSQL

- **Advanced Data Types**: Arrays, JSONB, geometric types, network address types, etc.
- **Extensibility**: Custom data types, operators, and functions
- **Full-Text Search**: Sophisticated full-text search with ranking
- **Geographic Information System**: PostGIS extension for spatial data
- **Table Inheritance**: Object-oriented table inheritance

### Oracle

- **PL/SQL**: Powerful procedural language
- **Materialized Views**: Pre-computed query results
- **Hierarchical Queries**: CONNECT BY syntax for tree structures
- **Advanced Partitioning**: Sophisticated table partitioning options
- **Oracle Text**: Advanced text search and analysis

### SQL Server

- **T-SQL**: Transact-SQL procedural language
- **Common Table Expressions**: Advanced CTE capabilities
- **Full-Text Search**: Integrated full-text search
- **Temporal Tables**: System-versioned temporal tables
- **Graph Database**: Node and edge table types

## Writing Portable SQL

When writing SQL that needs to work across different database systems, follow these guidelines:

1. **Use Standard SQL**: Stick to SQL features that are part of the SQL standard and widely supported
2. **Avoid Database-Specific Functions**: Use ActiveRecord's query builder instead of database-specific functions
3. **Be Careful with Data Types**: Use data types that have consistent behavior across databases
4. **Test on All Target Databases**: Verify that your queries work correctly on all database systems you need to support
5. **Use ActiveRecord Abstractions**: Let ActiveRecord handle dialect differences whenever possible

## Using Raw SQL Safely

When you need to use raw SQL (via the `raw_sql` method or similar), consider these best practices:

1. **Check Database Type**: Use conditional logic based on the database type

   ```python
   def get_complex_query(self):
       db_type = self.connection.dialect.db_type
       if db_type == 'postgresql':
           return "SELECT ... PostgreSQL specific syntax ..."
       elif db_type == 'mysql':
           return "SELECT ... MySQL specific syntax ..."
       elif db_type == 'mariadb':
           return "SELECT ... MariaDB specific syntax ..."
       # ...
   ```

2. **Use Query Fragments**: Build queries from fragments that can be conditionally selected based on the database type

3. **Document Database Requirements**: Clearly document which database systems your raw SQL is compatible with

4. **Consider Alternatives**: Before using raw SQL, check if ActiveRecord's query builder can achieve the same result in a database-agnostic way