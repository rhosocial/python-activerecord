# 查询作用域

本文档说明如何在ActiveRecord模型中使用查询作用域来创建可重用的查询条件和方法。

## 介绍

查询作用域是一种在模型类上定义常用查询条件作为方法的方式。它们帮助您封装查询逻辑，使代码更具可读性，并消除应用程序中的重复。

## 定义查询作用域

在ActiveRecord中定义查询作用域有两种主要方法：

1. **模型类上的实例方法**
2. **向多个模型添加查询方法的混入**

### 方法1：模型实例方法

定义查询作用域的最简单方法是向模型类添加返回查询对象的方法：

```python
from rhosocial.activerecord import ActiveRecord

class Article(ActiveRecord):
    __table_name__ = 'articles'
    
    @classmethod
    def published(cls):
        """已发布文章的作用域。"""
        return cls.query().where('status = ?', 'published')
    
    @classmethod
    def recent(cls, days=7):
        """最近发布文章的作用域。"""
        return cls.query().where(
            'published_at > NOW() - INTERVAL ? DAY', 
            days
        ).order_by('published_at DESC')
    
    @classmethod
    def by_author(cls, author_id):
        """特定作者文章的作用域。"""
        return cls.query().where('author_id = ?', author_id)
```

### 方法2：查询作用域混入

对于适用于多个模型的查询作用域，您可以创建混入：

```python
class TimeScopeMixin:
    """添加基于时间的查询作用域的混入。"""
    
    @classmethod
    def created_after(cls, date):
        """查找在指定日期之后创建的记录。"""
        return cls.query().where('created_at > ?', date)
    
    @classmethod
    def created_before(cls, date):
        """查找在指定日期之前创建的记录。"""
        return cls.query().where('created_at < ?', date)
    
    @classmethod
    def created_between(cls, start_date, end_date):
        """查找在指定日期之间创建的记录。"""
        return cls.query().where(
            'created_at BETWEEN ? AND ?', 
            start_date, end_date
        )


class SoftDeleteScopeMixin:
    """添加软删除查询作用域的混入。"""
    
    @classmethod
    def active(cls):
        """仅查找活跃（未删除）的记录。"""
        return cls.query().where('deleted_at IS NULL')
    
    @classmethod
    def deleted(cls):
        """仅查找软删除的记录。"""
        return cls.query().where('deleted_at IS NOT NULL')
```

然后将这些混入应用到您的模型：

```python
class User(ActiveRecord, TimeScopeMixin, SoftDeleteScopeMixin):
    __table_name__ = 'users'
    # ...

class Post(ActiveRecord, TimeScopeMixin, SoftDeleteScopeMixin):
    __table_name__ = 'posts'
    # ...
```

## 使用查询作用域

一旦定义，查询作用域可以像任何其他查询方法一样使用：

```python
# 使用模型特定的作用域
recent_articles = Article.published().recent().all()
user_articles = Article.by_author(current_user.id).all()

# 使用混入作用域
recent_users = User.created_after(last_week).active().all()
deleted_posts = Post.deleted().order_by('deleted_at DESC').all()
```

### 组合多个作用域

查询作用域的主要优点之一是它们可以相互组合，也可以与标准查询方法组合：

```python
# 组合多个作用域
results = Article.published()\
    .recent(30)\
    .by_author(author_id)\
    .order_by('title')\
    .limit(10)\
    .all()
```

## 带参数的动态作用域

作用域可以接受参数，使其更加灵活：

```python
class Product(ActiveRecord):
    __table_name__ = 'products'
    
    @classmethod
    def price_range(cls, min_price, max_price):
        """查找价格范围内的产品。"""
        return cls.query().where(
            'price BETWEEN ? AND ?', 
            min_price, max_price
        )
    
    @classmethod
    def in_category(cls, category_id):
        """查找特定类别的产品。"""
        return cls.query().where('category_id = ?', category_id)
    
    @classmethod
    def with_tag(cls, tag):
        """查找带有特定标签的产品。"""
        return cls.query()\
            .join('JOIN product_tags ON products.id = product_tags.product_id')\
            .join('JOIN tags ON product_tags.tag_id = tags.id')\
            .where('tags.name = ?', tag)
```

用法：

```python
# 查找价格实惠的电子产品
results = Product.price_range(0, 100)\
    .in_category('electronics')\
    .with_tag('bestseller')\
    .all()
```

## 默认作用域

您可以通过重写`query`方法来实现默认作用域，该作用域会自动应用于模型的所有查询：

```python
class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    @classmethod
    def query(cls):
        """创建应用了默认作用域的新查询。"""
        # 从标准查询开始并应用默认条件
        return super().query().where('is_published = ?', True)
```

通过这种实现，除非明确覆盖，否则`Post`模型上的所有查询都将自动包含`is_published = True`条件。

## 取消作用域

要移除默认作用域或重置特定查询条件，可以创建一个全新的查询实例：

```python
# 创建一个没有任何默认作用域的全新查询
from rhosocial.activerecord.query import ActiveQuery
all_posts = ActiveQuery(Post).all()  # 直接创建一个新的查询实例

# 或使用查询类构造函数
all_posts = Post.query().__class__(Post).all()  # 创建新的查询实例
```

## 最佳实践

1. **清晰命名作用域**：使用描述性名称，指示作用域的功能。

2. **保持作用域专注**：每个作用域应该有单一的责任。

3. **文档化作用域**：为每个作用域提供清晰的文档字符串，解释其目的和参数。

4. **考虑可组合性**：设计可以有效组合的作用域。

5. **避免过度使用默认作用域**：默认作用域可能会导致意外行为，请谨慎使用。

6. **使用参数化查询**：始终使用参数化查询来防止SQL注入。

## 自定义查询类

除了使用查询作用域，您还可以通过自定义查询类来扩展查询功能。通过设置模型的`__query_class__`属性，您可以替换默认的查询实例：

```python
from rhosocial.activerecord import ActiveRecord
from .queries import CustomArticleQuery

class Article(ActiveRecord):
    __table_name__ = 'articles'
    __query_class__ = CustomArticleQuery  # 指定自定义查询类
    
    # 模型定义继续...
```

### 创建额外的查询方法

您还可以创建额外的查询方法与原查询方法共存：

```python
class Article(ActiveRecord):
    __table_name__ = 'articles'
    
    @classmethod
    def query_special(cls):
        """返回特殊查询实例。"""
        from .queries import SpecialArticleQuery
        return SpecialArticleQuery(cls)
```

这样，您可以同时使用默认查询和特殊查询：

```python
# 使用默认查询
regular_results = Article.query().all()

# 使用特殊查询
special_results = Article.query_special().all()
```

## 结论

查询作用域是ActiveRecord中一个强大的功能，它允许您创建可重用、可组合的查询片段。通过有效使用作用域和自定义查询类，您可以使数据库交互更加简洁、一致和安全，同时提高代码的可维护性和灵活性。