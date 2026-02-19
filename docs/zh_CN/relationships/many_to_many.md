# 多对多关系 (Many-to-Many)

本库目前没有内置隐式的 `ManyToMany` 描述符，而是鼓励使用**中间模型 (Intermediate Model)** 显式定义。这种方式虽然多写几行代码，但允许你在关系上存储额外数据（例如：标签是什么时候打上去的）。

> 💡 **AI提示词示例**: "如何在ActiveRecord中实现多对多关系？为什么不直接提供ManyToMany描述符？"

## 场景：Post 与 Tag

一篇文章有多个标签，一个标签可用于多篇文章。我们需要一个 `PostTag` 中间表来建立这种多对多关系。

### 1. 定义中间模型

中间模型是多对多关系的核心，它不仅连接两个实体，还可以存储关系本身的额外信息。

```python
# 导入必要的模块
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import BelongsTo
from rhosocial.activerecord.field import TimestampMixin

# PostTag类代表文章和标签之间的关联关系
# 继承TimestampMixin自动添加创建时间字段
class PostTag(TimestampMixin, ActiveRecord):
    # 外键字段，关联到Post表的id字段
    post_id: str
    # 外键字段，关联到Tag表的id字段
    tag_id: str
    # 额外信息：打标签的时间（从TimestampMixin继承）
    # created_at: datetime  # 自动添加的时间戳字段
    
    # 定义到Post的从属关系
    # BelongsTo描述符定义了从属关系
    # foreign_key='post_id' 指的是本表中的外键字段名
    # inverse_of='post_tags' 指定了反向关系的名称，即在Post类中对应的关联关系名
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id', inverse_of='post_tags')
    
    # 定义到Tag的从属关系
    # BelongsTo描述符定义了从属关系
    # foreign_key='tag_id' 指的是本表中的外键字段名
    # inverse_of='post_tags' 指定了反向关系的名称，即在Tag类中对应的关联关系名
    tag: ClassVar[BelongsTo['Tag']] = BelongsTo(foreign_key='tag_id', inverse_of='post_tags')

    # 返回表名
    @classmethod
    def table_name(cls) -> str:
        return 'post_tags'
```

> 💡 **AI提示词示例**: "中间模型在多对多关系中起什么作用？为什么比隐式的多对多更好？"

### 2. 定义两端模型

定义参与多对多关系的两个实体模型。

```python
# 导入必要的模块
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany

# Post类代表博客文章
class Post(ActiveRecord):
    # 文章标题
    title: str
    # 文章内容
    content: str
    
    # 指向中间表的关系 (一对多)
    # 一篇文章可以通过中间表关联到多个标签关系记录
    # HasMany描述符定义了一对多的拥有关系
    # foreign_key='post_id' 指的是 PostTag 表中的外键字段名
    # inverse_of='post' 指定了反向关系的名称，即在PostTag类中对应的关联关系名
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='post_id', inverse_of='post')

    # 返回表名
    @classmethod
    def table_name(cls) -> str:
        return 'posts'

# Tag类代表文章标签
class Tag(ActiveRecord):
    # 标签名称
    name: str
    # 标签描述
    description: str
    
    # 指向中间表的关系 (一对多)
    # 一个标签可以通过中间表关联到多个文章关系记录
    # HasMany描述符定义了一对多的拥有关系
    # foreign_key='tag_id' 指的是 PostTag 表中的外键字段名
    # inverse_of='tag' 指定了反向关系的名称，即在PostTag类中对应的关联关系名
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='tag_id', inverse_of='tag')

    # 返回表名
    @classmethod
    def table_name(cls) -> str:
        return 'tags'
```

> 💡 **AI提示词示例**: "多对多关系的两端模型应该如何定义？与一对多关系有什么相似之处？"

### 3. 使用多对多关系

通过中间模型访问多对多关系的数据。

```python
# 创建文章
post = Post(title="Python编程入门", content="Python是一门强大的编程语言...")
post.save()

# 创建标签
tag1 = Tag(name="Python", description="Python编程语言相关")
tag1.save()
tag2 = Tag(name="编程", description="编程技术相关")
tag2.save()

# 创建关联关系
post_tag1 = PostTag(post_id=post.id, tag_id=tag1.id)
post_tag1.save()
post_tag2 = PostTag(post_id=post.id, tag_id=tag2.id)
post_tag2.save()

# 查询某文章的所有标签
# 方法1: 通过中间表遍历 (会产生 N+1 查询，不推荐)
post = Post.find_one(post.id)
# 获取中间记录
links = post.post_tags()  # 第一次查询：获取所有关联记录
# 获取实际标签 (会产生 N+1 查询，每次调用tag()都会执行一次查询)
tags = [link.tag() for link in links]  # 多次查询：获取每个标签
print(f"文章标签: {[tag.name for tag in tags]}")

# 方法2: 使用预加载 (推荐，避免N+1问题)
# 在查询时一并加载关联数据
post_with_tags = Post.query().with_('post_tags').all()
for post in post_with_tags:
    links = post.post_tags()  # 从缓存中获取，不执行查询
    tags = [link.tag() for link in links]  # 从缓存中获取，不执行查询
    print(f"文章 '{post.title}' 的标签: {[tag.name for tag in tags]}")
```

> 💡 **AI提示词示例**: "如何高效地查询多对多关系的数据？如何避免N+1查询问题？"

### 4. 高级用法：直接获取关联对象

为了更方便地使用多对多关系，可以添加便捷方法：

```python
# 扩展Post类，添加获取标签的便捷方法
class Post(ActiveRecord):
    title: str
    content: str
    
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='post_id', inverse_of='post')

    @classmethod
    def table_name(cls) -> str:
        return 'posts'
    
    # 便捷方法：直接获取所有标签
    def tags(self):
        """获取文章的所有标签"""
        # 通过中间表获取所有关联记录，然后获取对应的标签
        links = self.post_tags()
        return [link.tag() for link in links]
    
    # 便捷方法：添加标签
    def add_tag(self, tag):
        """为文章添加标签"""
        # 检查是否已存在关联
        existing = PostTag.query().where(
            (PostTag.c.post_id == self.id) & (PostTag.c.tag_id == tag.id)
        ).first()
        
        if not existing:
            post_tag = PostTag(post_id=self.id, tag_id=tag.id)
            post_tag.save()
            return post_tag
        return existing

# 扩展Tag类，添加获取文章的便捷方法
class Tag(ActiveRecord):
    name: str
    description: str
    
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='tag_id', inverse_of='tag')

    @classmethod
    def table_name(cls) -> str:
        return 'tags'
    
    # 便捷方法：直接获取所有文章
    def posts(self):
        """获取使用此标签的所有文章"""
        # 通过中间表获取所有关联记录，然后获取对应的文章
        links = self.post_tags()
        return [link.post() for link in links]
```

> 💡 **AI提示词示例**: "如何为多对多关系添加便捷的访问方法？这样做的好处是什么？"