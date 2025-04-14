# 调试技术

有效的调试对于开发和维护ActiveRecord应用程序至关重要。本指南涵盖了常见的调试策略、工具和技术，帮助您识别和解决ActiveRecord代码中的问题。

## 使用日志进行调试

日志是调试ActiveRecord应用程序最强大的工具之一。Python ActiveRecord提供了全面的日志功能，帮助您了解底层发生的情况。

### 配置日志

```python
import logging
from rhosocial.activerecord import configure_logging

# 在应用程序级别配置日志
configure_logging(level=logging.DEBUG)

# 或为特定组件配置日志
configure_logging(level=logging.DEBUG, component="query")
```

### 日志级别

Python ActiveRecord使用标准的Python日志级别：

- `DEBUG`：详细信息，通常仅用于诊断问题
- `INFO`：确认事情按预期工作
- `WARNING`：表示发生了意外情况，但应用程序仍在工作
- `ERROR`：由于更严重的问题，应用程序无法执行某项功能
- `CRITICAL`：严重错误，表明应用程序本身可能无法继续运行

### 记录什么内容

调试ActiveRecord应用程序时，考虑记录：

1. **SQL查询**：记录实际执行的SQL及其参数
2. **查询执行时间**：记录查询执行所需的时间
3. **模型操作**：记录模型的创建、更新和删除
4. **事务边界**：记录事务的开始、提交或回滚
5. **关系加载**：记录关系何时被加载

### 示例：记录SQL查询

```python
import logging
from rhosocial.activerecord import configure_logging

# 启用SQL查询日志
configure_logging(level=logging.DEBUG, component="query")

# 现在所有SQL查询都将被记录
users = User.where("age > ?", [25]).order("created_at DESC").limit(10).all()

# 示例日志输出：
# DEBUG:rhosocial.activerecord.query:Executing SQL: SELECT * FROM users WHERE age > ? ORDER BY created_at DESC LIMIT 10 with params [25]
```

## 检查查询执行

了解ActiveRecord如何将代码转换为SQL查询对于调试性能问题和意外结果至关重要。

### 使用explain()方法

`explain()`方法显示数据库将如何执行查询：

```python
# 获取查询执行计划
explanation = User.where("age > ?", [25]).order("created_at DESC").explain()
print(explanation)

# 获取更详细的输出（如果数据库支持）
detailed_explanation = User.where("age > ?", [25]).explain(analyze=True, verbose=True)
print(detailed_explanation)
```

### 分析查询性能

识别慢查询：

```python
import time

# 测量查询执行时间
start_time = time.time()
result = User.where("age > ?", [25]).order("created_at DESC").all()
end_time = time.time()

print(f"查询耗时 {end_time - start_time:.6f} 秒")
print(f"检索到 {len(result)} 条记录")
```

### 调试复杂查询

对于带有连接、预加载或聚合的复杂查询：

```python
# 获取原始SQL而不执行查询
query = User.joins("posts").where("posts.published = ?", [True]).group("users.id")
raw_sql = query.to_sql()
print(f"生成的SQL: {raw_sql}")

# 使用调试日志执行
result = query.all()
```

## 调试关系问题

关系问题在ActiveRecord应用程序中很常见。以下是调试它们的技术：

### 检查已加载的关系

```python
# 检查关系是否已加载
user = User.find_by_id(1)
print(f"posts关系是否已加载？{'_loaded_relations' in dir(user) and 'posts' in user._loaded_relations}")

# 检查已加载的关系数据
if hasattr(user, '_loaded_relations') and 'posts' in user._loaded_relations:
    print(f"已加载的posts: {user._loaded_relations['posts']}")
```

### 调试预加载

```python
# 为关系加载启用详细日志
configure_logging(level=logging.DEBUG, component="relation")

# 使用with_预加载关系
user = User.with_("posts.comments").find_by_id(1)

# 检查已加载的关系
print(f"用户有 {len(user.posts)} 篇文章")
for post in user.posts:
    print(f"文章 {post.id} 有 {len(post.comments)} 条评论")
```

## 排查常见问题

### N+1查询问题

N+1查询问题发生在获取N条记录然后执行N个额外查询来获取相关数据时：

```python
# 启用查询日志
configure_logging(level=logging.DEBUG, component="query")

# 不好的方法（导致N+1查询）
users = User.all()
for user in users:
    print(f"用户 {user.username} 有 {len(user.posts)} 篇文章")  # 每次访问user.posts都会触发一个查询

# 更好的方法（使用预加载）
users = User.with_("posts").all()
for user in users:
    print(f"用户 {user.username} 有 {len(user.posts)} 篇文章")  # 不会有额外查询
```

### 意外的查询结果

当查询返回意外结果时：

```python
# 启用查询日志以查看实际SQL
configure_logging(level=logging.DEBUG, component="query")

# 检查查询条件
query = User.where("age > ?", [25]).where("active = ?", [True])
print(f"查询条件: {query._where_conditions}")

# 执行并检查结果
results = query.all()
print(f"找到 {len(results)} 个结果")
for user in results:
    print(f"用户: {user.username}, 年龄: {user.age}, 活跃: {user.active}")
```

### 事务问题

调试事务问题：

```python
# 启用事务日志
configure_logging(level=logging.DEBUG, component="transaction")

try:
    with db_connection.transaction():
        user = User(username="test_user", email="test@example.com")
        user.save()
        
        # 模拟错误
        if not user.validate_email():
            raise ValueError("无效的电子邮件")
            
        # 如果发生错误，这不会执行
        print("事务成功完成")
except Exception as e:
    print(f"事务失败: {e}")
```

### 数据库连接问题

排查数据库连接问题：

```python
# 检查连接状态
try:
    db_connection.execute("SELECT 1")
    print("数据库连接正常")
except Exception as e:
    print(f"数据库连接错误: {e}")
    
# 检查连接池状态（如果使用连接池）
if hasattr(db_connection, "pool"):
    print(f"活动连接: {db_connection.pool.active_connections}")
    print(f"可用连接: {db_connection.pool.available_connections}")
```

## 使用Python调试器

Python内置的调试工具对ActiveRecord调试非常有价值。

### 使用pdb

```python
import pdb

# 设置断点
def process_user_data():
    users = User.where("age > ?", [25]).all()
    pdb.set_trace()  # 执行将在此处暂停
    for user in users:
        # 处理用户数据
        pass
```

### 使用IPython的调试器

如果您使用IPython，可以使用其增强的调试器：

```python
from IPython.core.debugger import set_trace

def process_user_data():
    users = User.where("age > ?", [25]).all()
    set_trace()  # IPython调试器
    for user in users:
        # 处理用户数据
        pass
```

## 调试工具和扩展

### 特定数据库的工具

许多数据库提供自己的调试工具：

- **SQLite**：SQLite Browser、SQLite Analyzer
- **PostgreSQL**：pgAdmin、pg_stat_statements
- **MySQL**：MySQL Workbench、EXPLAIN ANALYZE

### IDE集成

现代IDE提供出色的调试支持：

- **PyCharm**：集成调试器和数据库工具
- **VS Code**：带有断点和变量检查的Python调试器扩展
- **Jupyter Notebooks**：使用`%debug`魔术命令进行交互式调试

## 调试最佳实践

1. **从简单开始**：从能重现问题的最简单测试用例开始

2. **隔离问题**：确定问题是在您的代码、ActiveRecord库还是数据库中

3. **策略性使用日志**：仅为您正在调试的组件启用详细日志

4. **检查您的假设**：验证变量包含您期望的内容

5. **阅读错误消息**：ActiveRecord错误消息通常包含有关出错原因的有价值信息

6. **检查生成的SQL**：始终检查实际执行的SQL

7. **隔离测试**：单独测试各个查询或操作以精确定位问题

8. **使用版本控制**：进行小的、增量的更改并频繁提交，以便更容易识别问题引入的时间

9. **编写回归测试**：修复bug后，编写测试以确保它不会再次出现

10. **记录您的发现**：记录您遇到的bug和解决方法