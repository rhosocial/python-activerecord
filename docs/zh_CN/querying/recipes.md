# 复杂查询实战 (Query Recipes)

本文档提供常见业务场景的查询解决方案，展示 rhosocial-activerecord 的最佳实践。

> 💡 **核心原则**：
> 1. **使用表达式系统**：rhosocial-activerecord 的表达式系统覆盖完整的 SQL 标准，无需手写 SQL
> 2. **自定义查询类**：对于常用查询，继承 `ActiveQuery` 创建专用查询类，在模型中通过 `__query_class__` 指定
> 3. **CTEQuery 用于复杂查询**：需要使用 CTE (公用表表达式) 时，使用 `CTEQuery` 类独立构建查询

---

## 最佳实践：自定义查询类

当某个查询模式在你的应用中被频繁使用时，最佳做法是创建一个自定义查询类：

```python
from typing import ClassVar, Optional, List
from datetime import datetime, timedelta
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.query import ActiveQuery
from rhosocial.activerecord.base import FieldProxy
from pydantic import Field

class UserQuery(ActiveQuery):
    """User 模型的专用查询类，封装常用查询逻辑。"""
    
    def recent(self, days: int = 7) -> 'UserQuery':
        """查询最近 N 天注册的用户。"""
        cutoff_date = datetime.now() - timedelta(days=days)
        return self.where(self.model_class.c.created_at >= cutoff_date)
    
    def active(self) -> 'UserQuery':
        """查询活跃用户（已验证邮箱且未禁用）。"""
        return self.where(
            (self.model_class.c.email_verified == True) & 
            (self.model_class.c.is_banned == False)
        )


class User(ActiveRecord):
    """User 模型，使用自定义查询类。"""
    
    # 指定自定义查询类
    __query_class__ = UserQuery
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    email_verified: bool = False
    is_banned: bool = False
    created_at: datetime
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# 使用自定义查询方法
recent_active_users = User.query().recent(days=7).active().all()
```

**关键点：**
- 继承 `ActiveQuery` 创建自定义查询类
- 在模型中设置 `__query_class__ = YourCustomQuery`
- `self.model_class` 访问当前模型，通过 `self.model_class.c` 访问字段代理
- 返回 `self` 支持方法链式调用

> 💡 **AI 提示词：** "如何为 rhosocial-activerecord 模型创建自定义查询类？"

---

## 场景 1：最近 7 天注册的用户

**业务需求**：获取过去一周内新注册的用户列表。

### 方法 1：使用表达式（简单场景）

```python
from datetime import datetime, timedelta
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar, Optional
from pydantic import Field

class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    created_at: datetime
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# 查询最近 7 天注册的用户
seven_days_ago = datetime.now() - timedelta(days=7)

recent_users = User.query() \
    .where(User.c.created_at >= seven_days_ago) \
    .order_by((User.c.created_at, "DESC")) \
    .all()

print(f"最近 7 天注册用户：{len(recent_users)} 人")
for user in recent_users:
    print(f"- {user.username} ({user.created_at.strftime('%Y-%m-%d')})")
```

### 方法 2：使用自定义查询类（推荐）

```python
class UserQuery(ActiveQuery):
    """User 专用查询类。"""
    
    def recent(self, days: int = 7) -> 'UserQuery':
        """查询最近 N 天注册的用户。"""
        cutoff = datetime.now() - timedelta(days=days)
        return self.where(self.model_class.c.created_at >= cutoff)
    
    def newest_first(self) -> 'UserQuery':
        """按注册时间倒序排列。"""
        return self.order_by((self.model_class.c.created_at, "DESC"))


class User(ActiveRecord):
    __query_class__ = UserQuery
    # ... 字段定义


# 使用
recent_users = User.query().recent(days=7).newest_first().all()
```

> 💡 **AI 提示词：** " rhosocial-activerecord 中如何用表达式进行日期范围查询？"

---

## 场景 2：购买次数最多的前 10 名客户

**业务需求**：统计每个客户的订单数量，找出下单最频繁的 10 个客户。

使用 **CTEQuery** 实现复杂聚合：

```python
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.query import CTEQuery

class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'

class Order(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    user_id: int
    total_amount: float
    created_at: datetime
    
    @classmethod
    def table_name(cls) -> str:
        return 'orders'


# 使用 CTEQuery 进行 Top 10 客户统计
# 步骤 1：获取 backend
backend = Order.backend()

# 步骤 2：创建 CTEQuery 实例
cte_query = CTEQuery(backend)

# 步骤 3：创建子查询（统计每个用户的订单数）
order_stats = Order.query() \
    .select('user_id') \
    .group_by('user_id')

# 步骤 4：添加 CTE
cte_query.with_cte('order_stats', order_stats)

# 步骤 5：构建主查询并执行
# 注意：CTEQuery 需要使用 from_cte() 指定主查询从哪个 CTE 读取
top_customers = cte_query \
    .from_cte('order_stats') \
    .select('user_id') \
    .aggregate()  # 返回字典列表

print("客户订单统计：")
for row in top_customers:
    print(f"- 用户 {row['user_id']}")
```

**关键点：**
- `CTEQuery(backend)` 创建实例，需要传入 backend
- `.with_cte('name', query)` 添加 CTE，query 可以是 ActiveQuery
- `.from_cte('name')` 指定主查询从哪个 CTE 读取数据
- `.aggregate()` 执行查询并返回字典列表

> 💡 **AI 提示词：** "如何用 CTEQuery 实现 GROUP BY 聚合查询？"

---

## 场景 3：未完成任务数超过 5 个的用户

**业务需求**：找出积压任务过多的用户，用于提醒或绩效分析。

```python
from typing import ClassVar, Optional
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.query import CTEQuery

class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'

class Task(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    user_id: int
    title: str
    status: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'tasks'


# 查询未完成任务超过 5 个的用户
backend = Task.backend()

# 创建 CTEQuery
cte_query = CTEQuery(backend)

# 创建子查询：统计每个用户的待办任务
pending_counts = Task.query() \
    .select('user_id') \
    .where("status = 'pending'") \
    .group_by('user_id')

# 添加 CTE
cte_query.with_cte('pending_counts', pending_counts)

# 执行主查询
overloaded_users = cte_query \
    .from_cte('pending_counts') \
    .select('user_id') \
    .aggregate()

print("待办任务统计：")
for row in overloaded_users:
    print(f"⚠️ 用户 {row['user_id']}")
```

**关键点：**
- 在子查询中使用 `.where()` 过滤待办任务
- 使用 `.group_by()` 按用户分组
- 主查询从 CTE 中读取统计结果

> 💡 **AI 提示词：** " rhosocial-activerecord 中如何过滤和分组数据？"

---

## 场景 4：按月份统计订单数量

**业务需求**：生成月度销售报告，统计每个月的订单量。

使用 **CTEQuery** 配合日期函数：

```python
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.query import CTEQuery

class Order(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    order_no: str
    total_amount: float
    created_at: datetime
    
    @classmethod
    def table_name(cls) -> str:
        return 'orders'


# 按月份统计订单
backend = Order.backend()

# 创建 CTEQuery
cte_query = CTEQuery(backend)

# 创建子查询：按月份分组统计
# 注意：日期函数是数据库特定的，这里使用字符串形式的 where 条件
monthly_stats = Order.query() \
    .select('id', 'total_amount', 'created_at') \
    .where("created_at >= date('now', '-12 months')") \
    .group_by("strftime('%Y-%m', created_at)")

# 添加 CTE
cte_query.with_cte('monthly_stats', monthly_stats)

# 执行查询
result = cte_query \
    .from_cte('monthly_stats') \
    .select('id', 'total_amount', 'created_at') \
    .aggregate()

print("月度订单统计（最近 12 个月）：")
for row in result:
    print(f"订单 {row['id']}: ¥{row['total_amount']} ({row['created_at']})")
```

**不同数据库的日期函数：**

```python
# 根据后端类型动态选择日期函数
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect
from rhosocial.activerecord.backend.impl.postgres import PostgresDialect

backend = Order.backend()

if isinstance(backend.dialect, SQLiteDialect):
    # SQLite: strftime('%Y-%m', created_at)
    date_expr = "strftime('%Y-%m', created_at)"
elif isinstance(backend.dialect, PostgresDialect):
    # PostgreSQL: to_char(created_at, 'YYYY-MM')
    date_expr = "to_char(created_at, 'YYYY-MM')"
else:  # MySQL
    # MySQL: DATE_FORMAT(created_at, '%Y-%m')
    date_expr = "DATE_FORMAT(created_at, '%Y-%m')"
```

**关键点：**
- 日期函数是数据库特定的，需要根据实际情况选择
- 可以在 WHERE 子句中使用字符串形式的日期比较
- GROUP BY 可以使用字符串形式的表达式

> 💡 **AI 提示词：** "如何在 rhosocial-activerecord 中使用不同数据库的日期函数？"

---

## 场景 5：找出重复邮箱的用户

**业务需求**：数据清洗时发现多个用户使用了相同的邮箱地址，需要找出这些重复记录。

```python
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.query import CTEQuery

class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# 查找重复邮箱
backend = User.backend()

# 创建 CTEQuery
cte_query = CTEQuery(backend)

# 创建子查询：按邮箱分组
duplicate_query = User.query() \
    .select('email', 'id', 'username') \
    .group_by('email')

# 添加 CTE
cte_query.with_cte('duplicate_emails', duplicate_query)

# 执行主查询
result = cte_query \
    .from_cte('duplicate_emails') \
    .select('email', 'id', 'username') \
    .aggregate()

print("用户邮箱列表：")
for row in result:
    print(f"📧 {row['email']}: {row['username']} (ID: {row['id']})")
```

**处理重复数据：**

```python
# 保留最早注册的账户，删除其他重复账户
# 注意：这是示例逻辑，实际执行删除需要谨慎

def deduplicate_emails():
    backend = User.backend()
    
    # 找出每组中最早的 ID
    sql = """
    SELECT MIN(id) as min_id
    FROM users
    GROUP BY email
    """
    
    result = backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.SELECT))
    ids_to_keep = [row['min_id'] for row in result]
    
    # 删除不在保留列表中的记录
    if ids_to_keep:
        placeholders = ','.join(['?' for _ in ids_to_keep])
        delete_sql = f"DELETE FROM users WHERE id NOT IN ({placeholders})"
        backend.execute(delete_sql, tuple(ids_to_keep), options=ExecutionOptions(stmt_type=StatementType.DELETE))
        print("已清理重复邮箱账户")
```

> 💡 **AI 提示词：** "如何用 rhosocial-activerecord 查找并清理重复数据？"

---

## 场景 6：分页查询的实现

**业务需求**：实现经典的分页功能，支持跳转到指定页码。

### 方法 1：在自定义查询类中实现

```python
from typing import ClassVar, Optional, List, Tuple, Dict, Any
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.query import ActiveQuery
from rhosocial.activerecord.base import FieldProxy

class ProductQuery(ActiveQuery):
    """Product 专用查询类，封装分页逻辑。"""
    
    def by_category(self, category: str) -> 'ProductQuery':
        """按分类过滤。"""
        return self.where(self.model_class.c.category == category)
    
    def paginate(
        self, 
        page: int = 1, 
        per_page: int = 20
    ) -> Tuple[List, int]:
        """
        执行分页查询。
        
        Returns:
            (当前页数据, 总记录数)
        """
        # 查询总数
        total = self.count()
        
        # 计算 offset
        offset = (page - 1) * per_page
        
        # 执行分页查询
        items = self \
            .order_by((self.model_class.c.created_at, "DESC")) \
            .limit(per_page) \
            .offset(offset) \
            .all()
        
        return items, total
    
    def paginated_response(
        self, 
        page: int = 1, 
        per_page: int = 20
    ) -> Dict[str, Any]:
        """返回标准分页响应格式（适合 API）。"""
        items, total = self.paginate(page, per_page)
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "data": [item.model_dump() for item in items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }


class Product(ActiveRecord):
    __query_class__ = ProductQuery
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    name: str
    price: float
    category: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def table_name(cls) -> str:
        return 'products'


# 使用示例
page = 1
products, total = Product.query().by_category("electronics").paginate(page=page, per_page=10)

# API 响应格式
response = Product.query().by_category("electronics").paginated_response(page=1, per_page=10)
```

### 方法 2：游标分页（大数据集优化）

```python
class ProductQuery(ActiveQuery):
    """支持游标分页的查询类。"""
    
    def cursor_paginate(
        self,
        last_id: Optional[int] = None,
        per_page: int = 20
    ) -> Tuple[List, Optional[int]]:
        """
        游标分页（适用于大数据集）。
        
        Args:
            last_id: 上一页最后一个商品的 ID
            per_page: 每页数量
        
        Returns:
            (商品列表, 下一页游标)
        """
        query = self.order_by((self.model_class.c.id, "ASC"))
        
        if last_id:
            query = query.where(self.model_class.c.id > last_id)
        
        # 多查询一条用于判断是否有下一页
        products = query.limit(per_page + 1).all()
        
        if len(products) > per_page:
            next_cursor = products[-1].id
            products = products[:-1]  # 移除多查询的一条
        else:
            next_cursor = None
        
        return products, next_cursor


# 使用游标分页
first_page, next_cursor = Product.query().cursor_paginate(per_page=10)
if next_cursor:
    second_page, next_cursor = Product.query().cursor_paginate(last_id=next_cursor, per_page=10)
```

**两种分页方式对比：**

| 特性 | OFFSET 分页 | 游标分页 |
|-----|------------|---------|
| 适用场景 | 小数据集，需要跳页 | 大数据集，只需上一页/下一页 |
| 性能 | OFFSET 大时变慢 | 始终高效 |
| 数据一致性 | 翻页时数据可能变化 | 数据稳定性好 |
| 实现复杂度 | 简单 | 稍复杂 |

> 💡 **AI 提示词：** "rhosocial-activerecord 中 OFFSET 分页和游标分页的区别和选择？"

---

## 更多查询模式

### 模糊搜索（LIKE）

```python
# 用户名包含 "admin"
admins = User.query() \
    .where(User.c.username.like("%admin%")) \
    .all()

# 以 "test" 开头的邮箱
test_users = User.query() \
    .where(User.c.email.like("test%")) \
    .all()
```

### IN 查询

```python
user_ids = [1, 2, 3, 4, 5]
users = User.query() \
    .where(User.c.id.in_(user_ids)) \
    .all()
```

### 范围查询（BETWEEN）

```python
from datetime import date

orders = Order.query() \
    .where(Order.c.created_at.between(date(2024, 1, 1), date(2024, 12, 31))) \
    .all()
```

### 复合条件（AND/OR）

```python
from rhosocial.activerecord.backend.expression import and_, or_

# VIP 或最近 30 天注册
vip_or_recent = User.query() \
    .where(or_(
        User.c.is_vip == True,
        User.c.created_at >= thirty_days_ago
    )) \
    .all()

# VIP 且最近 30 天注册
vip_and_recent = User.query() \
    .where(and_(
        User.c.is_vip == True,
        User.c.created_at >= thirty_days_ago
    )) \
    .all()
```

> 💡 **AI 提示词：** "展示 rhosocial-activerecord 中 AND、OR 条件组合的用法"

---

## CTEQuery vs ActiveQuery 对比

| 特性 | ActiveQuery | CTEQuery |
|-----|------------|---------|
| 使用场景 | 简单到中等复杂度的查询 | 需要 CTE/WITH 子句的复杂查询 |
| 创建方式 | `Model.query()` | `CTEQuery(backend)` |
| 关联 CTE | 不支持 | `.with_cte(name, query)` |
| 指定数据来源 | 自动使用模型表 | `.from_cte(name)` |
| 返回结果 | 模型实例列表 | 字典列表 (`.aggregate()`) |
| 是否需要 backend | 否（从模型获取） | 是（需要传入） |

---

## 另请参阅

- [ActiveQuery](active_query.md) — 完整查询 API 文档
- [CTEQuery](cte_query.md) — 公用表表达式详细文档
- [查询速查表](cheatsheet.md) — 快速参考常见查询模式
