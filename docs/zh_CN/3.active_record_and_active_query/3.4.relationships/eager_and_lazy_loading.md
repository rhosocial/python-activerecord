# 预加载和延迟加载

高效的数据加载对应用程序性能至关重要，特别是在处理相关记录时。rhosocial ActiveRecord提供了两种主要的相关数据加载方法：预加载和延迟加载。本文档深入探讨这些加载策略，提供实用示例和最佳实践。

## 理解加载策略

在深入了解每种加载策略的细节之前，理解它们之间的根本区别很重要：

- **延迟加载**：仅在明确请求时才加载相关数据
- **预加载**：提前加载相关数据，通常在加载父记录时

这些策略的选择可能会显著影响应用程序的性能和资源使用。

## 延迟加载

延迟加载是rhosocial ActiveRecord中的默认行为。当您访问关系时，框架执行单独的数据库查询来检索相关数据。

### 延迟加载的工作原理

当您在模型中定义关系时，rhosocial ActiveRecord会创建一个方法，当调用该方法时，会执行查询来获取相关记录：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class Author(IntegerPKMixin, ActiveRecord):
    __table_name__ = "authors"
    
    id: Optional[int] = None
    name: str
    
    books: ClassVar[HasMany['Book']] = HasMany(
        foreign_key='author_id',
        inverse_of='author'
    )

class Book(IntegerPKMixin, ActiveRecord):
    __table_name__ = "books"
    
    id: Optional[int] = None
    title: str
    author_id: int
    
    author: ClassVar[BelongsTo['Author']] = BelongsTo(
        foreign_key='author_id',
        inverse_of='books'
    )
```

使用延迟加载时，只有在调用关系方法时才会加载相关数据：

```python
# 加载一个作者
author = Author.find_by(name="简·奥斯汀")

# 此时还没有加载任何书籍

# 现在当我们调用books()方法时，书籍被加载
books = author.books()

for book in books:
    print(f"书籍: {book.title}")
    
    # 这会触发另一个查询来加载作者
    book_author = book.author()
    print(f"作者: {book_author.name}")
```

### 何时使用延迟加载

在以下情况下，延迟加载是适当的：

1. **当您不总是需要相关数据时**：如果您只是偶尔需要访问相关记录，延迟加载可以防止不必要的数据检索

2. **对于深度嵌套的关系**：当您有复杂的关系链，并且只需要特定分支时

3. **对于大型相关数据集**：当相关集合可能包含许多记录，而您想避免全部加载它们时

4. **在开发和探索阶段**：当您还不确定需要哪些关系时

### N+1查询问题

延迟加载的主要缺点是N+1查询问题。当您加载N条记录的集合，然后为每条记录访问一个关系时，会导致N个额外的查询：

```python
# 加载所有作者（1个查询）
authors = Author.find_all().all()

# 对于每个作者，加载他们的书籍（N个额外查询）
for author in authors:
    books = author.books()  # 这为每个作者执行一个查询
    print(f"作者: {author.name}, 书籍数量: {len(books)}")
```

随着记录数量的增加，这种模式可能会导致性能问题。

## 预加载

预加载通过提前加载相关数据来解决N+1查询问题。rhosocial ActiveRecord提供了`with_`方法来指定应该预加载哪些关系。

### 基本预加载

要预加载关系，在查询中使用`with_`方法：

```python
# 获取作者时预加载书籍
authors = Author.find_all().with_("books").all()

# 现在您可以访问书籍而无需额外查询
for author in authors:
    books = author.books()  # 不执行额外的查询
    print(f"作者: {author.name}, 书籍数量: {len(books)}")
```

在后台，rhosocial ActiveRecord执行两个查询：
1. 一个查询获取所有作者
2. 另一个查询获取这些作者的所有书籍

然后，它在内存中将书籍与各自的作者关联起来，因此当您访问关系时不需要额外的查询。

### 嵌套预加载

您可以使用点表示法预加载嵌套关系：

```python
# 预加载书籍和每本书的评论
authors = Author.find_all().with_("books.reviews").all()

# 现在您可以访问书籍和评论而无需额外查询
for author in authors:
    for book in author.books():
        print(f"书籍: {book.title}")
        for review in book.reviews():
            print(f"  评论: {review.content}")
```

### 多关系预加载

您可以通过向`with_`方法传递列表来预加载多个关系：

```python
# 同时预加载书籍和出版商信息
authors = Author.find_all().with_(["books", "publisher"]).all()

# 现在您可以访问这两种关系而无需额外查询
for author in authors:
    books = author.books()
    publisher = author.publisher()
    print(f"作者: {author.name}, 出版商: {publisher.name}")
    print(f"书籍数量: {len(books)}")
```

### 条件预加载

您可以将预加载与查询条件结合起来，限制加载的相关记录：

```python
# 只预加载已出版的书籍
authors = Author.find_all().with_("books", lambda q: q.where(published=True)).all()

# 现在您可以访问只有已出版的书籍而无需额外查询
for author in authors:
    published_books = author.books()  # 只包含已出版的书籍
    print(f"作者: {author.name}, 已出版书籍: {len(published_books)}")
```

### 何时使用预加载

在以下情况下，预加载是有益的：

1. **当您知道将需要相关数据时**：如果您确定将访问相关记录，预加载可以减少数据库查询的数量

2. **对于集合**：当处理多个父记录及其关系时

3. **用于显示相关数据**：当构建显示父记录及其相关数据的视图或报告时

4. **为了一致的性能**：避免不可预测的查询模式并确保一致的响应时间

## 高级加载技术

### 选择性加载

有时您可能只想加载相关记录的特定列。您可以通过将预加载与选择子句结合来实现这一点：

```python
# 只预加载书籍标题
authors = Author.find_all().with_("books", lambda q: q.select("id", "title")).all()

# 现在您可以访问书籍标题而无需加载所有书籍数据
for author in authors:
    books = author.books()
    for book in books:
        print(f"书籍标题: {book.title}")
        # 其他书籍属性可能不可用
```

### 计数相关记录

如果您只需要知道相关记录的数量而不加载它们，可以使用`with_count`方法：

```python
# 加载作者及其书籍数量
authors = Author.find_all().with_count("books").all()

# 访问数量而不加载实际的书籍
for author in authors:
    book_count = author.books_count  # 这是一个属性，不是方法调用
    print(f"作者: {author.name}, 书籍数量: {book_count}")
```

### 手动预加载特定记录

在某些情况下，您可能希望手动预加载相关记录以获得更好的控制：

```python
# 加载所有作者
authors = Author.find_all().all()

# 获取所有作者ID
author_ids = [author.id for author in authors]

# 在单个查询中预加载这些作者的所有书籍
all_books = Book.find_all().where(author_id__in=author_ids).all()

# 按作者ID分组书籍
books_by_author = {}
for book in all_books:
    if book.author_id not in books_by_author:
        books_by_author[book.author_id] = []
    books_by_author[book.author_id].append(book)

# 现在您可以访问书籍而无需额外查询
for author in authors:
    author_books = books_by_author.get(author.id, [])
    print(f"作者: {author.name}, 书籍数量: {len(author_books)}")
```

## 性能考虑

### 内存使用

预加载一次将所有相关数据加载到内存中，这对于大型数据集可能是一个问题。考虑以下因素：

- **数据集大小**：对于非常大的相关集合，预加载可能会消耗大量内存
- **应用程序环境**：内存有限的服务器环境可能受益于更有选择性的加载策略
- **用户体验**：如果它显著改善响应时间，内存成本可能是值得的

### 查询复杂性

预加载可以生成复杂的SQL查询，特别是对于嵌套关系。监控您的数据库性能以确保这些查询是高效的：

- 在外键上使用数据库索引
- 考虑预加载关系的深度
- 注意非常复杂的关系链的查询超时

### 基准测试

对于您的特定用例，对不同的加载策略进行基准测试通常很有帮助：

```python
import time

# 延迟加载基准测试
start_time = time.time()
authors = Author.find_all().all()
for author in authors:
    books = author.books()
    for book in books:
        _ = book.title
end_time = time.time()
print(f"延迟加载时间: {end_time - start_time} 秒")

# 预加载基准测试
start_time = time.time()
authors = Author.find_all().with_("books").all()
for author in authors:
    books = author.books()
    for book in books:
        _ = book.title
end_time = time.time()
print(f"预加载时间: {end_time - start_time} 秒")
```

## 最佳实践

### 1. 分析您的应用程序

使用数据库查询日志和分析工具来识别N+1查询问题和其他性能问题：

```python
# 在开发期间启用查询日志
from rhosocial.activerecord import set_query_logging
set_query_logging(True)

# 您的代码
```

### 2. 策略性地使用预加载

只预加载您知道将需要的关系。预加载未使用的关系可能会浪费内存和数据库资源。

### 3. 考虑批处理

对于非常大的数据集，考虑分批处理记录，以平衡内存使用和查询效率：

```python
# 每批处理100个作者
batch_size = 100
offset = 0

while True:
    authors_batch = Author.find_all().limit(batch_size).offset(offset).with_("books").all()
    
    if not authors_batch:
        break
        
    for author in authors_batch:
        # 处理作者和书籍
        pass
        
    offset += batch_size
```

### 4. 使用关系缓存

为频繁访问的关系配置适当的缓存，以减少数据库负载：

```python
from rhosocial.activerecord.relation import HasMany, CacheConfig

class Author(IntegerPKMixin, ActiveRecord):
    # ...
    
    books: ClassVar[HasMany['Book']] = HasMany(
        foreign_key='author_id',
        inverse_of='author',
        cache_config=CacheConfig(enabled=True, ttl=300)  # 缓存5分钟
    )
```

### 5. 优化查询

使用查询范围和条件来限制加载的数据量：

```python
# 为最近的书籍定义一个范围
class Book(IntegerPKMixin, ActiveRecord):
    # ...
    
    @classmethod
    def recent(cls, query=None):
        query = query or cls.find_all()
        return query.where(published_at__gte=datetime.now() - timedelta(days=30))

# 将范围与预加载一起使用
authors = Author.find_all().with_("books", Book.recent).all()
```

### 6. 考虑反规范化

对于读取密集型应用程序，考虑对某些数据进行反规范化，以减少对关系加载的需求：

```python
class Author(IntegerPKMixin, ActiveRecord):
    __table_name__ = "authors"
    
    id: Optional[int] = None
    name: str
    book_count: int = 0  # 反规范化的书籍数量
    
    # ...
```

## 结论

在预加载和延迟加载之间选择是一个关键决策，它影响应用程序的性能和资源使用。通过理解权衡并为每种情况应用适当的策略，您可以优化数据库交互并为用户提供更好的体验。

请记住，没有一种通用的方法——最佳加载策略取决于您的特定用例、数据量和应用程序需求。定期分析和基准测试将帮助您做出明智的决策并持续改进应用程序的性能。