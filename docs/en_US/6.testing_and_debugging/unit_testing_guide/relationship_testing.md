# Query and Association Testing

Currently, rhosocial ActiveRecord has limited relationship testing capabilities. The system supports basic model associations but comprehensive relationship testing is not yet available in the testing framework.

## Current State

- Basic foreign key relationship support
- Simple lookup operations
- No advanced relationship querying capabilities

## Testing Simple Associations

For the limited relationship functionality that exists:

```python
import unittest
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    name: str

class Post(ActiveRecord):
    title: str
    user_id: int  # Simple foreign key approach

class TestBasicAssociation(unittest.TestCase):
    def test_foreign_key_assignment(self):
        user = User(name="Test User")
        user.save()
        
        post = Post(title="Test Post", user_id=user.id)
        post.save()
        
        # Verify the foreign key was set correctly
        self.assertEqual(post.user_id, user.id)
```

## Limitations

The current implementation does not include:
- Relationship method testing (like has_many, belongs_to methods)
- Complex association queries
- Eager loading verification
- Nested relationship testing
- Many-to-many relationship testing

Relationship testing capabilities will be expanded when relationship functionality is fully implemented.

## Setting Up Relationship Tests

### Test Fixtures for Related Models

When testing relationships, you need fixtures for all related models:

```python
import pytest
from rhosocial.activerecord.backend import SQLiteBackend
from your_app.models import User, Post, Comment, Tag

@pytest.fixture
def db_connection():
    """Create a test database connection."""
    connection = SQLiteBackend(":memory:")
    # Create all necessary tables
    User.create_table(connection)
    Post.create_table(connection)
    Comment.create_table(connection)
    Tag.create_table(connection)
    # For many-to-many relationships
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
    """Create related model instances for testing."""
    # Create a user
    user = User(username="test_user", email="test@example.com")
    user.save()
    
    # Create posts for the user
    post1 = Post(user_id=user.id, title="First Post", content="Content 1")
    post1.save()
    
    post2 = Post(user_id=user.id, title="Second Post", content="Content 2")
    post2.save()
    
    # Create comments for the first post
    comment1 = Comment(post_id=post1.id, user_id=user.id, content="Comment 1")
    comment1.save()
    
    comment2 = Comment(post_id=post1.id, user_id=user.id, content="Comment 2")
    comment2.save()
    
    # Create tags and associate with posts
    tag1 = Tag(name="Tag1")
    tag1.save()
    
    tag2 = Tag(name="Tag2")
    tag2.save()
    
    # Associate tags with posts (many-to-many)
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

## Testing One-to-One Relationships

One-to-one relationships connect one record to exactly one other record:

```python
def test_one_to_one_relationship(db_connection):
    """Test one-to-one relationship between User and Profile."""
    # Create a user
    user = User(username="profile_test", email="profile@example.com")
    user.save()
    
    # Create a profile for the user
    profile = Profile(user_id=user.id, bio="Test bio", website="https://example.com")
    profile.save()
    
    # Test accessing profile from user
    user_profile = user.profile
    assert user_profile is not None
    assert user_profile.id == profile.id
    assert user_profile.bio == "Test bio"
    
    # Test accessing user from profile
    profile_user = profile.user
    assert profile_user is not None
    assert profile_user.id == user.id
    assert profile_user.username == "profile_test"
    
    # Test updating through relationship
    user_profile.bio = "Updated bio"
    user_profile.save()
    
    # Verify update
    refreshed_profile = Profile.find_by_id(profile.id)
    assert refreshed_profile.bio == "Updated bio"
```

## Testing One-to-Many Relationships

One-to-many relationships connect one record to multiple related records:

```python
def test_one_to_many_relationship(relationship_fixtures):
    """Test one-to-many relationship between User and Posts."""
    user = relationship_fixtures["user"]
    posts = relationship_fixtures["posts"]
    
    # Test accessing posts from user
    user_posts = user.posts
    assert len(user_posts) == 2
    assert user_posts[0].title in ["First Post", "Second Post"]
    assert user_posts[1].title in ["First Post", "Second Post"]
    
    # Test accessing user from post
    post_user = posts[0].user
    assert post_user is not None
    assert post_user.id == user.id
    assert post_user.username == "test_user"
    
    # Test adding a new post to the relationship
    new_post = Post(title="Third Post", content="Content 3")
    user.posts.append(new_post)
    new_post.save()
    
    # Verify the new post was added to the relationship
    updated_posts = user.posts
    assert len(updated_posts) == 3
    assert any(post.title == "Third Post" for post in updated_posts)
    
    # Test cascading delete (if implemented)
    if hasattr(User, "cascade_delete") and User.cascade_delete:
        user.delete()
        # Verify all posts are deleted
        for post in posts:
            assert Post.find_by_id(post.id) is None
```

## Testing Many-to-Many Relationships

Many-to-many relationships connect records where each can be related to multiple instances of the other:

```python
def test_many_to_many_relationship(relationship_fixtures, db_connection):
    """Test many-to-many relationship between Posts and Tags."""
    posts = relationship_fixtures["posts"]
    tags = relationship_fixtures["tags"]
    
    # Assuming you have a method to get tags for a post
    post_tags = posts[0].tags
    assert len(post_tags) == 2
    assert post_tags[0].name in ["Tag1", "Tag2"]
    assert post_tags[1].name in ["Tag1", "Tag2"]
    
    # Test posts for a specific tag
    tag_posts = tags[0].posts
    assert len(tag_posts) == 2
    assert tag_posts[0].id in [posts[0].id, posts[1].id]
    assert tag_posts[1].id in [posts[0].id, posts[1].id]
    
    # Test adding a new tag to a post
    new_tag = Tag(name="Tag3")
    new_tag.save()
    
    # Associate the new tag with the first post
    db_connection.execute(
        "INSERT INTO post_tags (post_id, tag_id) VALUES (?, ?)",
        [posts[0].id, new_tag.id]
    )
    
    # Verify the new tag was added to the post's tags
    updated_post_tags = posts[0].tags
    assert len(updated_post_tags) == 3
    assert any(tag.name == "Tag3" for tag in updated_post_tags)
    
    # Test removing a tag from a post
    db_connection.execute(
        "DELETE FROM post_tags WHERE post_id = ? AND tag_id = ?",
        [posts[0].id, tags[0].id]
    )
    
    # Verify the tag was removed
    updated_post_tags = posts[0].tags
    assert len(updated_post_tags) == 2
    assert all(tag.id != tags[0].id for tag in updated_post_tags)
```

## Testing Polymorphic Relationships

Polymorphic relationships allow a model to belong to more than one type of model:

```python
def test_polymorphic_relationship(db_connection):
    """Test polymorphic relationship for comments on different content types."""
    # Create a user
    user = User(username="poly_test", email="poly@example.com")
    user.save()
    
    # Create a post and a photo (different commentable types)
    post = Post(user_id=user.id, title="Polymorphic Post", content="Post content")
    post.save()
    
    photo = Photo(user_id=user.id, title="Polymorphic Photo", url="/path/to/photo.jpg")
    photo.save()
    
    # Create comments for both types
    post_comment = Comment(
        user_id=user.id,
        commentable_id=post.id,
        commentable_type="Post",
        content="Comment on post"
    )
    post_comment.save()
    
    photo_comment = Comment(
        user_id=user.id,
        commentable_id=photo.id,
        commentable_type="Photo",
        content="Comment on photo"
    )
    photo_comment.save()
    
    # Test accessing comments from different parent types
    post_comments = post.comments
    assert len(post_comments) == 1
    assert post_comments[0].content == "Comment on post"
    
    photo_comments = photo.comments
    assert len(photo_comments) == 1
    assert photo_comments[0].content == "Comment on photo"
    
    # Test accessing parent from comment
    comment_post = post_comment.commentable
    assert comment_post is not None
    assert comment_post.id == post.id
    assert comment_post.title == "Polymorphic Post"
    
    comment_photo = photo_comment.commentable
    assert comment_photo is not None
    assert comment_photo.id == photo.id
    assert comment_photo.title == "Polymorphic Photo"
```

## Testing Self-Referential Relationships

Self-referential relationships connect records of the same model type:

```python
def test_self_referential_relationship(db_connection):
    """Test self-referential relationship for hierarchical categories."""
    # Create parent categories
    parent1 = Category(name="Parent 1")
    parent1.save()
    
    parent2 = Category(name="Parent 2")
    parent2.save()
    
    # Create child categories
    child1 = Category(name="Child 1", parent_id=parent1.id)
    child1.save()
    
    child2 = Category(name="Child 2", parent_id=parent1.id)
    child2.save()
    
    child3 = Category(name="Child 3", parent_id=parent2.id)
    child3.save()
    
    # Create a grandchild category
    grandchild = Category(name="Grandchild", parent_id=child1.id)
    grandchild.save()
    
    # Test parent-child relationship
    parent1_children = parent1.children
    assert len(parent1_children) == 2
    assert parent1_children[0].name in ["Child 1", "Child 2"]
    assert parent1_children[1].name in ["Child 1", "Child 2"]
    
    # Test child-parent relationship
    child1_parent = child1.parent
    assert child1_parent is not None
    assert child1_parent.id == parent1.id
    assert child1_parent.name == "Parent 1"
    
    # Test multi-level relationship
    grandchild_parent = grandchild.parent
    assert grandchild_parent is not None
    assert grandchild_parent.id == child1.id
    assert grandchild_parent.name == "Child 1"
    
    # Test recursive relationship traversal (if implemented)
    if hasattr(Category, "ancestors"):
        grandchild_ancestors = grandchild.ancestors()
        assert len(grandchild_ancestors) == 2
        assert grandchild_ancestors[0].id == child1.id
        assert grandchild_ancestors[1].id == parent1.id
```

## Testing Eager Loading

Test that eager loading correctly loads related records:

```python
def test_eager_loading(relationship_fixtures):
    """Test eager loading of relationships."""
    user_id = relationship_fixtures["user"].id
    
    # Test eager loading of posts with comments
    user_with_posts = User.with_("posts").find_by_id(user_id)
    assert hasattr(user_with_posts, "_loaded_relations")
    assert "posts" in user_with_posts._loaded_relations
    
    # Access posts without additional queries
    posts = user_with_posts.posts
    assert len(posts) == 2
    
    # Test nested eager loading
    user_with_posts_and_comments = User.with_("posts.comments").find_by_id(user_id)
    posts = user_with_posts_and_comments.posts
    
    # Access comments without additional queries
    for post in posts:
        if post.id == relationship_fixtures["posts"][0].id:
            assert len(post.comments) == 2
```

## Best Practices for Relationship Testing

1. **Test Both Directions**: For bidirectional relationships, test both sides of the association.

2. **Test Cascading Operations**: If your relationships have cascading behavior (e.g., cascading deletes), test that they work correctly.

3. **Test Validation Rules**: Test that relationship validation rules (e.g., required associations) work as expected.

4. **Test Edge Cases**: Test relationships with null foreign keys, missing related records, and other edge cases.

5. **Test Eager Loading**: Verify that eager loading correctly loads related records and improves performance.

6. **Test Custom Relationship Methods**: If you've added custom methods to your relationships, test them thoroughly.

7. **Use Transactions**: Wrap relationship tests in transactions to ensure test isolation.

8. **Test Performance**: For applications with complex relationships, include performance tests to ensure efficient loading of related records.