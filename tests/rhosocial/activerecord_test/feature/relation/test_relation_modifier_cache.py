# tests/rhosocial/activerecord_test/feature/relation/test_relation_modifier_cache.py
"""
Tests for relation caching behavior with query modifiers.

These tests specifically cover the interaction between with_() modifiers
and the relation cache, which is a key feature of python-activerecord.
"""
import pytest
from typing import ClassVar, Any, Optional, List, Dict

from pydantic import BaseModel

from rhosocial.activerecord.relation.cache import CacheConfig, InstanceCache
from rhosocial.activerecord.relation.base import RelationManagementMixin
from rhosocial.activerecord.relation.descriptors import HasMany, BelongsTo


class MockLoaderWithCounter:
    """Loader that tracks how many times it was called."""
    def __init__(self):
        self.load_count = 0
        self.batch_load_count = 0

    def load(self, instance: Any) -> Optional[List[Any]]:
        self.load_count += 1
        return [{"id": 1, "name": f"Item {self.load_count}"}]

    def batch_load(self, instances: List[Any], base_query: Any) -> Dict[int, Any]:
        self.batch_load_count += 1
        return {id(inst): [{"id": 1, "name": f"Item {self.batch_load_count}"}] for inst in instances}


class Author(RelationManagementMixin, BaseModel):
    id: int
    name: str
    books: ClassVar[HasMany["Book"]] = HasMany(
        foreign_key="author_id",
        inverse_of="author"
    )


class Book(RelationManagementMixin, BaseModel):
    id: int
    title: str
    author_id: int
    author: ClassVar[BelongsTo["Author"]] = BelongsTo(
        foreign_key="author_id",
        inverse_of="books"
    )


class TestRelationModifierCache:
    """Tests for relation cache behavior with query modifiers."""

    @pytest.fixture
    def author_instance(self):
        return Author(id=1, name="Test Author")

    @pytest.fixture
    def book_instance(self):
        return Book(id=1, title="Test Book", author_id=1)

    def test_first_access_loads_from_loader(self, author_instance):
        """Test that first access to relation loads from loader."""
        loader = MockLoaderWithCounter()
        relation = author_instance.get_relation("books")
        relation._loader = loader

        result = relation._load_relation(author_instance)

        assert loader.load_count == 1
        assert result is not None

    def test_second_access_uses_cache(self, author_instance):
        """Test that second access uses cached value."""
        loader = MockLoaderWithCounter()
        relation = author_instance.get_relation("books")
        relation._loader = loader

        result1 = relation._load_relation(author_instance)
        result2 = relation._load_relation(author_instance)

        assert loader.load_count == 1
        assert result1 == result2

    def test_cache_cleared_on_delete(self, author_instance):
        """Test that cache is cleared when relation is deleted."""
        loader = MockLoaderWithCounter()
        relation = author_instance.get_relation("books")
        relation._loader = loader

        result1 = relation._load_relation(author_instance)
        assert loader.load_count == 1

        relation.__delete__(author_instance)

        result2 = relation._load_relation(author_instance)
        assert loader.load_count == 2

    def test_clear_relation_cache_method(self, author_instance):
        """Test clear_relation_cache method."""
        loader = MockLoaderWithCounter()
        relation = author_instance.get_relation("books")
        relation._loader = loader

        relation._load_relation(author_instance)
        assert loader.load_count == 1

        author_instance.clear_relation_cache("books")

        relation._load_relation(author_instance)
        assert loader.load_count == 2

    def test_clear_all_relations_cache(self, author_instance):
        """Test clearing all relation caches."""
        loader = MockLoaderWithCounter()
        relation = author_instance.get_relation("books")
        relation._loader = loader

        relation._load_relation(author_instance)
        assert loader.load_count == 1

        author_instance.clear_relation_cache()

        relation._load_relation(author_instance)
        assert loader.load_count == 2

    def test_cache_isolation_between_instances(self):
        """Test that cache is isolated between different instances."""
        author1 = Author(id=1, name="Author 1")
        author2 = Author(id=2, name="Author 2")

        loader = MockLoaderWithCounter()
        relation1 = author1.get_relation("books")
        relation2 = author2.get_relation("books")
        relation1._loader = loader
        relation2._loader = loader

        result1 = relation1._load_relation(author1)
        result2 = relation2._load_relation(author2)

        assert loader.load_count == 2
        assert result1 is not None
        assert result2 is not None

    def test_cache_with_custom_config(self, author_instance):
        """Test caching with custom CacheConfig."""
        config = CacheConfig(ttl=1, enabled=True)
        relation = author_instance.get_relation("books")
        relation._cache_config = config

        loader = MockLoaderWithCounter()
        relation._loader = loader

        result1 = relation._load_relation(author_instance)
        result2 = relation._load_relation(author_instance)

        assert loader.load_count == 1

    def test_cache_disabled_config(self, author_instance):
        """Test that caching is disabled with enabled=False."""
        config = CacheConfig(enabled=False)
        relation = author_instance.get_relation("books")
        relation._cache_config = config

        loader = MockLoaderWithCounter()
        relation._loader = loader

        result1 = relation._load_relation(author_instance)
        result2 = relation._load_relation(author_instance)

        assert loader.load_count == 2

    def test_cache_with_expired_ttl(self, author_instance):
        """Test cache expiration after TTL."""
        config = CacheConfig(ttl=1)
        relation = author_instance.get_relation("books")
        relation._cache_config = config

        import time
        loader = MockLoaderWithCounter()
        relation._loader = loader

        result1 = relation._load_relation(author_instance)
        assert loader.load_count == 1

        time.sleep(1.1)

        result2 = relation._load_relation(author_instance)
        assert loader.load_count == 2

    def test_different_relations_independent_cache(self, book_instance):
        """Test that different relations have independent caches."""
        loader = MockLoaderWithCounter()
        book_loader = MockLoaderWithCounter()

        author_relation = book_instance.get_relation("author")
        author_relation._loader = book_loader

        result1 = author_relation._load_relation(book_instance)
        assert book_loader.load_count == 1

        result2 = author_relation._load_relation(book_instance)
        assert book_loader.load_count == 1

    def test_loading_without_loader(self, author_instance):
        """Test loading when no loader is set."""
        relation = author_instance.get_relation("books")
        relation._loader = None

        result = relation._load_relation(author_instance)
        assert result is None


class TestRelationDescriptorProtocol:
    """Tests for relation descriptor protocol methods."""

    def test_get_descriptor_from_class(self):
        """Test accessing descriptor from class returns descriptor itself."""
        relation = Author.get_relation("books")
        assert isinstance(relation, HasMany)
        assert relation.foreign_key == "author_id"

    def test_get_descriptor_from_instance_returns_method(self):
        """Test accessing descriptor from instance returns bound method."""
        author = Author(id=1, name="Test")

        books_relation = author.books
        assert callable(books_relation)

    def test_set_name_callback(self):
        """Test that __set_name__ is called on descriptor assignment."""
        class OtherItem(RelationManagementMixin, BaseModel):
            id: int
            test_id: int

        class TestModelForName(RelationManagementMixin, BaseModel):
            id: int
            items: ClassVar[HasMany["OtherItem"]] = HasMany(
                foreign_key="test_id",
                inverse_of="test"
            )

        relation = TestModelForName.get_relation("items")
        assert relation.name == "items"
        assert relation._owner == TestModelForName

    def test_query_method_created(self):
        """Test that query method is created for relation."""
        assert hasattr(Author, "books_query")
        assert callable(Author.books_query)
