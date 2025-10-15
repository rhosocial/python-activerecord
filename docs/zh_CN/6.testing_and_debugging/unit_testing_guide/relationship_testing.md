# 查询和关联测试

当前，rhosocial ActiveRecord 在关系测试方面功能有限。系统支持基本模型关联，但测试框架中尚未提供全面的关系测试功能。

## 当前状态

- 基本外键关系支持
- 简单查找操作
- 无高级关系查询功能

## 测试简单关联

对于现有的有限关系功能：

```python
import unittest
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    name: str

class Post(ActiveRecord):
    title: str
    user_id: int  # 简单外键方法

class TestBasicAssociation(unittest.TestCase):
    def test_foreign_key_assignment(self):
        user = User(name="测试用户")
        user.save()
        
        post = Post(title="测试帖子", user_id=user.id)
        post.save()
        
        # 验证外键正确设置
        self.assertEqual(post.user_id, user.id)
```

## 限制

当前实现不包括：
- 关系方法测试（如has_many, belongs_to方法）
- 复杂关联查询
- 预加载验证
- 嵌套关系测试
- 多对多关系测试

关系测试功能将在关系功能完全实现后扩展。

## 设置关系测试

### 相关模型的测试夹具

测试关系时，您需要为所有相关模型创建夹具：

```python
import pytest
from rhosocial.activerecord.backend import SQLiteBackend
from your_app.models import User, Post, Comment, Tag

@pytest.fixture
def db_connection():
    """创建测试数据库连接。"""
    connection = SQLiteBackend(":memory:")
    # 创建所有必要的表
    User.create_table(connection)
    Post.create_table(connection)
    Comment.create_table(connection)
    Tag.create_table(connection)
    # 对于多对多关系
    connection.execute("""
        CREATE TABLE post_tags (
            post_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (post_id, tag_id)
        )
    """)
    yield connection

@pytest.fixture
def relationship_fixtures(db_connection):
    """创建用于测试的相关模型实例。"""
    # 创建用户
    user = User(username="test_user", email="test@example.com")
    user.save()
    
    # 为用户创建文章
    post1 = Post(user_id=user.id, title="第一篇文章", content="内容1")
    post1.save()
    
    post2 = Post(user_id=user.id, title="第二篇文章", content="内容2")
    post2.save()
    
    # 为第一篇文章创建评论
    comment1 = Comment(post_id=post1.id, user_id=user.id, content="评论1")
    comment1.save()
    
    comment2 = Comment(post_id=post1.id, user_id=user.id, content="评论2")
    comment2.save()
    
    # 创建标签并与文章关联
    tag1 = Tag(name="标签1")
    tag1.save()
    
    tag2 = Tag(name="标签2")
    tag2.save()
    
    # 将标签与文章关联（多对多）
    db_connection.execute(
        "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)",
        [post1.id, tag1.id]
    )
    db_connection.execute(
        "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)",
        [post1.id, tag2.id]
    )
    db_connection.execute(
        "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)",
        [post2.id, tag1.id]
    )
    
    return {
        "user": user,
        "posts": [post1, post2],
        "comments": [comment1, comment2],
        "tags": [tag1, tag2]
    }
```

## 测试一对一关系

一对一关系将一条记录连接到恰好一条其他记录：

```python
def test_one_to_one_relationship(db_connection):
    """测试用户和个人资料之间的一对一关系。"""
    # 创建用户
    user = User(username="profile_test", email="profile@example.com")
    user.save()
    
    # 为用户创建个人资料
    profile = Profile(user_id=user.id, bio="测试简介", website="https://example.com")
    profile.save()
    
    # 测试从用户访问个人资料
    user_profile = user.profile
    assert user_profile is not None
    assert user_profile.id == profile.id
    assert user_profile.bio == "测试简介"
    
    # 测试从个人资料访问用户
    profile_user = profile.user
    assert profile_user is not None
    assert profile_user.id == user.id
    assert profile_user.username == "profile_test"
    
    # 测试通过关系更新
    user_profile.bio = "更新的简介"
    user_profile.save()
    
    # 验证更新
    refreshed_profile = Profile.find_by_id(profile.id)
    assert refreshed_profile.bio == "更新的简介"
```

## 测试一对多关系

一对多关系将一条记录连接到多条相关记录：

```python
def test_one_to_many_relationship(relationship_fixtures):
    """测试用户和文章之间的一对多关系。"""
    user = relationship_fixtures["user"]
    posts = relationship_fixtures["posts"]
    
    # 测试从用户访问文章
    user_posts = user.posts
    assert len(user_posts) == 2
    assert user_posts[0].title in ["第一篇文章", "第二篇文章"]
    assert user_posts[1].title in ["第一篇文章", "第二篇文章"]
    
    # 测试从文章访问用户
    post_user = posts[0].user
    assert post_user is not None
    assert post_user.id == user.id
    assert post_user.username == "test_user"
    
    # 测试向关系中添加新文章
    new_post = Post(title="第三篇文章", content="内容3")
    user.posts.append(new_post)
    new_post.save()
    
    # 验证新文章已添加到关系中
    updated_posts = user.posts
    assert len(updated_posts) == 3
    assert any(post.title == "第三篇文章" for post in updated_posts)
    
    # 测试级联删除（如果已实现）
    if hasattr(User, "cascade_delete") and User.cascade_delete:
        user.delete()
        # 验证所有文章都已删除
        for post in posts:
            assert Post.find_by_id(post.id) is None
```

## 测试多对多关系

多对多关系连接记录，其中每条记录可以与另一类型的多个实例相关联：

```python
def test_many_to_many_relationship(relationship_fixtures, db_connection):
    """测试文章和标签之间的多对多关系。"""
    posts = relationship_fixtures["posts"]
    tags = relationship_fixtures["tags"]
    
    # 假设您有一个方法来获取文章的标签
    post_tags = posts[0].tags
    assert len(post_tags) == 2
    assert post_tags[0].name in ["标签1", "标签2"]
    assert post_tags[1].name in ["标签1", "标签2"]
    
    # 测试特定标签的文章
    tag_posts = tags[0].posts
    assert len(tag_posts) == 2
    assert tag_posts[0].id in [posts[0].id, posts[1].id]
    assert tag_posts[1].id in [posts[0].id, posts[1].id]
    
    # 测试向文章添加新标签
    new_tag = Tag(name="标签3")
    new_tag.save()
    
    # 将新标签与第一篇文章关联
    db_connection.execute(
        "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)",
        [posts[0].id, new_tag.id]
    )
    
    # 验证新标签已添加到文章的标签中
    updated_post_tags = posts[0].tags
    assert len(updated_post_tags) == 3
    assert any(tag.name == "标签3" for tag in updated_post_tags)
    
    # 测试从文章中移除标签
    db_connection.execute(
        "DELETE FROM post_tags WHERE post_id = ? AND tag_id = ?",
        [posts[0].id, tags[0].id]
    )
    
    # 验证标签已被移除
    updated_post_tags = posts[0].tags
    assert len(updated_post_tags) == 2
    assert all(tag.id != tags[0].id for tag in updated_post_tags)
```

## 测试多态关系

多态关系允许模型属于多种类型的模型：

```python
def test_polymorphic_relationship(db_connection):
    """测试不同内容类型评论的多态关系。"""
    # 创建用户
    user = User(username="poly_test", email="poly@example.com")
    user.save()
    
    # 创建文章和照片（不同的可评论类型）
    post = Post(user_id=user.id, title="多态文章", content="文章内容")
    post.save()
    
    photo = Photo(user_id=user.id, title="多态照片", url="/path/to/photo.jpg")
    photo.save()
    
    # 为两种类型创建评论
    post_comment = Comment(
        user_id=user.id,
        commentable_id=post.id,
        commentable_type="Post",
        content="文章评论"
    )
    post_comment.save()
    
    photo_comment = Comment(
        user_id=user.id,
        commentable_id=photo.id,
        commentable_type="Photo",
        content="照片评论"
    )
    photo_comment.save()
    
    # 测试从不同父类型访问评论
    post_comments = post.comments
    assert len(post_comments) == 1
    assert post_comments[0].content == "文章评论"
    
    photo_comments = photo.comments
    assert len(photo_comments) == 1
    assert photo_comments[0].content == "照片评论"
    
    # 测试从评论访问父级
    comment_post = post_comment.commentable
    assert comment_post is not None
    assert comment_post.id == post.id
    assert comment_post.title == "多态文章"
    
    comment_photo = photo_comment.commentable
    assert comment_photo is not None
    assert comment_photo.id == photo.id
    assert comment_photo.title == "多态照片"
```

## 测试自引用关系

自引用关系连接同一模型类型的记录：

```python
def test_self_referential_relationship(db_connection):
    """测试分层类别的自引用关系。"""
    # 创建父类别
    parent1 = Category(name="父类别1")
    parent1.save()
    
    parent2 = Category(name="父类别2")
    parent2.save()
    
    # 创建子类别
    child1 = Category(name="子类别1", parent_id=parent1.id)
    child1.save()
    
    child2 = Category(name="子类别2", parent_id=parent1.id)
    child2.save()
    
    child3 = Category(name="子类别3", parent_id=parent2.id)
    child3.save()
    
    # 创建孙类别
    grandchild = Category(name="孙类别", parent_id=child1.id)
    grandchild.save()
    
    # 测试父子关系
    parent1_children = parent1.children
    assert len(parent1_children) == 2
    assert parent1_children[0].name in ["子类别1", "子类别2"]
    assert parent1_children[1].name in ["子类别1", "子类别2"]
    
    # 测试子父关系
    child1_parent = child1.parent
    assert child1_parent is not None
    assert child1_parent.id == parent1.id
    assert child1_parent.name == "父类别1"
    
    # 测试多级关系
    grandchild_parent = grandchild.parent
    assert grandchild_parent is not None
    assert grandchild_parent.id == child1.id
    assert grandchild_parent.name == "子类别1"
    
    # 测试递归关系遍历（如果已实现）
    if hasattr(Category, "ancestors"):
        grandchild_ancestors = grandchild.ancestors()
        assert len(grandchild_ancestors) == 2
        assert grandchild_ancestors[0].id == child1.id
        assert grandchild_ancestors[1].id == parent1.id
```

## 测试预加载

测试预加载正确加载相关记录：

```python
def test_eager_loading(relationship_fixtures):
    """测试关系的预加载。"""
    user_id = relationship_fixtures["user"].id
    
    # 测试文章的预加载
    user_with_posts = User.with_("posts").find_by_id(user_id)
    assert hasattr(user_with_posts, "_loaded_relations")
    assert "posts" in user_with_posts._loaded_relations
    
    # 无需额外查询即可访问文章
    posts = user_with_posts.posts
    assert len(posts) == 2
    
    # 测试嵌套预加载
    user_with_posts_and_comments = User.with_("posts.comments").find_by_id(user_id)
    posts = user_with_posts_and_comments.posts
    
    # 无需额外查询即可访问评论
    for post in posts:
        if post.id == relationship_fixtures["posts"][0].id:
            assert len(post.comments) == 2
```

## 关系测试的最佳实践

1. **测试双向关系**：对于双向关系，测试关联的两侧。

2. **测试级联操作**：如果您的关系具有级联行为（例如级联删除），测试它们是否正确工作。

3. **测试验证规则**：测试关系验证规则（例如必需的关联）是否按预期工作。

4. **测试边缘情况**：测试具有空外键、缺少相关记录和其他边缘情况的关系。

5. **测试预加载**：验证预加载正确加载相关记录并提高性能。

6. **测试自定义关系方法**：如果您向关系添加了自定义方法，请彻底测试它们。

7. **使用事务**：将关系测试包装在事务中以确保测试隔离。

8. **测试性能**：对于具有复杂关系的应用程序，包括性能测试以确保高效加载相关记录。