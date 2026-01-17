# 多对多关系 (Many-to-Many)

本库目前没有内置隐式的 `ManyToMany` 描述符，而是鼓励使用**中间模型 (Intermediate Model)** 显式定义。这种方式虽然多写几行代码，但允许你在关系上存储额外数据（例如：标签是什么时候打上去的）。

## 场景：Post 与 Tag

一篇文章有多个标签，一个标签可用于多篇文章。我们需要一个 `PostTag` 中间表。

### 1. 定义中间模型

```python
class PostTag(ActiveRecord):
    post_id: str
    tag_id: str
    created_at: int  # 额外信息：打标签的时间

    # 定义到两端的 BelongsTo
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id', inverse_of='post_tags')
    tag: ClassVar[BelongsTo['Tag']] = BelongsTo(foreign_key='tag_id', inverse_of='post_tags')
```

### 2. 定义两端模型

```python
class Post(ActiveRecord):
    # 指向中间表
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='post_id', inverse_of='post')

class Tag(ActiveRecord):
    # 指向中间表
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='tag_id', inverse_of='tag')
```

### 3. 使用

要查询某文章的所有标签，我们通常通过中间表进行连接查询（将在查询章节详细介绍），或者在应用层遍历：

```python
post = Post.find(1)
# 获取中间记录
links = post.post_tags()
# 获取实际标签 (会产生 N+1 查询，建议使用预加载)
tags = [link.tag() for link in links]
```
