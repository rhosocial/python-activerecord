# 来自其他框架

如果你熟悉其他 ORM 或框架，本指南将帮助你将现有知识映射到 `rhosocial-activerecord` 概念。

## 如果你来自 **Django ORM**

| Django | rhosocial-activerecord | 说明 |
|--------|------------------------|------|
| `models.Model` | `ActiveRecord` | 模型基类 |
| `objects.filter()` | `.query().where()` | 查询构建 |
| `objects.get()` | `.find_one()` | 获取单条记录 |
| `ForeignKey` | `BelongsTo` | 多对一关系 |
| `ManyToManyField` | 使用中间模型 + `HasMany` | 通过中间表实现多对多 |
| `auto_now_add`, `auto_now` | `TimestampMixin` | 自动时间戳 |
| `SoftDelete` (django-softdelete) | `SoftDeleteMixin` | 逻辑删除 |
| `F()` 表达式 | `FieldProxy`（如 `User.c.age`） | 类型安全的字段引用 |
| `QuerySet` | `ActiveQuery` | 查询构建类 |
| `select_related` | `.with_()` | 预加载 |

**关键差异：**
- Django 在查询中使用字符串引用；我们使用类型安全的 `FieldProxy`
- Django 有自动迁移；我们使用显式 SQL 或迁移工具
- Django 有全局数据库连接；我们使用显式后端配置

> 💡 **AI 提示词：** "我熟悉 Django ORM。解释与 rhosocial-activerecord 的主要差异和相似之处。"

## 如果你来自 **SQLAlchemy**

| SQLAlchemy | rhosocial-activerecord | 说明 |
|------------|------------------------|------|
| `declarative_base()` | `ActiveRecord` | 基类 |
| `session.query(Model)` | `Model.query()` | 查询入口点 |
| `filter()`, `filter_by()` | `.where()` | 过滤 |
| `relationship()` | `HasMany`, `BelongsTo` | 关系 |
| `Column(Integer)` | `int` 配合类型提示 | 原生 Python 类型 |
| `session.add()` | `.save()` | 持久化对象 |
| `session.commit()` | 自动提交或显式 | 事务处理 |
| `select()` | `QueryExpression` | SQL 表达式构建 |
| `text()` 原始 SQL | 谨慎使用 | 我们更倾向于表达式 |

**关键差异：**
- SQLAlchemy 使用基于会话的方法；我们使用 Active Record 模式
- SQLAlchemy 有 Core 和 ORM 层；我们将其统一
- SQLAlchemy 需要显式表定义；我们使用 Pydantic 模型
- 我们的 Expression-Dialect 分离与 SQLAlchemy 的编译器类似但更加显式

> 💡 **AI 提示词：** "比较 SQLAlchemy 2.0 与 rhosocial-activerecord 架构。各自的优缺点是什么？"

## 如果你来自 **Rails ActiveRecord**

| Rails | rhosocial-activerecord | 说明 |
|-------|------------------------|------|
| `ActiveRecord::Base` | `ActiveRecord` | 基类 |
| `where()` | `.where()` | 相同的方法名！ |
| `find()` | `.find_one()` | 通过主键获取 |
| `has_many` | `HasMany` | 一对多 |
| `belongs_to` | `BelongsTo` | 多对一 |
| `has_one` | `HasOne` | 一对一 |
| `validates` | Pydantic `Field()` | 验证 |
| `before_save` | 模型事件/hooks | 生命周期回调 |
| `scope` | 返回查询的类方法 | 可复用的查询定义 |

**关键差异：**
- Rails 是 Ruby；我们是 Python，具有完整的类型安全
- Rails 有魔法方法；我们更倾向于显式类型安全的方法
- Rails 迁移是 Ruby DSL；我们使用 SQL 或迁移工具
- 我们的 `FieldProxy` 提供了 Ruby 无法匹敌的 IDE 支持

> 💡 **AI 提示词：** "我来自 Rails。如何将我的 ActiveRecord 知识迁移到这个 Python ORM？"

## 如果你来自 **Peewee**

| Peewee | rhosocial-activerecord | 说明 |
|--------|------------------------|------|
| `Model` | `ActiveRecord` | 基类 |
| `CharField()`, `IntegerField()` | `str`, `int` 配合类型提示 | 原生 Python 类型 |
| `fn` 函数 | `functions` 模块 | SQL 函数 |
| `prefetch()` | `.with_()` | 预加载 |
| `database` 代理 | 显式后端 | 数据库连接 |

**关键差异：**
- Peewee 使用字段实例；我们使用 Python 类型提示
- Peewee 有更简单的 API；我们有更多类型安全
- 我们的 Expression 系统比 Peewee 的查询构建器更强大

> 💡 **AI 提示词：** "比较 Peewee 与 rhosocial-activerecord。我应该何时选择其中一个？"

## 如果你来自 **Prisma**（TypeScript/Node.js）

| Prisma | rhosocial-activerecord | 说明 |
|--------|------------------------|------|
| `schema.prisma` | Python 类型提示 | 模式定义 |
| `prisma.user.findMany()` | `User.query().all()` | 查询方法 |
| `include` | `.with_()` | 关系加载 |
| 生成的客户端 | 直接使用类 | 无需代码生成 |
| 类型安全查询 | `FieldProxy` | 两者都提供类型安全 |

**关键差异：**
- Prisma 需要模式文件和代码生成；我们使用纯 Python
- Prisma 有自己的查询语言；我们使用 Python 表达式
- rhosocial-activerecord 不需要构建步骤

> 💡 **AI 提示词：** "我在 TypeScript 中使用过 Prisma。这个 Python ORM 在开发体验方面如何比较？"

## 常见迁移模式

### 定义模型

**Django：**
```python
class User(models.Model):
    username = models.CharField(max_length=50)
    email = models.EmailField()
```

**rhosocial-activerecord：**
```python
class User(ActiveRecord):
    __table_name__ = "users"
    username: str = Field(max_length=50)
    email: str
```

### 查询

**SQLAlchemy：**
```python
session.query(User).filter(User.age > 18).all()
```

**rhosocial-activerecord：**
```python
User.query().where(User.c.age > 18).all()
```

### 关系

**Rails：**
```ruby
class User < ApplicationRecord
  has_many :posts
end
```

**rhosocial-activerecord：**
```python
class User(ActiveRecord):
    posts: ClassVar[HasMany["Post"]] = HasMany(foreign_key="user_id")
```

## 快速参考卡

| 概念 | 在这里使用 |
|------|-----------|
| 模型基类 | `ActiveRecord` / `AsyncActiveRecord` |
| 字段定义 | Python 类型提示 + Pydantic 的 `Field()` |
| 验证 | `Field()` 中的 Pydantic 验证 |
| 查询构建 | `.query().where().order_by().all()` |
| 类型安全字段访问 | `User.c.field_name` (FieldProxy) |
| 关系 | `BelongsTo`, `HasOne`, `HasMany` |
| 时间戳 | `TimestampMixin` |
| 软删除 | `SoftDeleteMixin` |
| 数据库后端 | 使用 `Backend` 类配置 |
| 原始 SQL | 仅在必要时使用；优先使用表达式 |

## 获取帮助

- 不确定如何转换模式？在文档中查找 💡 AI 提示词标记
- 问你的 AI 助手："如何在 rhosocial-activerecord 中做 [X]（来自 [框架]）？"
- 查看 [术语表](glossary.md) 了解术语解释

## 另请参阅

- [技术选型指南](comparison.md) - 还在评估使用哪个 ORM？
- [术语表](glossary.md) - 术语解释
- [核心特性](key_features.md) - 核心功能导览
- [AI 辅助开发](ai_assistance.md) - 使用 AI 加速学习
