# rhosocial-activerecord vs Tortoise ORM 竞争优势分析

## 概述

Tortoise ORM 是专为异步设计的 Python ORM，灵感来自 Django ORM。它采用 asyncio 原生设计，但同步支持有限。rhosocial-activerecord 提供真正的同步/异步对等，两者都是一等公民。

---

## 核心优势

### 1. 同步/异步对等

**Tortoise ORM**:

```python
# Tortoise 以异步为设计核心
from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)

# 异步是主要 API
async def get_user():
    user = await User.get(id=1)
    return user

# 同步支持需要额外配置
from tortoise import Tortoise
# 同步操作需要使用 run_sync 或其他包装
```

**rhosocial-activerecord**:

```python
# 同步和异步完全对等
# 同步
def get_user():
    user = User.query().where(User.c.id == 1).first()
    return user

# 异步：完全相同的 API
async def get_user():
    user = await User.query().where(User.c.id == 1).first()
    return user
```

**优势分析**:

- **一等公民**: 同步和异步都是原生实现，无主次之分
- **API 一致**: 方法名完全相同，仅通过 `await` 区分
- **迁移简单**: 同步代码改异步只需添加 `await`
- **灵活性**: 同一项目可混用同步/异步模型

---

### 2. 模型定义对比

**Tortoise ORM**:

```python
from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    age = fields.IntField()

    class Meta:
        table = "users"

class Post(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=200)
    author = fields.ForeignKeyField("models.User", related_name="posts")
```

**rhosocial-activerecord**:

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo
from typing import ClassVar, Optional

class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    name: str = Field(max_length=100)
    age: int = 0

    c: ClassVar[FieldProxy] = FieldProxy()
    posts: ClassVar[HasMany["Post"]] = HasMany(foreign_key="author_id")

class Post(ActiveRecord):
    __table_name__ = "posts"
    id: Optional[int] = None
    title: str = Field(max_length=200)
    author_id: int

    c: ClassVar[FieldProxy] = FieldProxy()
    author: ClassVar[BelongsTo["User"]] = BelongsTo(foreign_key="author_id")
```

**优势分析**:

- **Pydantic 原生**: 使用标准 Python 类型注解
- **IDE 友好**: 完整的类型提示和自动补全
- **关系类型安全**: 关系定义可被 IDE 识别

---

### 3. 查询构建器对比

**Tortoise ORM**:

```python
# Django 风格的查询
users = await User.filter(age__gte=18).order_by("-name")

# 复杂查询需要 Q 对象
from tortoise.expressions import Q
users = await User.filter(Q(name__startswith="A") | Q(name__startswith="B"))

# 聚合
from tortoise.functions import Count
users = await User.annotate(post_count=Count("posts")).filter(post_count__gt=0)
```

**rhosocial-activerecord**:

```python
# 链式调用，SQL 风格
users = await User.query().where(User.c.age >= 18).order_by(User.c.name.desc())

# 逻辑组合直观
users = await User.query().where(
    (User.c.name.startswith("A")) | (User.c.name.startswith("B"))
)

# 聚合
users = await User.query().select([
    User.c.id,
    User.c.name,
    func.count(Post.c.id).as_("post_count")
]).join(Post).group_by(User.c.id).having(func.count(Post.c.id) > 0)

# SQL 透明
sql, params = User.query().where(User.c.age >= 18).to_sql()
```

**优势分析**:

- **表达式对象**: 类型安全的查询构建
- **SQL 风格**: 更接近 SQL 思维方式
- **透明度高**: `.to_sql()` 随时查看生成的 SQL

---

### 4. 初始化与配置

**Tortoise ORM**:

```python
from tortoise import Tortoise

# 必须先初始化
await Tortoise.init(
    db_url="sqlite://:memory:",
    modules={"models": ["app.models"]}
)

# 生成表
await Tortoise.generate_schemas()

# 关闭连接
await Tortoise.close_connections()
```

**rhosocial-activerecord**:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# 配置模型
config = SQLiteConnectionConfig(database=":memory:")
User.configure(config, SQLiteBackend)

# 直接使用，无需初始化步骤
user = User(name="Alice")
user.save()

# 断开连接
User.__backend__.disconnect()
```

**优势分析**:

- **即时使用**: 无需初始化步骤
- **模型级配置**: 每个模型可独立配置后端
- **灵活简单**: 不需要模块注册

---

### 5. SQL 表达能力

**Tortoise ORM**:

```python
# CTE 支持有限
# 窗口函数支持有限
# 复杂查询通常需要原生 SQL

# 使用原生 SQL
from tortoise import connections
conn = connections.get("default")
results = await conn.execute_query("SELECT ...")
```

**rhosocial-activerecord**:

```python
# 通过 Expression/Dialect 系统表达所有 SQL
# CTE 通过 CTEQuery
cte_query = CTEQuery().with_cte(
    "adults",
    User.query().where(User.c.age >= 18)
)
results = await User.query().from_cte("adults").all()

# 窗口函数
from rhosocial.activerecord.query.window import Window

users = await User.query().select([
    User.c.id,
    User.c.name,
    func.row_number().over(
        partition_by=[User.c.department],
        order_by=[User.c.salary.desc()]
    ).as_("rank")
]).all()

# Set Operations
union_query = SetOperationQuery().union(
    User.query().where(User.c.age < 18),
    User.query().where(User.c.age > 65)
)
```

**优势分析**:

- **完整 SQL 覆盖**: Expression/Dialect 系统可表达所有标准 SQL 和方言特性
- **CTE 支持**: 专门的 CTEQuery 构建器
- **窗口函数**: 类型安全的窗口函数支持
- **集合操作**: UNION/INTERSECT/EXCEPT 支持
- **能力声明**: 显式声明后端支持的功能

---

### 6. 能力声明机制

**Tortoise ORM**:

```python
# 无统一的能力声明机制
# 后端特性需要手动检测或查阅文档
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

### 7. 类型安全对比

**Tortoise ORM**:

```python
user = await User.get(id=1)
user.name  # 类型提示有限
user.age   # 类型提示有限

# IDE 自动补全不完整
```

**rhosocial-activerecord**:

```python
user = await User.query().where(User.c.id == 1).first()
user.name  # 类型: str ✅
user.age   # 类型: int ✅

# IDE 完整支持
User.query().where(User.c.age >= 18)  # 完整类型提示
```

---

### 8. 后端独立性与可扩展性

**Tortoise ORM**:

- 后端与 ORM 层紧密耦合
- 自定义后端需要继承 Tortoise 的 Database 类
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

| 场景 | rhosocial-activerecord | Tortoise ORM |
|------|------------------------|--------------|
| 纯异步项目 | ✅ 原生支持 | ✅ 设计核心 |
| 纯同步项目 | ✅ 原生支持 | ⚠️ 需包装 |
| 混合同步/异步 | ✅ 完全对等 | ⚠️ 异步优先 |
| Django 用户迁移 | ⚠️ 需适应 | ✅ 类似 Django |
| Pydantic 用户 | ✅ 优势 | ⚠️ 不同体系 |
| 完整 SQL 表达 | ✅ 完整覆盖 | ⚠️ 原生 SQL |
| CTE/窗口函数 | ✅ 完整支持 | ⚠️ 有限 |

---

## 结论

rhosocial-activerecord 相对于 Tortoise ORM 的核心优势：

1. **同步/异步对等** — 两者都是一等公民，API 完全一致
2. **Pydantic 集成** — 类型安全和运行时验证
3. **完整 SQL 表达** — CTE、窗口函数、集合操作支持
4. **能力声明** — 显式的功能可用性声明

**适合选择 rhosocial-activerecord 的开发者**:

- 需要同步和异步混合使用
- 使用 Pydantic 和 FastAPI 的项目
- 需要完整 SQL 表达能力（CTE、窗口函数）
- 追求类型安全和 IDE 友好

**适合选择 Tortoise ORM 的开发者**:

- 纯异步项目
- 从 Django ORM 迁移
- 偏好 Django 风格的 API
- 不需要复杂 SQL 功能
