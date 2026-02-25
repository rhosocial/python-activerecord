# 查询速查表

rhosocial-activerecord 常见查询模式快速参考。

> 💡 **AI 提示词：** "展示常见 SQL 查询模式以及如何使用 rhosocial-activerecord ActiveQuery 编写它们，包括过滤、排序、分页和聚合。"

---

## 前置条件：FieldProxy

下面的例子都使用 `User.c.field_name` 语法，其中 `c` 是用户自行定义的 `FieldProxy` 实例。这不是内置的——你必须在模型中自行定义：

```python
from typing import ClassVar
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    # 定义你自己的字段代理（可以取任何名字，'c' 只是约定俗成）
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: int
    name: str
    email: str
```

你可以给它取任何名字（`c`、`fields`、`col` 等）。本文档所有例子都假设你定义为 `c`。

**为什么字段代理的字段可以进行比较、运算等操作？**

当你通过 `User.c.name` 访问字段时，FieldProxy 会返回一个 `Column` 表达式对象。这个对象继承自多个 Mixin 类，这些类实现了 Python 运算符重载：

- **ComparisonMixin**：实现 `==`、`!=`、`>`、`<`、`>=`、`<=` 运算符 → 返回比较谓词
- **StringMixin**：实现 `.like()`、`.ilike()`、`.length()`、`.lower()`、`.upper()` 方法 → 仅在字符串字段上可用
- **ArithmeticMixin**：实现 `+`、`-`、`*`、`/` 运算符 → 用于数值计算
- **LogicalMixin**：实现 `&`（AND）、`|`（OR）、`~`（NOT）运算符 → 用于组合条件

这些 Mixin 只会被混合到支持它们的字段类型的 `Column` 类中。例如，`StringMixin` 只对 `str` 字段可用——因此对数值字段调用 `.like()` 会引发错误。

> 🔮 **未来增强**：FieldProxy 还将支持特定后端的字段类型。当你使用 PostgreSQL 特定类型定义字段时（例如来自 `rhosocial-activerecord-postgres`），将获得额外的操作：
> - PostgreSQL 的 `VARCHAR` 字段支持 `.ilike()`（不区分大小写的 LIKE）
> - 几何类型（POINT、POLYGON 等）支持空间操作（距离、包含等）
> - JSON/JSONB 类型支持 `.json_extract()`、`.json_path()` 操作
> - 详细请参阅 [rhosocial-activerecord-postgres](https://github.com/rhosocial/python-activerecord-postgres) 文档。

---

## 字段类型与可用操作

不同的字段类型支持不同的操作。这是因为 FieldProxy 会根据字段的 Python 类型返回不同的表达式类型：

| 字段类型 | 可用操作 |
|----------|----------|
| **所有类型** | `==`, `!=`, `.in_()`, `.not_in()`, `.is_null()`, `.is_not_null()` |
| **字符串 (`str`)** | `.like()`, `.ilike()`, `.not_like()`, `.not_ilike()`, `.length()`, `.lower()`, `.upper()` |
| **数值 (`int`, `float`)** | `>`, `<`, `>=`, `<=`, BETWEEN 操作 |
| **日期时间** | `>`, `<`, `>=`, `<=`, 日期范围操作 |

```python
# 所有字段：相等判断
users = User.query().where(User.c.name == 'John').all()
users = User.query().where(User.c.id.in_([1, 2, 3])).all()

# 字符串字段：LIKE 模式（数值字段不支持！）
users = User.query().where(User.c.name.like('%John%')).all()
users = User.query().where(User.c.email.ilike('%@GMAIL.COM')).all()

# 数值字段：比较运算（字符串字段不能这样做！）
users = User.query().where(User.c.age >= 18).all()
users = User.query().where((User.c.score >= 0) & (User.c.score <= 100)).all()
```

---

## 比较运算符

| SQL 模式 | rhosocial-activerecord | 示例 |
|----------|------------------------|------|
| `=` (等于) | `==` | `User.c.name == 'John'` |
| `!=` (不等于) | `!=` | `User.c.status != 'deleted'` |
| `>` (大于) | `>` | `User.c.age > 18` |
| `<` (小于) | `<` | `User.c.created_at < datetime.now()` |
| `>=` (大于等于) | `>=` | `User.c.score >= 100` |
| `<=` (小于等于) | `<=` | `User.c.age <= 65` |

```python
# 等于
users = User.query().where(User.c.name == 'John').all()

# 不等于
users = User.query().where(User.c.status != 'inactive').all()

# 范围查询（链式 .where() 实现 AND - 推荐）
users = User.query().where(User.c.age >= 18).where(User.c.age <= 65).all()

# 或使用 & 运算符实现 AND
users = User.query().where(
    (User.c.age >= 18) & (User.c.age <= 65)
).all()
```

---

## IN 和 NOT IN

```python
# IN - 匹配列表中的任意值
user_ids = [1, 2, 3, 4, 5]
users = User.query().where(User.c.id.in_(user_ids)).all()

# NOT IN - 排除某些值
banned_ids = [99, 100]
users = User.query().where(User.c.id.not_in(banned_ids)).all()
```

---

## LIKE 和模式匹配

```python
# 包含 (LIKE '%text%')
users = User.query().where(User.c.name.like('%John%')).all()

# 开头匹配 (LIKE 'text%')
users = User.query().where(User.c.email.like('admin@%')).all()

# 结尾匹配 (LIKE '%text')
users = User.query().where(User.c.name.like('%Smith')).all()

# 不区分大小写的模式匹配
users = User.query().where(User.c.name.ilike('%john%')).all()
```

---

## NULL 检查

```python
# IS NULL - 查找 NULL 值
users = User.query().where(User.c.phone == None).all()

# IS NOT NULL - 查找非 NULL 值
users = User.query().where(User.c.phone != None).all()

# 使用 FieldProxy 方法的替代写法
users = User.query().where(User.c.phone.is_(None)).all()
users = User.query().where(User.c.phone.is_not(None)).all()
```

---

## 逻辑运算符 (AND, OR, NOT)

使用 Python 位运算符进行逻辑组合。**重要**：由于运算符优先级，每个条件必须用括号包裹。

```python
# AND - 所有条件都必须为真 (& 运算符)
users = User.query().where(
    (User.c.age >= 18) & (User.c.status == 'active')
).all()

# OR - 任一条件为真即可 (| 运算符)
users = User.query().where(
    (User.c.role == 'admin') | (User.c.role == 'moderator')
).all()

# NOT - 否定条件 (~ 运算符)
users = User.query().where(
    ~(User.c.status == 'banned')
).all()

# 复杂组合
users = User.query().where(
    (User.c.age >= 18) &
    ((User.c.role == 'admin') | (User.c.is_verified == True))
).all()
```

> ⚠️ **重要**：Python 的位运算符 `&` 和 `|` 优先级高于比较运算符。**必须将每个条件用括号包裹**，否则会出现意外结果：
> ```python
> # ❌ 错误：这将失败
> User.query().where(User.c.age >= 18 & User.c.is_active == True)
>
> # ✅ 正确：包裹每个条件
> User.query().where((User.c.age >= 18) & (User.c.is_active == True))
> ```

---

## 排序 (ORDER BY)

```python
# 单列升序（默认）
users = User.query().order_by(User.c.name).all()

# 单列降序
users = User.query().order_by((User.c.created_at, 'DESC')).all()

# 多列排序
users = User.query().order_by(
    (User.c.status, 'ASC'),
    (User.c.created_at, 'DESC')
).all()

# 随机排序（数据库特定）
# 注意：大数据集慎用
users = User.query().order_by('RANDOM()').all()  # SQLite/PostgreSQL
```

---

## 分页 (LIMIT/OFFSET)

```python
# Limit - 获取前 N 条记录
users = User.query().limit(10).all()

# Offset - 跳过前 N 条记录
users = User.query().offset(20).all()

# 分页 - 获取第 3 页，每页 10 条
page = 3
per_page = 10
users = User.query().offset((page - 1) * per_page).limit(per_page).all()

# 常用分页模式
def get_paginated(page: int = 1, per_page: int = 20):
    offset = (page - 1) * per_page
    return User.query().offset(offset).limit(per_page).all()
```

---

## 聚合函数

> ⚠️ **命名说明**：`sum_`、`min_`、`max_` 使用下划线后缀是为了避免与 Python 内置函数 `sum()`、`min()`、`max()` 冲突。`count` 和 `avg` 不需要下划线。

```python
from rhosocial.activerecord.backend.expression import count, sum_, avg, max_, min_

# COUNT - 记录总数
total = User.query().aggregate(count()).scalar()

# 带条件的 COUNT
active_users = User.query().where(
    User.c.status == 'active'
).aggregate(count()).scalar()

# SUM - 列总和
total_sales = Order.query().aggregate(sum_(Order.c.amount)).scalar()

# AVG - 平均值
avg_age = User.query().aggregate(avg(User.c.age)).scalar()

# MAX/MIN - 极值
max_score = Game.query().aggregate(max_(Game.c.score)).scalar()
min_score = Game.query().aggregate(min_(Game.c.score)).scalar()

# 多个聚合
result = User.query().aggregate(
    count().as_('total'),
    avg(User.c.age).as_('avg_age'),
    max(User.c.created_at).as_('latest')
).one()

print(f"总数: {result.total}, 平均年龄: {result.avg_age}")
```

---

## 日期时间查询

```python
from datetime import datetime, timedelta

# 今天
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
today_users = User.query().where(
    User.c.created_at >= today
).all()

# 最近 7 天
week_ago = datetime.now() - timedelta(days=7)
recent_users = User.query().where(
    User.c.created_at >= week_ago
).all()

# 特定日期范围（链式 .where() 实现 AND - 推荐）
start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)
users = User.query().where(
    User.c.created_at >= start_date
).where(
    User.c.created_at <= end_date
).all()

# 特定日期之前
old_users = User.query().where(
    User.c.created_at < datetime(2020, 1, 1)
).all()
```

---

## 字符串操作

```python
# 字符串长度（如果方言支持）
long_names = User.query().where(
    User.c.name.length() > 50
).all()

# 字符串连接（如果支持）
# 注意：检查你的方言是否支持字符串连接
```

---

## 存在性检查

```python
# 检查是否有任何记录
has_users = User.query().exists()

# 带条件的检查
has_admins = User.query().where(User.c.role == 'admin').exists()

# 在条件逻辑中使用
if User.query().where(User.c.email == 'test@example.com').exists():
    print("用户已存在！")
```

---

## 选择特定列

```python
# 只选择特定列（推荐：使用 FieldProxy）
users = User.query().select(User.c.id, User.c.name, User.c.email).all()

# 替代方式：如果你知道列名，也可以直接使用字符串
users = User.query().select('id', 'name', 'email').all()

# 排除特定列（选择其他所有列）
users = User.query().select(exclude=['password_hash']).all()

# 注意：选择特定列时，你得到的是类字典对象
# 而不是完整的模型实例
```

---

## 去重值

```python
# 获取某列的不重复值
roles = User.query().distinct(User.c.role).all()

# 多列去重
# （返回唯一组合）
results = User.query().distinct(User.c.country, User.c.city).all()
```

---

## 原始 SQL（需要时）

```python
# 执行原始 SQL 进行复杂查询
result = User.__backend__.execute(
    "SELECT * FROM users WHERE custom_condition = ?",
    ('value',),
    options=ExecutionOptions(stmt_type=StatementType.DQL)
)

# 转换为模型
users = [User(**row) for row in result.rows]
```

> ⚠️ **警告：** 尽量少用原始 SQL。它会降低跨数据库后端的可移植性。

---

## 快速参考卡

```python
# 最常见的模式汇总

# 基本获取
User.query().all()                           # 所有记录（列表）
User.query().one()                           # 第一条匹配的记录或 None

# 过滤
User.query().where(User.c.id == 1).one()
User.query().where(User.c.age > 18).all()
User.query().where(User.c.name.in_(['A', 'B'])).all()

# 逻辑运算符（使用 & | ~，不是 and or not）
User.query().where((User.c.age >= 18) & (User.c.is_active == True)).all()
User.query().where((User.c.role == 'admin') | (User.c.role == 'moderator')).all()
User.query().where(~(User.c.status == 'deleted')).all()

# 排序
User.query().order_by(User.c.name).all()
User.query().order_by((User.c.age, 'DESC')).all()

# 分页
User.query().limit(10).all()
User.query().offset(20).limit(10).all()

# 计数
User.query().count()
User.query().where(User.c.active == True).count()

# 聚合
from rhosocial.activerecord.backend.expression import count, sum_, avg
User.query().aggregate(count()).scalar()
Order.query().aggregate(sum_(Order.c.amount)).scalar()
```

---

## 另请参阅

- [ActiveQuery](./active_query.md) - 完整的 ActiveQuery 文档
- [查询实战](./recipes.md) - 复杂查询示例
- [查询优化](./optimization.md) - 性能建议
