# rhosocial-activerecord vs Peewee 竞争优势分析

## 概述

Peewee 是一个轻量级的 Python ORM，采用 ActiveRecord 模式，体积小巧。rhosocial-activerecord 同样采用 ActiveRecord 模式，但基于现代 Python 特性（Pydantic、类型注解）构建，提供更好的类型安全和 IDE 支持。

---

## 核心优势

### 1. 类型安全与 Pydantic 集成

**Peewee**:

```python
from peewee import Model, CharField, IntegerField

class User(Model):
    name = CharField(max_length=100)
    age = IntegerField()

user = User.get(User.id == 1)
user.name  # 类型: Any
user.age   # 类型: Any

# 无运行时验证
user = User(name="Alice", age="not a number")  # 不报错，直到数据库操作失败
```

**rhosocial-activerecord**:

```python
from rhosocial.activerecord.model import ActiveRecord
from typing import Optional

class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    name: str = Field(max_length=100)
    age: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()

user = User.query().where(User.c.id == 1).first()
user.name  # 类型: str ✅
user.age   # 类型: int ✅

# 运行时验证
user = User(name="Alice", age="not a number")  # ValidationError
```

**优势分析**:

- **完整类型提示**: IDE 自动补全和类型检查
- **运行时验证**: Pydantic 验证器在数据进入前检查
- **零学习成本**: 熟悉 Pydantic 的开发者可直接上手

---

### 2. 现代异步支持

**Peewee**:

```python
# 异步支持通过 playhouse 扩展
from playhouse.shortcuts import model_to_dict

# 需要单独的异步模型定义
from peewee_async import Manager, MySQLDatabase

database = MySQLDatabase(...)
objects = Manager(database)

# 异步 API 不同
user = await objects.get(User, User.id == 1)
```

**rhosocial-activerecord**:

```python
# 同步
user = User.query().where(User.c.id == 1).first()

# 异步：完全相同的 API
user = await User.query().where(User.c.id == 1).first()
```

**优势分析**:

- **API 一致**: 同步/异步方法名完全相同
- **原生实现**: 非包装层，性能更优
- **无需额外配置**: 同一个模型类支持两种模式

---

### 3. 查询构建器对比

**Peewee**:

```python
# 字段引用使用模型属性
users = User.select().where(User.age >= 18).order_by(User.name)

# 复杂表达式需要特殊语法
from peewee import fn

User.select(User, fn.COUNT(Post.id).alias('post_count')) \
    .join(Post, JOIN.LEFT_OUTER) \
    .group_by(User.id)

# CTE 支持
cte = User.select().where(User.age >= 18).cte('adults')
users = User.select().from_(cte)
```

**rhosocial-activerecord**:

```python
# FieldProxy 提供类型安全的字段引用
users = User.query().where(User.c.age >= 18).order_by(User.c.name)

# 函数调用更自然
User.query().select([
    User.c.id,
    User.c.name,
    func.count(Post.c.id).as_("post_count")
]).join(Post).group_by(User.c.id)

# CTE 通过专门的 CTEQuery
User.query().with_cte("adults", lambda: User.query().where(User.c.age >= 18))

# SQL 透明
sql, params = User.query().where(User.c.age >= 18).to_sql()
```

**优势分析**:

- **类型安全**: `FieldProxy` 提供编译时检查
- **SQL 透明**: `.to_sql()` 随时查看生成的 SQL
- **专用构建器**: CTEQuery、SetOperationQuery 语义清晰

---

### 4. 模型定义对比

**Peewee**:

```python
from peewee import Model, CharField, ForeignKeyField

class BaseModel(Model):
    class Meta:
        database = database

class User(BaseModel):
    name = CharField()

class Post(BaseModel):
    title = CharField()
    author = ForeignKeyField(User, backref='posts')

# 需要显式连接数据库
database.connect()
database.create_tables([User, Post])
```

**rhosocial-activerecord**:

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    name: str

    c: ClassVar[FieldProxy] = FieldProxy()
    posts: ClassVar[HasMany["Post"]] = HasMany(foreign_key="author_id")

class Post(ActiveRecord):
    __table_name__ = "posts"
    id: Optional[int] = None
    title: str
    author_id: int

    c: ClassVar[FieldProxy] = FieldProxy()
    author: ClassVar[BelongsTo["User"]] = BelongsTo(foreign_key="author_id")

# 配置后端
User.configure(config, SQLiteBackend)
```

**优势分析**:

- **关系类型安全**: 关系定义可被 IDE 识别
- **Pydantic 字段**: 原生支持验证器
- **后端配置灵活**: 模型与后端配置分离

---

### 5. 能力声明机制

**Peewee**:

```python
# 需要手动检测数据库特性
from peewee import MySQLDatabase

db = MySQLDatabase(...)
# 无统一的能力声明机制
# 需要查阅文档或运行时检测
```

**rhosocial-activerecord**:

```python
# 后端显式声明能力
@requires_capability(CTECapability.RECURSIVE_CTE)
def test_recursive_cte():
    pass

# 运行时查询
if backend.capabilities.has(WindowFunctionCapability.ROW_NUMBER):
    # 使用窗口函数
    pass
```

**优势分析**:

- **声明式**: 后端明确声明支持的功能
- **测试友好**: 自动跳过不支持的功能
- **文档化**: 能力声明即文档

---

### 6. SQL 表达能力与架构

**Peewee**:

- 自包含实现
- 约 5k 行核心代码
- 轻量但 SQL 表达能力有限

**rhosocial-activerecord**:

- 依赖 Pydantic
- Expression/Dialect 系统可表达所有标准 SQL 和方言特性
- 完整的 SQL 覆盖

**对比表**:

| 方面 | Peewee | rhosocial-activerecord |
|------|--------|------------------------|
| 类型安全 | 部分 | 完整 |
| 运行时验证 | 无 | Pydantic |
| 异步一致性 | 需要扩展 | 原生支持 |
| 字段定义 | Peewee Field | Pydantic Field |
| SQL 标准覆盖 | ⚠️ 有限 | ✅ 完整 |
| 方言特性覆盖 | ⚠️ 有限 | ✅ 完整 |

---

### 7. 后端独立性与可扩展性

**Peewee**:

- 后端与 ORM 层紧密耦合
- 自定义后端需要继承 Peewee 的 Database 类
- 难以脱离 ORM 层独立使用后端功能

**rhosocial-activerecord**:

```python
# 后端完全独立工作
backend = User.__backend__
result = backend.execute("""
    SELECT * FROM users
    WHERE JSON_EXTRACT(metadata, '$.role') = 'admin'
    FOR UPDATE SKIP LOCKED
""", params={}, options=ExecutionOptions(...))

# 自定义后端实现
class MyCustomBackend(StorageBackend):
    """用户可自行实现后端"""
    def _initialize_capabilities(self):
        capabilities = DatabaseCapabilities()
        # 声明支持的功能
        return capabilities

    def connect(self) -> None:
        # 自定义连接逻辑
        pass
```

**优势分析**:

- **后端独立可用**: 后端层可完全独立运行，覆盖完整 SQL 标准和方言特性
- **完全可扩展**: 用户可自行实现后端，接口简洁清晰
- **LLM 辅助开发**: 设计简洁明了，可借助大语言模型快速生成自定义后端

---

## 适用场景对比

| 场景 | rhosocial-activerecord | Peewee |
|------|------------------------|--------|
| 类型安全需求 | ✅ 优势 | ⚠️ 部分 |
| Pydantic 用户 | ✅ 优势 | ❌ 不兼容 |
| 现代异步项目 | ✅ 优势 | ⚠️ 需扩展 |
| 完整 SQL 表达 | ✅ 完整覆盖 | ⚠️ 有限 |
| 极简依赖 | ⚠️ 需要 Pydantic | ✅ 自包含 |
| 成熟稳定 | ⚠️ 发展中 | ✅ 成熟 |

---

## 结论

rhosocial-activerecord 相对于 Peewee 的核心优势：

1. **完整类型安全** — Pydantic 集成，编译时和运行时双重保障
2. **现代异步** — 原生支持，API 完全一致
3. **能力声明** — 显式的功能可用性声明
4. **Pydantic 生态** — 与 FastAPI 等现代框架无缝集成

**适合选择 rhosocial-activerecord 的开发者**:

- 使用 Pydantic 和 FastAPI 的项目
- 需要完整类型安全的团队
- 追求同步/异步 API 一致性
- 需要运行时数据验证

**适合选择 Peewee 的开发者**:

- 追求极简依赖
- 已有 Peewee 项目
- 小型项目
- 偏好自包含的解决方案
