# 调试技术

rhosocial ActiveRecord 应用程序的调试当前依赖于标准Python调试技术结合基本日志功能。

## 使用Python调试器

调试ActiveRecord应用程序的最有效方法是使用标准Python调试工具：

- `pdb` - Python的内置调试器
- `breakpoint()` - 设置断点的内置函数（Python 3.7+）
- IDE调试器（PyCharm、VS Code等）

## 调试的基本日志

基本日志支持通过Python的标准日志模块提供：

```python
import logging
from rhosocial.activerecord import ActiveRecord

# 启用日志以查看SQL查询
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('rhosocial.activerecord')

# 示例调试方法
def debug_model_operations():
    user = User(name="调试用户", email="debug@example.com")
    print(f"创建用户: {user.name}, {user.email}")
    
    result = user.save()
    print(f"保存结果: {result}")
    print(f"保存后的用户ID: {user.id}")
```

## 查询调试

当前，查询调试通过以下方式完成：

- 检查生成的SQL字符串（如果可用）
- 使用打印语句检查值
- 使用Python调试器逐步执行代码

## 常见调试方法

1. **模型验证问题**：在验证前后打印模型值
2. **数据库连接问题**：检查连接参数和数据库可用性
3. **查询问题**：检查查询参数和预期与实际结果

## 限制

- 无内置查询分析
- 无ActiveRecord特定的高级调试工具
- 有限的查询检查功能
- 无自动调试辅助工具

调试工具将在未来版本中增强，提供更多ActiveRecord特定的功能。

## 使用日志进行调试

日志是调试ActiveRecord应用程序最强大的工具之一。rhosocial ActiveRecord提供了全面的日志功能，帮助您了解底层发生的情况。

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

rhosocial ActiveRecord使用标准的Python日志级别：

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
users = User.where("age > ?", (25,)).order_by("created_at DESC").limit(10).all()

# 示例日志输出：
# DEBUG:rhosocial.activerecord.query:Executing SQL: SELECT * FROM users WHERE age > ? ORDER BY created_at DESC LIMIT 10 with params (25,)
```

## 检查查询执行

了解ActiveRecord如何将代码转换为SQL查询对于调试性能问题和意外结果至关重要。

### 使用explain()方法

`explain()`方法显示数据库将如何执行查询，帮助您理解查询的执行计划和性能特征：

```python
from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat

# 获取基本查询执行计划
explanation = User.where("age > ?", (25,)).order_by("created_at DESC").explain()
print(explanation)

# 使用特定类型的执行计划（SQLite特有的QUERYPLAN类型）
query_plan = User.where("age > ?", (25,)).explain(type=ExplainType.QUERYPLAN).all()
print(query_plan)  # 输出更易读的查询计划

# 使用详细选项（根据数据库支持情况）
detailed_explanation = User.where("age > ?", (25,)).explain(
    type=ExplainType.BASIC,  # 基本执行计划
    format=ExplainFormat.TEXT,  # 文本格式输出
    verbose=True  # 详细信息
).all()
print(detailed_explanation)
```

#### 支持的参数

`explain()`方法支持以下参数：

- **type**: 执行计划类型
  - `ExplainType.BASIC`: 基本执行计划（默认）
  - `ExplainType.ANALYZE`: 包含实际执行统计信息
  - `ExplainType.QUERYPLAN`: 仅查询计划（SQLite特有）

- **format**: 输出格式
  - `ExplainFormat.TEXT`: 人类可读文本（默认，所有数据库都支持）
  - `ExplainFormat.JSON`: JSON格式（部分数据库支持）
  - `ExplainFormat.XML`: XML格式（部分数据库支持）
  - `ExplainFormat.YAML`: YAML格式（PostgreSQL支持）
  - `ExplainFormat.TREE`: 树形格式（MySQL支持）

- **其他选项**:
  - `costs=True`: 显示估计成本
  - `buffers=False`: 显示缓冲区使用情况
  - `timing=True`: 包含时间信息
  - `verbose=False`: 显示额外信息
  - `settings=False`: 显示修改的设置（PostgreSQL）
  - `wal=False`: 显示WAL使用情况（PostgreSQL）

#### 数据库差异

不同数据库对`explain()`的支持有所不同：

- **SQLite**: 支持`BASIC`和`QUERYPLAN`类型，仅支持`TEXT`格式
- **PostgreSQL**: 支持更多选项，如`buffers`、`settings`和`wal`
- **MySQL**: 支持`TREE`格式输出

请注意，如果为特定数据库指定了不支持的选项，这些选项将被忽略或可能引发错误。

### 分析查询性能

识别慢查询：

```python
import time

# 测量查询执行时间
start_time = time.time()
result = User.where("age > ?", (25,)).order_by("created_at DESC").all()
end_time = time.time()

print(f"查询耗时 {end_time - start_time:.6f} 秒")
print(f"检索到 {len(result)} 条记录")
```

### 调试复杂查询

对于带有连接、预加载或聚合的复杂查询：

```python
# 获取原始SQL而不执行查询
query = User.joins("posts").where("posts.published = ?", (True,)).group("users.id")
raw_sql, params = query.to_sql()  # 注意：to_sql()同时返回SQL和参数
print(f"生成的SQL: {raw_sql}")
print(f"参数: {params}")

# 使用调试日志执行
result = query.all()
```

#### 使用链式调用的增量调试

对于复杂的链式调用，您可以通过检查每个方法调用后的SQL来逐步调试：

```python
# 从基本查询开始
query = User.where("active = ?", (True,))
sql, params = query.to_sql()
print(f"where之后: {sql}，参数 {params}")

# 添加连接
query = query.joins("posts")
sql, params = query.to_sql()
print(f"join之后: {sql}，参数 {params}")

# 在连接的表上添加条件
query = query.where("posts.published = ?", (True,))
sql, params = query.to_sql()
print(f"第二个where之后: {sql}，参数 {params}")

# 添加分组
query = query.group("users.id")
sql, params = query.to_sql()
print(f"分组之后: {sql}，参数 {params}")

# 最后执行
result = query.all()
```

这种方法帮助您理解链中的每个方法如何影响最终的SQL查询，使识别问题可能出现的位置变得更容易。

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

# 您还可以调试为预加载生成的SQL
sql, params = User.with_("posts.comments").to_sql()
print(f"预加载SQL: {sql}")
print(f"参数: {params}")

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
users = User.all()  # 1个查询获取所有用户
for user in users:  # 如果有100个用户，这将触发100个额外查询
    print(f"用户 {user.username} 有 {len(user.posts)} 篇文章")  # 每次访问user.posts都会触发一个查询
# 总计：101个查询（1 + N）

# 更好的方法（使用预加载）
users = User.with_("posts").all()  # 1个查询获取用户 + 1个查询获取所有相关文章
for user in users:  # 无论有多少用户，都不会有额外查询
    print(f"用户 {user.username} 有 {len(user.posts)} 篇文章")  # 不会有额外查询
# 总计：2个查询
```

#### 点分表示法用于关系名称

使用`with_()`进行预加载时，您可以使用点分表示法指定嵌套关系。理解这种命名约定对于有效调试至关重要：

```python
# 加载单个关系
users = User.with_("posts").all()

# 在同一级别加载多个关系
users = User.with_("posts", "profile", "settings").all()

# 加载嵌套关系（文章及其评论）
users = User.with_("posts.comments").all()

# 加载深度嵌套关系
users = User.with_("posts.comments.author.profile").all()

# 加载多个嵌套路径
users = User.with_("posts.comments", "posts.tags", "profile.settings").all()
```

关系路径中的每个点都代表一级嵌套。系统将生成适当的JOIN语句，以最少的查询次数获取所有所需数据。

#### 调试N+1问题

要识别N+1问题，请在日志中查找模式，其中同一类型的查询使用不同参数重复多次：

```python
# 启用详细查询日志
configure_logging(level=logging.DEBUG, component="query")

# 执行可能存在N+1问题的代码
users = User.all()
for user in users:
    _ = user.posts  # 如果没有预加载，这将触发N个单独的查询
```

#### 关系性能的数据库索引

适当的数据库索引对关系性能至关重要：

```python
# 在迁移中创建索引的示例
def up(self):
    # 在外键列上创建索引
    self.add_index("posts", "user_id")  # 加速User.posts关系
    
    # 为多个条件创建复合索引
    self.add_index("posts", ["user_id", "published"])  # 加速User.posts.where(published=True)
```

调试关系性能问题时：

1. 检查外键列上是否存在适当的索引
2. 使用`explain()`查看是否使用了索引
3. 考虑为经常过滤的关系添加复合索引
4. 监控有无索引时的查询执行时间，以衡量改进

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