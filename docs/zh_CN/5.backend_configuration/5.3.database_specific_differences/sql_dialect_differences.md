# SQL方言差异

本文档探讨了rhosocial ActiveRecord支持的数据库系统之间的SQL方言差异，以及框架如何处理这些差异。

## 目录

- [SQL方言简介](#sql方言简介)
- [rhosocial ActiveRecord如何处理方言差异](#python-activerecord如何处理方言差异)
- [主要方言差异](#主要方言差异)
  - [查询语法](#查询语法)
  - [函数名称和行为](#函数名称和行为)
  - [分页和限制](#分页和限制)
  - [连接和表引用](#连接和表引用)
  - [事务控制](#事务控制)
  - [锁定机制](#锁定机制)
  - [返回子句](#返回子句)
  - [JSON操作](#json操作)
  - [窗口函数](#窗口函数)
  - [公共表表达式（CTEs）](#公共表表达式ctes)
  - [标识符引用](#标识符引用)
  - [大小写敏感性](#大小写敏感性)
- [数据库特定SQL功能](#数据库特定sql功能)
  - [SQLite](#sqlite)
  - [MySQL](#mysql)
  - [MariaDB](#mariadb)
  - [PostgreSQL](#postgresql)
  - [Oracle](#oracle)
  - [SQL Server](#sql-server)
- [编写可移植SQL](#编写可移植sql)
- [安全使用原始SQL](#安全使用原始sql)

## SQL方言简介

虽然SQL是一种标准化语言，但每个数据库系统都实现了自己的方言，具有独特的语法、函数和功能。这些差异可以从函数名称的微小变化到复杂操作执行方式的显著差异。

SQL方言在几个关键领域有所不同：

- **语法**：常见操作的确切语法
- **函数**：可用函数及其名称
- **功能**：某些系统可能有而其他系统没有的高级功能
- **限制**：每个系统特有的约束和限制
- **扩展**：对SQL标准的供应商特定扩展

## rhosocial ActiveRecord如何处理方言差异

rhosocial ActiveRecord通过其查询构建器和SQL生成系统抽象了许多方言差异。该框架使用分层方法：

1. **统一查询接口**：ActiveRecord和ActiveQuery提供了一个与数据库无关的API来构建查询
2. **SQL方言类**：每个数据库后端实现了一个`SQLDialectBase`子类，处理特定方言的SQL生成
3. **SQL构建器**：数据库特定的SQL构建器类为每个操作生成适当的SQL语法

这种架构允许您编写适用于不同数据库系统的代码，而无需担心底层SQL方言差异。

## 主要方言差异

### 查询语法

#### 占位符样式

不同的数据库使用不同的占位符样式进行参数化查询：

| 数据库        | 占位符样式 | 示例                          |
|---------------|-------------------|-------------------------------|
| SQLite        | `?`               | `SELECT * FROM users WHERE id = ?` |
| MySQL         | `?`               | `SELECT * FROM users WHERE id = ?` |
| MariaDB       | `?`               | `SELECT * FROM users WHERE id = ?` |
| PostgreSQL    | `$n`              | `SELECT * FROM users WHERE id = $1` |
| Oracle        | `:name`           | `SELECT * FROM users WHERE id = :id` |
| SQL Server    | `@name`           | `SELECT * FROM users WHERE id = @id` |

rhosocial ActiveRecord通过将占位符转换为每个数据库后端的适当样式来处理这些差异。

### 函数名称和行为

常见函数在不同数据库系统中通常有不同的名称或行为：

| 函数              | SQLite                | MySQL                | MariaDB              | PostgreSQL            | Oracle                | SQL Server            |
|-------------------|------------------------|----------------------|----------------------|------------------------|------------------------|------------------------|
| 字符串连接       | `||` 或 `concat()`    | `concat()`           | `concat()`           | `||` 或 `concat()`    | `||` 或 `concat()`    | `+` 或 `concat()`     |
| 子字符串         | `substr()`            | `substring()`        | `substring()`        | `substring()`         | `substr()`            | `substring()`         |
| 当前日期         | `date('now')`         | `curdate()`          | `curdate()`          | `current_date`        | `sysdate`             | `getdate()`           |
| 当前时间戳       | `datetime('now')`     | `now()`              | `now()`              | `current_timestamp`   | `systimestamp`        | `getdate()`           |
| IFNULL            | `ifnull()`            | `ifnull()`           | `ifnull()`           | `coalesce()`          | `nvl()`               | `isnull()`            |
| 随机值           | `random()`            | `rand()`             | `rand()`             | `random()`            | `dbms_random.value`   | `rand()`              |

rhosocial ActiveRecord的SQL方言类将这些函数映射到每个数据库系统的适当等效项。

### 分页和限制

不同的数据库对分页有不同的语法：

| 数据库        | 分页语法                                            |
|---------------|--------------------------------------------------------|
| SQLite        | `LIMIT [limit] OFFSET [offset]`                        |
| MySQL         | `LIMIT [offset], [limit]` 或 `LIMIT [limit] OFFSET [offset]` |
| MariaDB       | `LIMIT [offset], [limit]` 或 `LIMIT [limit] OFFSET [offset]` |
| PostgreSQL    | `LIMIT [limit] OFFSET [offset]`                        |
| Oracle        | `OFFSET [offset] ROWS FETCH NEXT [limit] ROWS ONLY` (12c+) 或带`ROWNUM`的子查询 |
| SQL Server    | `OFFSET [offset] ROWS FETCH NEXT [limit] ROWS ONLY` (2012+) 或带子查询的`TOP` |

### 连接和表引用

虽然大多数数据库支持标准JOIN语法，但表的引用和连接方式存在差异：

- **跨数据库连接**：某些数据库允许连接来自不同数据库或模式的表，而其他数据库则不允许
- **自连接**：自连接的语法可能有所不同
- **横向连接**：对横向连接的支持（允许子查询引用前面FROM项的列）各不相同

### 事务控制

事务控制语句有一些变化：

| 操作              | 标准SQL             | 变体                                          |
|---------------------|----------------------|-------------------------------------------------|
| 开始事务         | `BEGIN TRANSACTION`  | `START TRANSACTION` (MySQL), `START TRANSACTION` (MariaDB), `BEGIN` (PostgreSQL) |
| 提交事务         | `COMMIT`             | 通常一致                                      |
| 回滚事务         | `ROLLBACK`           | 通常一致                                      |
| 保存点           | `SAVEPOINT [name]`   | 通常一致                                      |
| 释放保存点       | `RELEASE SAVEPOINT [name]` | 并非所有数据库都支持                        |
| 回滚到保存点     | `ROLLBACK TO SAVEPOINT [name]` | `ROLLBACK TO [name]` (PostgreSQL)     |

### 锁定机制

行级锁定语法差异显著：

| 数据库        | 悲观锁语法                                         |
|---------------|-------------------------------------------------------|
| SQLite        | 通过`BEGIN IMMEDIATE`提供有限支持                   |
| MySQL         | `SELECT ... FOR UPDATE` 或 `SELECT ... LOCK IN SHARE MODE` |
| MariaDB       | `SELECT ... FOR UPDATE` 或 `SELECT ... LOCK IN SHARE MODE` |
| PostgreSQL    | `SELECT ... FOR UPDATE` 或 `SELECT ... FOR SHARE`     |
| Oracle        | `SELECT ... FOR UPDATE` 或 `SELECT ... FOR UPDATE NOWAIT` |
| SQL Server    | `SELECT ... WITH (UPDLOCK)` 或 `SELECT ... WITH (HOLDLOCK)` |

### 返回子句

从INSERT、UPDATE或DELETE操作返回受影响行的能力各不相同：

| 数据库        | 对RETURNING的支持                                   |
|---------------|-------------------------------------------------------|
| SQLite        | 通过`RETURNING`支持（在较新版本中）                 |
| MySQL         | 不直接支持（需要单独查询）                          |
| MariaDB       | 10.5+版本通过`RETURNING`支持                        |
| PostgreSQL    | 通过`RETURNING`完全支持                             |
| Oracle        | 通过`RETURNING ... INTO`支持                        |
| SQL Server    | 通过`OUTPUT`支持                                    |

### JSON操作

对JSON操作的支持差异很大：

| 数据库        | 原生JSON支持 | JSON路径语法                        |
|---------------|---------------------|------------------------------------|
| SQLite        | 有限              | 带路径参数的JSON函数                |
| MySQL         | 是 (5.7+)          | `->` 和 `->>` 运算符               |
| MariaDB       | 是 (10.2+)         | `->` 和 `->>` 运算符               |
| PostgreSQL    | 是 (JSONB类型)      | `->` 和 `->>` 运算符, `@>` 包含    |
| Oracle        | 是 (21c+)           | JSON_VALUE, JSON_QUERY函数         |
| SQL Server    | 是 (2016+)          | JSON_VALUE, JSON_QUERY函数         |

### 窗口函数

窗口函数（OVER子句）支持各不相同：

| 数据库        | 窗口函数支持                                        |
|---------------|-----------------------------------------------------|
| SQLite        | 在较新版本中有限支持                               |
| MySQL         | 在MySQL 8.0+中支持                                 |
| MariaDB       | 在MariaDB 10.2+中支持                              |
| PostgreSQL    | 全面支持                                           |
| Oracle        | 全面支持                                           |
| SQL Server    | 全面支持                                           |

### 公共表表达式（CTEs）

对CTEs和递归查询的支持：

| 数据库        | CTE支持                                             |
|---------------|-----------------------------------------------------|
| SQLite        | 支持（包括递归）                                    |
| MySQL         | 在MySQL 8.0+中支持（包括递归）                     |
| MariaDB       | 在MariaDB 10.2+中支持（包括递归）                  |
| PostgreSQL    | 全面支持（包括递归）                               |
| Oracle        | 全面支持（包括递归）                               |
| SQL Server    | 全面支持（包括递归）                               |

### 标识符引用

不同的数据库使用不同的字符来引用标识符：

| 数据库        | 标识符引用                                          |
|---------------|-----------------------------------------------------|
| SQLite        | 双引号或反引号                                      |
| MySQL         | 反引号                                             |
| MariaDB       | 反引号                                             |
| PostgreSQL    | 双引号                                             |
| Oracle        | 双引号                                             |
| SQL Server    | 方括号或双引号                                     |

### 大小写敏感性

数据库在处理标识符和字符串比较的大小写敏感性方面存在差异：

| 数据库        | 标识符大小写敏感性 | 字符串比较大小写敏感性 |
|---------------|-----------------------------|---------------------------------|
| SQLite        | 默认不区分大小写 | 默认区分大小写       |
| MySQL         | 取决于操作系统和配置 | 取决于排序规则（通常不区分大小写） |
| MariaDB       | 取决于操作系统和配置 | 取决于排序规则（通常不区分大小写） |
| PostgreSQL    | 默认区分大小写   | 默认区分大小写       |
| Oracle        | 默认不区分大小写 | 默认区分大小写       |
| SQL Server    | 默认不区分大小写 | 取决于排序规则（通常不区分大小写） |

## 数据库特定SQL功能

每个数据库系统都有其他系统中不可用的独特功能：

### SQLite

- **虚拟表**：FTS（全文搜索）、R-Tree等
- **JSON1扩展**：用于处理JSON数据的JSON函数
- **窗口函数**：在较新版本中有限支持
- **简单且可移植**：基于文件的数据库，无需服务器

### MySQL

- **存储引擎**：InnoDB、MyISAM、Memory等
- **全文搜索**：内置全文搜索功能
- **JSON函数**：在MySQL 5.7+中全面支持JSON
- **地理函数**：空间数据类型和函数
- **窗口函数**：MySQL 8.0+支持
- **CTE**：MySQL 8.0+支持

### MariaDB

- **存储引擎**：InnoDB、MyISAM、Memory、Aria等
- **全文搜索**：内置全文搜索功能
- **JSON函数**：在MariaDB 10.2+中支持JSON
- **地理函数**：空间数据类型和函数
- **列式存储**：ColumnStore引擎
- **RETURNING子句**：MariaDB 10.5+支持

### PostgreSQL

- **高级数据类型**：数组、JSONB、几何类型、网络地址类型等
- **可扩展性**：自定义数据类型、运算符和函数
- **全文搜索**：带排名的复杂全文搜索
- **地理信息系统**：用于空间数据的PostGIS扩展
- **表继承**：面向对象的表继承

### Oracle

- **PL/SQL**：强大的过程语言
- **物化视图**：预计算的查询结果
- **层次查询**：用于树结构的CONNECT BY语法
- **高级分区**：复杂的表分区选项
- **Oracle Text**：高级文本搜索和分析

### SQL Server

- **T-SQL**：Transact-SQL过程语言
- **公共表表达式**：高级CTE功能
- **全文搜索**：集成全文搜索
- **时态表**：系统版本化时态表
- **图数据库**：节点和边表类型

## 编写可移植SQL

编写需要在不同数据库系统上工作的SQL时，请遵循以下准则：

1. **使用标准SQL**：坚持使用SQL标准的一部分并得到广泛支持的SQL功能
2. **避免数据库特定函数**：使用ActiveRecord的查询构建器而不是数据库特定函数
3. **谨慎使用数据类型**：使用在各数据库中行为一致的数据类型
4. **在所有目标数据库上测试**：验证您的查询在您需要支持的所有数据库系统上正确工作
5. **使用ActiveRecord抽象**：尽可能让ActiveRecord处理方言差异

## 安全使用原始SQL

当您需要使用原始SQL（通过`raw_sql`方法或类似方法）时，请考虑以下最佳实践：

1. **检查数据库类型**：基于数据库类型使用条件逻辑

   ```python
   def get_complex_query(self):
       db_type = self.connection.dialect.db_type
       if db_type == 'postgresql':
           return "SELECT ... PostgreSQL特定语法 ..."
       elif db_type == 'mysql':
           return "SELECT ... MySQL特定语法 ..."
       # ...
   ```

2. **使用查询片段**：从可以根据数据库类型有条件选择的片段构建查询

3. **记录数据库需求**：清楚地记录您的原始SQL与哪些数据库系统兼容

4. **考虑替代方案**：在使用原始SQL之前，检查ActiveRecord的查询构建器是否可以以与数据库无关的方式实现相同的结果