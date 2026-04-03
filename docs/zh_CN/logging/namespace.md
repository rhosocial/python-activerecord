# 日志命名空间

> 💡 **AI 提示**: "为什么 ActiveRecord 使用层次化的日志命名空间？有什么好处？"

日志系统采用独立的语义化层次命名空间，与代码模块路径不完全对应，仅用于日志分类和控制：

```text
rhosocial.activerecord                           # 根日志器
├── rhosocial.activerecord.model                 # 模型层
│   └── rhosocial.activerecord.model.{ClassName} # 库内置具体模型类
├── rhosocial.activerecord.backend               # 后端层
│   ├── rhosocial.activerecord.backend.sqlite    # SQLite 后端
│   └── rhosocial.activerecord.backend.mysql     # MySQL 后端
├── rhosocial.activerecord.query                 # 查询层
│   ├── rhosocial.activerecord.query.ActiveQuery
│   ├── rhosocial.activerecord.query.CTEQuery
│   └── rhosocial.activerecord.query.SetOperationQuery
└── rhosocial.activerecord.transaction           # 事务层
```

## 用户自定义类

用户自定义的 Model 类使用其模块命名空间，不放入库命名空间：

```python
# myapp/models.py
class User(ActiveRecord):
    pass
# 日志器：myapp.models.User
```

也可通过 `__logger_name__` 显式指定：

```python
class Article(ActiveRecord):
    __logger_name__ = 'myapp.article'
# 日志器：myapp.article
```

## 层次化命名的优势

### 1. 统一控制

通过父日志器统一控制所有子日志器：

```python
# 一次性调整所有 activerecord 相关日志级别
logging.getLogger('rhosocial.activerecord').setLevel(logging.WARNING)

# 仅调试模型层
logging.getLogger('rhosocial.activerecord.model').setLevel(logging.DEBUG)
```

### 2. 日志传播

子日志器的消息会自动传播到父日志器，只需在根日志器配置 handler，即可捕获所有子日志器的输出。

### 3. 灵活过滤

可在不同层级设置不同的 handler 和 filter：

```python
# 根日志器：输出到控制台
console_handler = logging.StreamHandler()
logging.getLogger('rhosocial.activerecord').addHandler(console_handler)

# 后端日志：额外输出到文件
file_handler = logging.FileHandler('backend.log')
logging.getLogger('rhosocial.activerecord.backend').addHandler(file_handler)
```

### 4. 运行时调整

生产环境中可动态调整特定组件的日志级别：

```python
# 单独开启 User 模型的 DEBUG 日志
logging.getLogger('rhosocial.activerecord.model.User').setLevel(logging.DEBUG)
```

## 与 Python logging 的关系

这种层次化命名符合 Python logging 模块的最佳实践：

- 使用点分隔的名称建立父子关系
- 子日志器自动继承父日志器的配置
- 支持 `propagate` 属性控制日志传播行为

主流 Python 库都采用类似方式：
- SQLAlchemy: `sqlalchemy.engine`, `sqlalchemy.orm`, `sqlalchemy.pool`
- Django: `django.request`, `django.db.backends`
