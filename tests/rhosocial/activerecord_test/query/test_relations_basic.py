# tests/rhosocial/activerecord_test/query/test_relations_basic.py
"""Test cases for basic relation definition functionality."""
from decimal import Decimal
from typing import ClassVar, Optional

import pytest
from pydantic import EmailStr

from src.rhosocial.activerecord import ActiveRecord
from src.rhosocial.activerecord.relation import BelongsTo, CacheConfig, HasMany, HasOne
from .utils import create_order_fixtures, create_blog_fixtures

order_fixtures = create_order_fixtures()


def test_relation_required_params(order_fixtures):
    """Test relation definition with missing required parameters."""
    User, _, _ = order_fixtures

    # Test missing related_model
    import pydantic
    with pytest.raises(pydantic.errors.PydanticUserError, match="All model fields require a type annotation"):
        class InvalidOrder(ActiveRecord):
            user = BelongsTo(foreign_key='user_id')

    # Test missing foreign_key
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'foreign_key'"):
        class InvalidOrder(ActiveRecord):
            user: ClassVar[BelongsTo['User']] = BelongsTo()


def test_relation_param_types(order_fixtures):
    """Test relation definition with invalid parameter types."""
    User, _, _ = order_fixtures

    # Test invalid foreign_key type
    with pytest.raises(TypeError, match="foreign_key must be a string"):
        class InvalidOrder(ActiveRecord):
            user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key=123)

    # Test invalid cache_config type
    with pytest.raises(TypeError, match="cache_config must be instance of CacheConfig"):
        class InvalidOrder(ActiveRecord):
            user: ClassVar[BelongsTo['User']] = BelongsTo(
                foreign_key='user_id',
                cache_config={'ttl': 300}  # Should be CacheConfig instance
            )


def test_relation_inheritance(order_fixtures):
    """Test relation inheritance and override behavior."""
    User, Order, _ = order_fixtures

    # Define base class with relation
    class BaseOrder(ActiveRecord):
        __table_name__ = 'orders'
        __backend__ = Order.__backend__
        user: ClassVar[BelongsTo['User']] = BelongsTo(
            foreign_key='user_id'
        )

    # Override relation in child class
    class CustomOrder(BaseOrder):
        user: ClassVar[BelongsTo['User']] = BelongsTo(
            foreign_key='user_id',
            cache_config=CacheConfig(ttl=60)
        )

    # Create instances and verify relations
    base_order = BaseOrder(
        user_id=1,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    custom_order = CustomOrder(
        user_id=1,
        order_number='ORD-002',
        total_amount=Decimal('100.00')
    )

    # Verify relation configurations
    # assert not hasattr(base_order.user.cache_config, 'ttl')
    # assert custom_order.user.cache_config.ttl == 60


# New test cases for RelationManagementMixin
def test_relation_registration():
    """Test basic relation registration functionality."""

    class User(ActiveRecord):
        __table_name__ = "users"
        id: Optional[int] = None
        username: str
        email: EmailStr

    class Post(ActiveRecord):
        __table_name__ = "posts"
        id: Optional[int] = None
        user_id: int
        title: str

        user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')

    # Test relation registration
    assert 'user' in Post._ensure_relations()
    assert isinstance(Post.get_relation('user'), BelongsTo)
    assert 'user' in Post.get_relations()


def test_relation_cache_management():
    """Test relation cache management."""

    class User(ActiveRecord):
        __table_name__ = "users"
        id: Optional[int] = None
        username: str
        email: EmailStr

    class Post(ActiveRecord):
        __table_name__ = "posts"
        id: Optional[int] = None
        user_id: int
        title: str

        user: ClassVar[BelongsTo['User']] = BelongsTo(
            foreign_key='user_id',
            cache_config=CacheConfig(ttl=60)
        )

    post = Post(user_id=1, title="Test Post")

    # Test cache clearing
    post.clear_relation_cache('user')
    with pytest.raises(ValueError):
        post.clear_relation_cache('invalid_relation')

    # Test clearing all caches
    post.clear_relation_cache()


# Test cases for RelationDescriptor
def test_relation_descriptor_initialization():
    """Test RelationDescriptor initialization and configuration."""

    class User(ActiveRecord):
        __table_name__ = "users"
        id: Optional[int] = None
        username: str
        email: EmailStr

    class Post(ActiveRecord):
        __table_name__ = "posts"
        id: Optional[int] = None
        user_id: int
        title: str

        # Test basic initialization
        user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')

        # Test with cache config
        cached_user: ClassVar[BelongsTo['User']] = BelongsTo(
            foreign_key='user_id',
            cache_config=CacheConfig(ttl=60)
        )

    assert Post.get_relation('user').foreign_key == 'user_id'
    assert Post.get_relation('cached_user').foreign_key == 'user_id'


def test_belongs_to_relation():
    """Test BelongsTo relation functionality."""

    class User(ActiveRecord):
        __table_name__ = "users"
        id: Optional[int] = None
        username: str
        email: EmailStr

    class Post(ActiveRecord):
        __table_name__ = "posts"
        id: Optional[int] = None
        user_id: int
        title: str

        author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')

    relation = Post.get_relation('author')
    assert isinstance(relation, BelongsTo)
    assert relation.foreign_key == 'user_id'


def test_has_many_relation():
    """Test HasMany relation functionality."""

    class Comment(ActiveRecord):
        __table_name__ = "comments"
        id: Optional[int] = None
        post_id: int
        content: str

    class Post(ActiveRecord):
        __table_name__ = "posts"
        id: Optional[int] = None
        title: str

        comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id')

    relation = Post.get_relation('comments')
    assert isinstance(relation, HasMany)
    assert relation.foreign_key == 'post_id'


def test_has_one_relation():
    """Test HasOne relation functionality."""

    class Profile(ActiveRecord):
        __table_name__ = "profiles"
        id: Optional[int] = None
        user_id: int
        bio: str

    class User(ActiveRecord):
        __table_name__ = "users"
        id: Optional[int] = None
        username: str

        profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id')

    relation = User.get_relation('profile')
    assert isinstance(relation, HasOne)
    assert relation.foreign_key == 'user_id'


def test_multiple_relations_on_model():
    """Test multiple relations on a single model."""

    class User(ActiveRecord):
        __table_name__ = "users"
        id: Optional[int] = None
        username: str

    class Comment(ActiveRecord):
        __table_name__ = "comments"
        id: Optional[int] = None
        post_id: int
        content: str

    class Post(ActiveRecord):
        __table_name__ = "posts"
        id: Optional[int] = None
        user_id: int
        title: str

        author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')
        comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id')

    relations = Post.get_relations()
    assert 'author' in relations
    assert 'comments' in relations

    assert isinstance(Post.get_relation('author'), BelongsTo)
    assert isinstance(Post.get_relation('comments'), HasMany)


def test_relation_inverse_of():
    """Test inverse_of relation configuration."""

    class User(ActiveRecord):
        __table_name__ = "users"
        id: Optional[int] = None
        username: str

        posts: ClassVar[HasMany['Post']] = HasMany(
            foreign_key='user_id',
            inverse_of='author'
        )

    class Post(ActiveRecord):
        __table_name__ = "posts"
        id: Optional[int] = None
        user_id: int
        title: str

        author: ClassVar[BelongsTo['User']] = BelongsTo(
            foreign_key='user_id',
            inverse_of='posts'
        )

    user_relation = Post.get_relation('author')
    post_relation = User.get_relation('posts')

    assert user_relation.inverse_of == 'posts'
    assert post_relation.inverse_of == 'author'


def test_relation_query_method():
    """Test relation query method generation."""

    class User(ActiveRecord):
        __table_name__ = "users"
        id: Optional[int] = None
        username: str

    class Post(ActiveRecord):
        __table_name__ = "posts"
        id: Optional[int] = None
        user_id: int
        title: str

        author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')

    # Verify query method existence
    assert hasattr(Post, 'author_query')
    assert callable(getattr(Post, 'author_query'))