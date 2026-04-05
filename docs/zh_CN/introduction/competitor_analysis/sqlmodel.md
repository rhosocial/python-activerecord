# rhosocial-activerecord vs SQLModel 竞争优势分析

## 概述

SQLModel 由 FastAPI 作者 tiangolo 创建，基于 Pydantic 和 SQLAlchemy 构建，目标是简化 SQL 数据库操作。rhosocial-activerecord 同样基于 Pydantic，但从零构建，提供更纯粹的 ActiveRecord 体验。

---

## 核心优势

### 1. 纯粹的 ActiveRecord 模式

**SQLModel (混合模式)**:

```python
# SQLModel 本质是 SQLAlchemy + Pydantic 的包装
# 仍然保留了 SQLAlchemy 的 Session 概念
from sqlmodel import Session, select

with Session(engine) as session:
    user = User(name="Alice")
    session.add(user)
    session.commit()

    # 查询使用 SQLAlchemy 风格
    statement = select(User).where(User.name == "Alice")
    user = session.exec(statement).first()
```

**rhosocial-activerecord (纯 ActiveRecord)**:

```python
# 纯粹的 ActiveRecord 风格
user = User(name="Alice")
user.save()  # 直接保存，无需 Session

# 查询直接从模型开始
user = User.query().where(User.c.name == "Alice").first()
```

**优势分析**:

- **无 Session**: 不需要理解 Session 生命周期
- **直接操作**: 模型实例直接 `save()`/`delete()`
- **心智模型简单**: 一行记录 = 一个模型实例

---

### 2. 从零构建 vs 包装层

**SQLModel 架构**:

```
你的代码 → SQLModel API → SQLAlchemy ORM → SQLAlchemy Core → 数据库驱动 → 数据库
```

**rhosocial-activerecord 架构**:

```
你的代码 → rhosocial-activerecord → 数据库驱动 → 数据库
```

**优势分析**:

- **单层抽象**: 没有中间包装层，行为可预测
- **调用栈浅**: 调试时更容易定位问题
- **无隐藏行为**: 没有 SQLAlchemy 的隐式状态管理

---

### 3. 同步/异步架构

**SQLModel**:

```python
# 同步使用 SQLAlchemy Session
from sqlmodel import Session
with Session(engine) as session:
    user = session.exec(select(User)).first()

# 异步使用 SQLAlchemy AsyncSession
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

async with AsyncSession(async_engine) as session:
    result = await session.exec(select(User))
    user = result.first()
```

**rhosocial-activerecord**:

```python
# 同步
user = User.query().where(User.c.id == 1).first()

# 异步：完全相同的 API
user = await User.query().where(User.c.id == 1).first()
```

**优势分析**:

- **API 完全一致**: 方法签名完全相同
- **无会话概念**: 不需要区分 Session/AsyncSession
- **原生实现**: 同步和异步都是原生实现

---

### 4. 查询构建器对比

**SQLModel**:

```python
# 使用 SQLAlchemy 风格的 select
from sqlmodel import select

statement = select(User).where(User.age >= 18).order_by(User.name)
users = session.exec(statement).all()

# 复杂查询需要了解 SQLAlchemy
from sqlalchemy import func, and_, or_
statement = select(
    User,
    func.count(Post.id).label("post_count")
).join(Post).group_by(User.id)
```

**rhosocial-activerecord**:

```python
# 链式调用，SQL 风格
users = User.query().where(User.c.age >= 18).order_by(User.c.name).all()

# 类型安全的表达式
User.query().select([
    User.c.id,
    User.c.name,
    func.count(Post.c.id).as_("post_count")
]).join(Post).group_by(User.c.id)

# CTE 支持
User.query().with_cte("adults", lambda: User.query().where(User.c.age >= 18))
```

**优势分析**:

- **链式查询**: 更接近 SQL 的思维方式
- **类型安全**: 表达式对象提供编译时检查
- **CTE/窗口函数**: 专门的 CTEQuery 构建 CTE

---

### 5. 模型定义对比

**SQLModel**:

```python
from sqlmodel import SQLModel, Field
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)

    # 关系需要单独定义
    posts: list["Post"] = Relationship(back_populates="author")

class Post(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    author_id: int = Field(foreign_key="user.id")
    author: Optional["User"] = Relationship(back_populates="posts")
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

    c: ClassVar[FieldProxy] = FieldProxy()
    posts: ClassVar[HasMany["Post"]] = HasMany(foreign_key="author_id")

class Post(ActiveRecord):
    __table_name__ = "posts"
    id: Optional[int] = None
    title: str
    author_id: int

    c: ClassVar[FieldProxy] = FieldProxy()
    author: ClassVar[BelongsTo["User"]] = BelongsTo(foreign_key="author_id")
```

**优势分析**:

- **关系定义清晰**: 使用 `ClassVar` 避免字段混淆
- **字段代理**: `FieldProxy` 提供类型安全的字段引用
- **预加载支持**: `with_()` 方法支持预加载

---

### 6. 能力声明机制

**SQLModel**:

```python
# 依赖 SQLAlchemy 的方言系统
# 功能可用性需要手动检测
if engine.dialect.name == "mysql":
    # MySQL 特定操作
    pass
```

**rhosocial-activerecord**:

```python
# 显式的能力声明
@requires_capability(CTECapability.RECURSIVE_CTE)
def test_recursive_cte():
    pass

# 运行时能力查询
if backend.capabilities.has(WindowFunctionCapability.ROW_NUMBER):
    User.query().select([...], window=Window(...))
```

**优势分析**:

- **声明式**: 后端明确声明支持的功能
- **自动跳过**: 测试框架自动处理不支持的功能
- **文档化**: 能力声明即文档

---

### 7. 后端独立性与可扩展性

**SQLModel**:

- 后端层与 SQLAlchemy 紧密耦合
- 自定义后端需要深入理解 SQLAlchemy 方言系统
- 难以脱离 SQLAlchemy 独立使用后端功能

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

## 补充对比

### 8. FastAPI 集成

**SQLModel**:

```python
# 原生支持 FastAPI 依赖注入
from fastapi import Depends
from sqlmodel import Session

def get_session():
    with Session(engine) as session:
        yield session

@app.post("/users/")
def create_user(user: User, session: Session = Depends(get_session)):
    session.add(user)
    session.commit()
    return user
```

**rhosocial-activerecord**:

```python
# 直接使用，无需依赖注入
@app.post("/users/")
def create_user(user: UserCreate):
    db_user = User(**user.dict())
    db_user.save()
    return db_user

# 异步版本
@app.post("/users/")
async def create_user(user: UserCreate):
    db_user = User(**user.dict())
    await db_user.save()
    return db_user
```

**优势分析**:

- **更简单**: 无需会话依赖注入
- **一致性强**: 同步/异步 API 完全相同

---

### 9. SQL 表达能力对比

| 方面 | SQLModel | rhosocial-activerecord |
|------|----------|------------------------|
| 底层引擎 | SQLAlchemy (成熟) | 自研 Expression/Dialect 系统 |
| SQL 标准覆盖 | ✅ 完整 (via SQLAlchemy) | ✅ 完整 |
| 方言特性覆盖 | ✅ 完整 | ✅ 完整 |
| 社区规模 | 中等 | 小 |
| 生产验证 | 有案例 | 开发中 |

**rhosocial-activerecord 的 Expression/Dialect 架构**:

- 后端致力于完整覆盖 SQL 标准和各方言特性
- 通过 Expression 对象表达任意 SQL 结构
- 通过 Dialect 层处理各数据库的 SQL 差异
- 能够表达所有标准 SQL 及方言特有功能

---

## 适用场景对比

| 场景 | rhosocial-activerecord | SQLModel |
|------|------------------------|----------|
| 纯 ActiveRecord 需求 | ✅ 优势 | ⚠️ 混合模式 |
| 无 Session 概念需求 | ✅ 优势 | ❌ 需要 Session |
| 完整 SQL 表达 | ✅ 完整覆盖 | ✅ 完整覆盖 |
| FastAPI 项目 | ✅ 简洁 | ✅ 原生集成 |
| 已有 SQLAlchemy 经验 | ⚠️ 新概念 | ✅ 熟悉的模式 |
| 需要 Alembic 迁移 | ⚠️ 需配置 | ✅ 直接集成 |

---

## 结论

rhosocial-activerecord 相对于 SQLModel 的核心优势：

1. **纯粹 ActiveRecord** — 无 Session 概念，更直观
2. **从零构建** — 单层抽象，无隐藏复杂性
3. **API 一致** — 同步/异步完全相同的 API
4. **能力声明** — 显式的功能可用性声明

**适合选择 rhosocial-activerecord 的开发者**:

- 偏好 ActiveRecord 模式
- 不想学习 SQLAlchemy 概念
- 追求同步/异步 API 一致性
- 需要类型安全的查询构建

**适合选择 SQLModel 的开发者**:

- 已熟悉 SQLAlchemy
- 需要 SQLAlchemy 的全部功能
- 需要成熟的迁移工具支持
- 项目需要成熟的生产验证
