# 调试技术

有效的调试对于开发和维护ActiveRecord应用程序至关重要。本指南涵盖了常见的调试策略、工具和技术，帮助您识别和解决ActiveRecord代码中的问题。

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

`explain()`方法是一个**标记方法**，它不会直接返回执行计划，而是标记当前查询应该返回执行计划。您需要将其与执行方法（如`all()`、`one()`等）结合使用，以获取数据库将如何执行查询的信息：

```python
from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat

# 获取基本查询执行计划
explanation = User.where("age > ?", (25,)).order_by("created_at DESC").explain().all()
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
query = User.joins("posts").where("posts.published = ?", (True,)).group_by("users.id")
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
query = query.group_by("users.id")
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
user = User.find_one(1)  # 注意：使用find_one而不是find_by_id
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
user = User.with_("posts.comments").find_one(1)  # 注意：使用find_one而不是find_by_id

# 您还可以调试为预加载生成的SQL
sql, params = User.with_("posts.comments").to_sql()
print(f"预加载SQL: {sql}")
print(f"参数: {params}")

# 检查已加载的关系
print(f"用户有 {len(user.posts())} 篇文章")  # 注意：使用posts()而不是posts
for post in user.posts():
    print(f"文章 {post.id} 有 {len(post.comments())} 条评论")  # 注意：使用comments()而不是comments
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
    print(f"用户 {user.username} 有 {len(user.posts())} 篇文章")  # 每次访问user.posts()都会触发一个查询
# 总计：101个查询（1 + N）

# 更好的方法（使用预加载）
users = User.with_("posts").all()  # 1个查询获取用户 + 1个查询获取所有相关文章
for user in users:  # 无论有多少用户，都不会有额外查询
    print(f"用户 {user.username} 有 {len(user.posts())} 篇文章")  # 不会有额外查询
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
    _ = user.posts()  # 如果没有预加载，这将触发N个单独的查询
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

## 关联关系预加载的工作原理

理解关联关系预加载的内部工作原理对于有效调试和优化查询至关重要。

### 预加载的本质

预加载（Eager Loading）是一种优化技术，它通过减少数据库查询的数量来提高性能。当您使用`with_()`方法时，ActiveRecord会执行以下步骤：

1. 执行主查询获取父记录（例如用户）
2. 收集所有父记录的主键值
3. 执行单个查询获取所有相关记录（例如所有这些用户的帖子）
4. 在内存中将相关记录与其父记录关联起来

这种方法将查询次数从N+1（1个主查询 + N个关系查询）减少到2（1个主查询 + 1个关系查询）。

### 预加载的实际示例

以下是预加载如何工作的详细示例：

```python
# 不使用预加载（N+1问题）
users = User.where("active = ?", [True]).all()  # 1个查询

# 生成的SQL：
# SELECT * FROM users WHERE active = ?

for user in users:  # 假设返回3个用户
    posts = user.posts()  # 为每个用户执行1个查询
    # 生成的SQL（重复3次，每次使用不同的user.id）：
    # SELECT * FROM posts WHERE user_id = ?

# 总计：4个查询（1 + 3）

# 使用预加载
users = User.where("active = ?", [True]).with_("posts").all()  # 2个查询

# 生成的SQL：
# 查询1：SELECT * FROM users WHERE active = ?
# 查询2：SELECT * FROM posts WHERE user_id IN (1, 2, 3)  # 假设用户ID是1、2和3

for user in users:
    posts = user.posts()  # 不执行额外查询，使用已加载的数据

# 总计：2个查询
```

### 嵌套预加载的工作原理

嵌套预加载（例如`with_("posts.comments")`）以类似的方式工作，但会执行额外的查询来加载嵌套关系：

```python
users = User.where("active = ?", [True]).with_("posts.comments").all()  # 3个查询

# 生成的SQL：
# 查询1：SELECT * FROM users WHERE active = ?
# 查询2：SELECT * FROM posts WHERE user_id IN (1, 2, 3)
# 查询3：SELECT * FROM comments WHERE post_id IN (101, 102, 103, ...)  # 假设帖子ID是101、102、103等
```

### 条件预加载

您可以使用查询修饰符来限制预加载的记录：

```python
# 只预加载已发布的帖子
users = User.with_(("posts", lambda q: q.where("published = ?", [True]))).all()

# 生成的SQL：
# 查询1：SELECT * FROM users
# 查询2：SELECT * FROM posts WHERE user_id IN (1, 2, 3) AND published = ?
```

### 关系查询方法

除了直接访问关系（如`user.posts()`）外，您还可以使用关系查询方法（如`user.posts_query()`）来进一步自定义关系查询：

```python
# 获取用户
user = User.find_one(1)

# 使用关系查询方法
posts_query = user.posts_query()  # 返回一个查询对象，尚未执行

# 自定义查询
recent_posts = posts_query.where("created_at > ?", [一周前的日期]).order_by("created_at DESC").limit(5).all()
```

这种方法允许您在关系的基础上应用额外的过滤、排序和限制，而不需要加载所有相关记录。

## 大数据量查询的分页处理

处理大量数据时，分页是一种重要的优化技术。以下是在ActiveRecord中实现分页的几种方法：

### 基本分页

使用`limit`和`offset`进行基本分页：

```python
# 获取第2页，每页10条记录
page = 2
per_page = 10
offset = (page - 1) * per_page

users = User.order_by("created_at DESC").limit(per_page).offset(offset).all()
```

### 关系查询的分页

对关系查询也可以应用分页：

```python
# 获取用户
user = User.find_one(1)

# 分页获取用户的帖子
page = 2
per_page = 10
offset = (page - 1) * per_page

posts = user.posts_query().order_by("created_at DESC").limit(per_page).offset(offset).all()
```

### 预加载与分页的结合

当使用预加载时，您可能需要限制预加载的相关记录数量：

```python
# 获取用户并预加载其最新的5篇帖子
users = User.with_(("posts", lambda q: q.order_by("created_at DESC").limit(5))).all()

# 现在每个用户最多有5篇最新帖子被预加载
for user in users:
    recent_posts = user.posts()  # 包含最多5篇最新帖子
```

### 游标分页

对于非常大的数据集，基于游标的分页通常比基于偏移的分页更高效：

```python
# 初始查询（第一页）
first_page = User.order_by("id ASC").limit(10).all()

# 如果有结果，获取最后一个ID作为游标
if first_page:
    last_id = first_page[-1].id
    
    # 获取下一页（使用游标）
    next_page = User.where("id > ?", [last_id]).order_by("id ASC").limit(10).all()
```

### 计算总记录数

为了实现分页UI，您通常需要知道总记录数：

```python
# 获取总记录数
total_count = User.count()

# 计算总页数
per_page = 10
total_pages = (total_count + per_page - 1) // per_page  # 向上取整

print(f"总记录数: {total_count}, 总页数: {total_pages}")
```

### 分页性能优化

1. **添加适当的索引**：确保排序和过滤条件使用的列上有索引
2. **避免大偏移**：对于大数据集，避免使用大的`offset`值，考虑使用基于游标的分页
3. **限制预加载的数据量**：使用条件预加载限制每个关系加载的记录数
4. **使用计数缓存**：对于频繁的计数查询，考虑缓存总记录数

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

## 总结

有效的调试是开发高质量ActiveRecord应用程序的关键。通过使用本指南中描述的技术，您可以更轻松地识别和解决常见问题，包括：

- 使用日志和`explain()`方法了解查询执行
- 通过预加载解决N+1查询问题
- 使用关系查询方法自定义关系查询
- 实现有效的分页策略处理大数据量
- 利用Python调试工具进行深入调试

记住，良好的调试实践不仅有助于解决问题，还能帮助您编写更高效、更可维护的代码。