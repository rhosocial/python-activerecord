# 常见问题解答

本指南解答了您在开始使用rhosocial ActiveRecord时可能遇到的常见问题和问题。

## 一般问题

### ActiveRecord与其他ORM有什么区别？

rhosocial ActiveRecord遵循ActiveRecord模式，将数据访问和业务逻辑合并在一个对象中。这与其他ORM（如SQLAlchemy）不同，后者通常将这些关注点分开。主要区别包括：

- **与Pydantic集成**：rhosocial ActiveRecord利用Pydantic进行类型验证和转换
- **更简单的API**：设计为直观且需要更少的样板代码
- **流畅的查询接口**：提供可链接的API来构建复杂查询
- **内置SQLite支持**：开箱即用，支持SQLite

有关详细比较，请参阅[ORM比较](../1.introduction)文档。

### 我可以将ActiveRecord用于现有数据库吗？

是的，rhosocial ActiveRecord可以与现有数据库一起使用。只需定义与现有表结构匹配的模型即可。如果您的表已经存在，则不需要使用`create_table`方法。

## 安装和设置

### 为什么我收到"SQLite版本太旧"的错误？

rhosocial ActiveRecord需要SQLite 3.25或更高版本，因为它使用了窗口函数和其他现代SQL功能。您可以使用以下命令检查SQLite版本：

```python
import sqlite3
print(sqlite3.sqlite_version)
```

如果您的版本太旧，您可能需要：
- 更新您的Python安装
- 安装更新版本的SQLite并重新编译Python的sqlite3模块
- 使用不同的数据库后端

### 如何连接到多个数据库？

您可以配置不同的模型使用不同的数据库连接：

```python
# 配置User模型使用一个数据库
User.configure(
    ConnectionConfig(database='users.sqlite3'),
    backend_class=SQLiteBackend
)

# 配置Product模型使用另一个数据库
Product.configure(
    ConnectionConfig(database='products.sqlite3'),
    backend_class=SQLiteBackend
)
```

## 模型定义

### 如何定义主键？

默认情况下，rhosocial ActiveRecord使用名为`id`的字段作为主键。您可以通过设置`__primary_key__`属性来自定义这一点：

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    __primary_key__ = 'user_id'  # 自定义主键字段
    
    user_id: int
    name: str
```

### 如何处理自动递增字段？

对于SQLite，整数主键自动递增。对于其他字段类型或数据库，您可能需要使用特定的字段类型或数据库功能。

### 我可以使用UUID主键吗？

是的，rhosocial ActiveRecord通过`UUIDField`混入支持UUID主键：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field.uuid import UUIDField
from uuid import UUID

class User(UUIDField, ActiveRecord):
    __table_name__ = 'users'
    
    id: UUID  # UUID主键
    name: str
```

## 数据库操作

### 如何执行原始SQL查询？

您可以通过模型类的`.backend()`方法获取数据库后端，然后使用后端的`.execute()`方法执行原始SQL查询：

```python
# 获取数据库后端
backend = User.backend()

# 执行SELECT查询并获取结果
result = backend.execute(
    "SELECT * FROM users WHERE age > ?", 
    params=(18,),
    returning=True,  # 或使用 ReturningOptions.all_columns()
    column_types=None  # 可选：指定列类型映射
)

# 处理查询结果
if result and result.data:
    for row in result.data:
        print(row)  # 每行数据以字典形式返回

# 执行INSERT/UPDATE/DELETE操作
result = backend.execute(
    "UPDATE users SET status = 'active' WHERE last_login > date('now', '-30 days')"
)
print(f"受影响的行数: {result.affected_rows}")

# 使用便捷方法获取单条记录
user = backend.fetch_one("SELECT * FROM users WHERE id = ?", params=(1,))

# 获取多条记录
users = backend.fetch_all("SELECT * FROM users WHERE status = ?", params=('active',))
```

`execute()`方法的参数说明：
- `sql`: SQL语句字符串
- `params`: 查询参数（可选），作为元组传递
- `returning`: 控制返回子句行为（可选）
- `column_types`: 结果类型转换的列类型映射（可选）

返回的`QueryResult`对象包含以下属性：
- `data`: 查询结果数据（列表中的字典）
- `affected_rows`: 受影响的行数
- `last_insert_id`: 最后插入的ID（如适用）
- `duration`: 查询执行时间（秒）

### 如何处理数据库迁移？

rhosocial ActiveRecord的核心包中不包含内置的迁移系统。对于简单的架构更改，您可以使用`create_table`、`add_column`等方法。对于更复杂的迁移，请考虑：

1. 使用可选的迁移包：`pip install rhosocial-activerecord[migration]`
2. 使用专用迁移工具，如Alembic
3. 使用SQL脚本手动管理迁移

## 性能

### 如何优化大型数据集的查询？

对于大型数据集，请考虑以下优化技术：

1. **使用分页**：限制一次检索的记录数
   ```python
   users = User.query().limit(100).offset(200).all()
   ```

2. **只选择需要的列**：
   ```python
   users = User.query().select('id', 'name').all()
   ```
   
   **注意**：当选择特定列时，请注意Pydantic验证规则。未标记为可选（`Optional`类型）的字段不能为`None`。如果您选择模型实例化的列子集，请确保包含所有必需字段或使用`to_dict()`绕过模型验证。

3. **使用适当的索引**：确保您的数据库表有适当的索引

4. **使用关系的预加载**：在单个查询中加载相关数据

5. **适当使用字典结果**：当您只需要数据而不需要模型功能时
   ```python
   # 返回字典而不是模型实例
   users = User.query().to_dict().all()
   
   # 对于JOIN查询或当模型验证会失败时
   results = User.query()\
       .join("JOIN orders ON users.id = orders.user_id")\
       .select("users.id", "users.name", "orders.total")\
       .to_dict(direct_dict=True)\
       .all()
   ```

### 如何返回字典结果而不是模型实例？

当您需要原始数据访问而不需要模型验证，或者处理返回未在模型中定义的列的复杂查询时，请使用`to_dict()`方法：

```python
# 标准用法 - 首先实例化模型，然后转换为字典
users = User.query().to_dict().all()

# 对于JOIN查询 - 完全绕过模型实例化
results = User.query()\
    .join("JOIN orders ON users.id = orders.user_id")\
    .select("users.id", "users.name", "orders.total")\
    .to_dict(direct_dict=True)\
    .all()

# 仅包含特定字段
users = User.query().to_dict(include={'id', 'name', 'email'}).all()

# 排除特定字段
users = User.query().to_dict(exclude={'password', 'secret_token'}).all()
```

**重要提示：** `to_dict()`方法只能放在ActiveQuery调用链的最后，且调用后只能执行`all()`、`one()`或`to_sql()`方法。调用`to_dict()`后，返回的对象与原始的ActiveQuery已无关联。

`direct_dict=True`参数在以下情况特别有用：
1. 处理返回模型架构中不存在的列的JOIN查询
2. 需要绕过模型验证
3. 只对数据感兴趣，而不是模型功能

## 故障排除

### 为什么我的更改没有保存到数据库？

常见原因包括：

1. **忘记调用`save()`**：模型属性的更改不会自动保存
2. **事务回滚**：如果事务中发生异常，更改将回滚
3. **验证失败**：如果验证失败，保存操作将中止

检查是否有异常，并确保在进行更改后调用`save()`。

### 如何调试SQL查询？

您可以启用SQL日志记录以查看正在执行的查询：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('rhosocial.activerecord.backend').setLevel(logging.DEBUG)
```

这将打印所有SQL查询到控制台，有助于识别性能问题或错误。

## 下一步

如果您的问题在此处未得到解答，请考虑：

1. 探索完整文档以获取更详细的信息
2. 检查项目的GitHub问题，查找类似问题
3. 加入社区讨论论坛
4. 通过改进文档或报告错误来为项目做贡献