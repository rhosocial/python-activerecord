# 模型最佳实践 (Best Practices)

本文档总结在使用 `rhosocial-activerecord` 定义模型时的最佳实践，帮助你写出更健壮、易维护的代码。

> 💡 **AI 提示词：** "如何设计一个好的 ActiveRecord 模型？有哪些最佳实践？"

---

## 1. 模型命名约定

一致的命名规范可以大幅提升代码的可读性和可维护性。

### 类名：单数 PascalCase

```python
# ✅ 正确：类名使用单数形式，PascalCase
class User(ActiveRecord):
    pass

class OrderItem(ActiveRecord):
    pass

class BlogPost(ActiveRecord):
    pass

# ❌ 错误：避免复数形式
class Users(ActiveRecord):  # 不要这样
    pass

# ❌ 错误：避免 snake_case
class blog_post(ActiveRecord):  # 不要这样
    pass
```

### 表名：复数 snake_case

```python
class User(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return "users"  # ✅ 复数形式

class OrderItem(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return "order_items"  # ✅ 复数 + snake_case
```

### 约定速查表

| 项目 | 命名规范 | 示例 |
|-----|---------|------|
| 模型类名 | PascalCase, 单数 | `User`, `OrderItem` |
| 表名 | snake_case, 复数 | `users`, `order_items` |
| 字段名 | snake_case | `first_name`, `created_at` |
| 外键字段 | `<关联表名>_id` | `user_id`, `order_id` |
| 布尔字段 | `is_<形容词>` 或 `has_<名词>` | `is_active`, `is_deleted`, `has_paid` |
| 时间戳 | `created_at`, `updated_at` | 使用 TimestampMixin 自动生成 |

> 💡 **AI 提示词：** "ActiveRecord 模型命名规范有哪些？"

---

## 2. 字段设计原则

### 2.1 何时使用 Optional

```python
from typing import Optional

class User(ActiveRecord):
    # ✅ 必须有值：用户名必须提供
    username: str
    
    # ✅ Optional：邮箱可以不填，或者之后验证
    email: Optional[str] = None
    
    # ✅ Optional：用户可能还没有上传头像
    avatar_url: Optional[str] = None
    
    # ✅ 有默认值：用户创建时自动激活
    is_active: bool = True
    
    # ✅ 有默认值：创建时自动填充
    created_at: Optional[datetime] = None
```

**决策原则：**

| 场景 | 推荐做法 | 示例 |
|-----|---------|------|
| 数据库必填且无默认值 | `field: type` | `username: str` |
| 数据库必填但有默认值 | `field: type = default` | `is_active: bool = True` |
| 数据库可空 | `field: Optional[type] = None` | `email: Optional[str] = None` |
| 由数据库自动生成 | `field: Optional[type] = None` | `id: Optional[int] = None` |

### 2.2 默认值策略

```python
from datetime import datetime
from pydantic import Field

class Post(ActiveRecord):
    # ✅ 使用 Python 默认值（静态值）
    status: str = "draft"
    view_count: int = 0
    is_published: bool = False
    
    # ✅ 使用 Field 默认值工厂（动态值）
    created_at: datetime = Field(default_factory=datetime.now)
    
    # ✅ 使用 Mixin 自动处理（推荐）
    # 继承 TimestampMixin 自动管理 created_at 和 updated_at
```

**推荐使用 Mixin 处理常见字段：**

```python
from rhosocial.activerecord.field import TimestampMixin, UUIDMixin, SoftDeleteMixin

class Post(UUIDMixin, TimestampMixin, SoftDeleteMixin, ActiveRecord):
    """
    自动获得：
    - id: UUID 主键（来自 UUIDMixin）
    - created_at: 创建时间（来自 TimestampMixin）
    - updated_at: 更新时间（来自 TimestampMixin）
    - deleted_at: 软删除标记（来自 SoftDeleteMixin）
    """
    title: str
    content: str
```

### 2.3 验证规则设计

```python
from pydantic import Field, EmailStr

class User(ActiveRecord):
    # ✅ 基础验证：长度限制
    username: str = Field(..., min_length=3, max_length=50)
    
    # ✅ 格式验证：使用 Pydantic 内置类型
    email: EmailStr  # 自动验证邮箱格式
    
    # ✅ 数值验证：范围限制
    age: int = Field(..., ge=0, le=150)  # 0-150 岁
    
    # ✅ 正则验证：自定义格式
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")  # 中国手机号
```

> 💡 **AI 提示词：** "Pydantic Field 有哪些常用的验证参数？"

---

## 3. 大型项目模型组织

当项目变大时，合理的组织方式至关重要。

### 3.1 按模块组织

```
my_project/
├── models/
│   ├── __init__.py
│   ├── base.py          # 基础模型配置
│   ├── user/
│   │   ├── __init__.py
│   │   ├── models.py    # User, UserProfile
│   │   └── queries.py   # 用户相关查询类
│   ├── order/
│   │   ├── __init__.py
│   │   ├── models.py    # Order, OrderItem
│   │   └── queries.py
│   └── product/
│       ├── __init__.py
│       └── models.py    # Product, Category
```

**models/base.py:**

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from typing import ClassVar

# 配置基础后端
_base_backend = None

def get_backend():
    global _base_backend
    if _base_backend is None:
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
        config = SQLiteConnectionConfig(database='app.db')
        _base_backend = SQLiteBackend(config)
    return _base_backend

class BaseModel(ActiveRecord):
    """项目基础模型类。"""
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @classmethod
    def configure_backend(cls):
        """配置后端（在应用启动时调用）。"""
        if not hasattr(cls, '_backend_configured'):
            cls.configure(get_backend())
            cls._backend_configured = True
```

**models/user/models.py:**

```python
from typing import Optional
from pydantic import Field
from ..base import BaseModel

class User(BaseModel):
    """用户模型。"""
    
    id: Optional[int] = None
    username: str = Field(..., max_length=50)
    email: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'

class UserProfile(BaseModel):
    """用户资料模型。"""
    
    id: Optional[int] = None
    user_id: int
    bio: Optional[str] = None
    avatar: Optional[str] = None
    
    @classmethod
    def table_name(cls) -> str:
        return 'user_profiles'
```

### 3.2 按领域组织（DDD 风格）

```
my_project/
├── domains/
│   ├── user/
│   │   ├── __init__.py
│   │   ├── models.py      # User 模型
│   │   ├── repository.py  # 数据访问层
│   │   └── services.py    # 业务逻辑
│   └── order/
│       ├── __init__.py
│       ├── models.py      # Order, OrderItem
│       └── services.py
```

### 3.3 查询类组织

将复杂查询封装在专门的查询类中：

```python
# models/user/queries.py
from rhosocial.activerecord.query import ActiveQuery
from datetime import datetime, timedelta

class UserQuery(ActiveQuery):
    """用户专用查询类。"""
    
    def active(self):
        """只查询活跃用户。"""
        return self.where(self.model_class.c.is_active == True)
    
    def recently_joined(self, days: int = 30):
        """查询最近注册的用户。"""
        cutoff = datetime.now() - timedelta(days=days)
        return self.where(self.model_class.c.created_at >= cutoff)
    
    def with_email(self):
        """只查询有邮箱的用户。"""
        return self.where(self.model_class.c.email.is_not(None))

# models/user/models.py
class User(BaseModel):
    __query_class__ = UserQuery  # 绑定自定义查询类
    # ... 字段定义

# 使用
recent_active_users = User.query().active().recently_joined(7).all()
```

> 💡 **AI 提示词：** "大型项目中如何组织 ActiveRecord 模型？"

---

## 4. 版本控制策略

### 4.1 模型变更与数据库迁移

当模型发生变化时，需要同步更新数据库结构。

**基本原则：**

1. **永远不要直接修改已发布模型的字段类型**（可能导致数据丢失）
2. **添加新字段时使用默认值或允许为空**
3. **删除字段前先确认数据已备份或迁移**
4. **重命名字段时分两步：添加新字段 → 复制数据 → 删除旧字段**

```python
# ✅ 安全：添加可选字段
class User(ActiveRecord):
    # 新字段，允许为空，现有用户将使用 None
    phone_number: Optional[str] = None
    
    # 新字段，有默认值
    is_vip: bool = False
```

### 4.2 使用 Alembic 进行迁移

虽然 `rhosocial-activerecord` 本身不提供迁移工具，但你可以使用 Alembic。

**alembic/env.py 配置：**

```python
# 从模型生成迁移脚本
from myapp.models import User, Order, Product

target_metadata = ActiveRecord.metadata

def run_migrations_offline() -> None:
    # ... 标准 Alembic 配置
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
```

**迁移工作流：**

```bash
# 1. 修改模型代码
# 2. 生成迁移脚本
alembic revision --autogenerate -m "Add user phone_number"

# 3. 检查生成的脚本，确保正确
# 4. 执行迁移
alembic upgrade head
```

### 4.3 向后兼容性

当进行破坏性变更时，保持向后兼容：

```python
class User(ActiveRecord):
    # 旧字段（标记为废弃，但仍保留）
    name: Optional[str] = None  # 废弃，使用 first_name + last_name
    
    # 新字段
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        """兼容旧代码。"""
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return self.name or ""  # 兼容旧数据
```

> 💡 **AI 提示词：** "如何安全地进行 ActiveRecord 模型变更和数据库迁移？"

---

## 5. 性能优化：何时加索引

索引可以大幅提升查询性能，但也会增加写入开销和存储空间。

### 5.1 应该加索引的场景

```python
# ✅ 外键字段（JOIN 查询）
class Order(ActiveRecord):
    user_id: int  # 应该索引：经常 JOIN users 表

# ✅ 经常用于 WHERE 条件的字段
class User(ActiveRecord):
    email: str    # 应该索引：经常按邮箱查询
    username: str # 应该索引：经常按用户名查询

# ✅ 经常用于排序的字段
class Post(ActiveRecord):
    created_at: datetime  # 应该索引：经常 ORDER BY created_at
    published_at: Optional[datetime]  # 应该索引：经常按发布时间排序
```

### 5.2 不应该加索引的场景

```python
# ❌ 很少查询的字段
class User(ActiveRecord):
    bio: Optional[str] = None  # 很少按 bio 查询，不加索引

# ❌ 区分度很低的字段（如布尔值）
class User(ActiveRecord):
    is_active: bool = True  # 大部分用户都是 True，区分度低，不加索引

# ❌ 经常变更的字段
class Product(ActiveRecord):
    view_count: int = 0  # 频繁更新，索引会影响性能
```

### 5.3 复合索引

当多个字段经常一起用于查询时，使用复合索引：

```sql
-- 经常查询：WHERE status = 'active' AND category_id = 5
CREATE INDEX idx_products_status_category ON products(status, category_id);

-- 经常查询：WHERE user_id = 1 ORDER BY created_at DESC
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC);
```

**复合索引字段顺序原则：**
1. **等值查询字段在前**（`=` 或 `IN`）
2. **排序字段在后**
3. **范围查询字段在最后**（`>`, `<`, `BETWEEN`）

### 5.4 索引最佳实践

```python
class User(ActiveRecord):
    """用户模型 - 索引示例。"""
    
    # 主键自动有索引
    id: Optional[int] = None
    
    # ✅ 唯一索引：邮箱必须唯一
    email: str
    # SQL: CREATE UNIQUE INDEX idx_users_email ON users(email);
    
    # ✅ 普通索引：经常按用户名查询
    username: str
    # SQL: CREATE INDEX idx_users_username ON users(username);
    
    # ✅ 复合索引：经常按状态+注册时间查询
    is_active: bool = True
    created_at: datetime
    # SQL: CREATE INDEX idx_users_active_created ON users(is_active, created_at);
    
    # ❌ 不需要索引：很少查询
    bio: Optional[str] = None
```

### 5.5 使用 EXPLAIN 分析查询

```python
# 查看查询计划
query = User.query().where(User.c.email == 'alice@example.com')
sql, params = query.to_sql()
print(f"SQL: {sql}")

# 在数据库客户端中执行：
# EXPLAIN QUERY PLAN SELECT * FROM users WHERE email = 'alice@example.com';
```

**理想的查询计划：**
- `SEARCH TABLE users USING INDEX idx_users_email (email=?)`

**需要优化的查询计划：**
- `SCAN TABLE users` （全表扫描，慢！）

### 5.6 性能优化检查清单

- [ ] 所有外键字段都有索引
- [ ] 经常查询的字段有索引
- [ ] 经常排序的字段有索引
- [ ] 避免在低区分度字段上建索引
- [ ] 避免在频繁更新的字段上建索引
- [ ] 定期使用 `EXPLAIN` 检查慢查询
- [ ] 定期使用 `VACUUM` (SQLite) 或 `OPTIMIZE TABLE` (MySQL) 维护数据库

> 💡 **AI 提示词：** "数据库索引什么时候该加？什么时候不该加？"

---

## 6. 安全最佳实践

### 6.1 防止 SQL 注入

```python
# ✅ 安全：使用参数化查询
users = User.query().where(User.c.email == user_input).all()

# ✅ 安全：使用 FieldProxy
User.query().where(User.c.status == 'active')

# ❌ 危险：直接拼接 SQL
# User.query().where(f"email = '{user_input}'")  # 永远不要这样做！
```

### 6.2 敏感数据处理

```python
from pydantic import Field

class User(ActiveRecord):
    # ✅ 密码永远要哈希存储
    password_hash: str
    
    # 不提供 password 字段，而是提供设置方法
    def set_password(self, plain_password: str):
        import bcrypt
        self.password_hash = bcrypt.hashpw(
            plain_password.encode(), 
            bcrypt.gensalt()
        ).decode()
    
    def check_password(self, plain_password: str) -> bool:
        import bcrypt
        return bcrypt.checkpw(
            plain_password.encode(), 
            self.password_hash.encode()
        )
```

### 6.3 数据验证

```python
from pydantic import Field, validator

class User(ActiveRecord):
    email: str
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()  # 统一转为小写
```

> 💡 **AI 提示词：** "ActiveRecord 模型安全最佳实践有哪些？"

---

## 7. 总结

好的模型设计应该：

✅ **命名清晰**：类名单数 PascalCase，表名复数 snake_case  
✅ **类型明确**：合理使用 Optional，区分必填/可选字段  
✅ **验证充分**：利用 Pydantic Field 进行数据验证  
✅ **组织有序**：大型项目按模块或领域组织  
✅ **版本可控**：使用 Alembic 管理数据库迁移  
✅ **性能优化**：在合适的字段上添加索引  
✅ **安全处理**：防止 SQL 注入，敏感数据加密存储  

---

## 另请参阅

- [字段定义](fields.md) — 深入了解 FieldProxy 和字段类型
- [Mixins](mixins.md) — 复用常见字段和行为
- [验证与生命周期](validation.md) — Pydantic 验证和模型钩子
- [查询速查表](../querying/cheatsheet.md) — 高效查询技巧
