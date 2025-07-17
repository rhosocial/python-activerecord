# tests/rhosocial/activerecord_test/relation/conftest.py
"""Test fixtures for the relations package."""

from typing import ClassVar, Any, Optional, List, Dict
import pytest
from pydantic import BaseModel

from src.rhosocial.activerecord.relation.base import RelationManagementMixin
from src.rhosocial.activerecord.relation.cache import CacheConfig
from src.rhosocial.activerecord.relation.descriptors import BelongsTo, HasMany, HasOne
from src.rhosocial.activerecord.relation.interfaces import RelationLoader


class Employee(RelationManagementMixin, BaseModel):
    id: int
    name: str
    department_id: int
    department: ClassVar[BelongsTo["Department"]] = BelongsTo(
        foreign_key="department_id",
        inverse_of="employees"
    )

class Department(RelationManagementMixin, BaseModel):
    id: int
    name: str
    employees: ClassVar[HasMany["Employee"]] = HasMany(
        foreign_key="department_id",
        inverse_of="department"
    )

@pytest.fixture
def employee():
    return Employee(id=1, name="John Doe", department_id=1)

@pytest.fixture
def department():
    return Department(id=1, name="Engineering")

@pytest.fixture
def employee_class():
    return Employee

@pytest.fixture
def department_class():
    return Department


class CustomBookLoader(RelationLoader):
    def load(self, instance: Any) -> Optional[List[Any]]:
        return [Book(id=1, title="Test Book", author_id=instance.id)]

    def batch_load(self, instances: List[Any], base_query: Any) -> Dict[int, Any]:
        pass

class CustomAuthorLoader(RelationLoader):
    def load(self, instance: Any) -> Optional[Any]:
        return Author(id=instance.author_id, name="Test Author")

    def batch_load(self, instances: List[Any], base_query: Any) -> Dict[int, Any]:
        pass

class CustomProfileLoader(RelationLoader):
    def load(self, instance: Any) -> Optional[Any]:
        return Profile(id=1, bio="Test Bio", author_id=instance.id)

    def batch_load(self, instances: List[Any], base_query: Any) -> Dict[int, Any]:
        pass

class CustomChapterLoader(RelationLoader):
    def load(self, instance: Any) -> Optional[List[Any]]:
        return [Chapter(id=1, title="Test Chapter", book_id=instance.id)]

    def batch_load(self, instances: List[Any], base_query: Any) -> Dict[int, Any]:
        pass

class CustomAuthorProfileLoader(RelationLoader):
    def load(self, instance: Any) -> Optional[Any]:
        return Author(id=instance.author_id, name="Test Author")

    def batch_load(self, instances: List[Any], base_query: Any) -> Dict[int, Any]:
        pass

class Author(RelationManagementMixin, BaseModel):
    id: int
    name: str
    books: ClassVar[HasMany["Book"]] = HasMany(
        foreign_key="author_id",
        inverse_of="author",
        loader=CustomBookLoader(),
        cache_config=CacheConfig(ttl=1)
    )
    profile: ClassVar[HasOne["Profile"]] = HasOne(
        foreign_key="author_id",
        inverse_of="author",
        loader=CustomProfileLoader()
    )

class Book(RelationManagementMixin, BaseModel):
    id: int
    title: str
    author_id: int
    author: ClassVar[BelongsTo["Author"]] = BelongsTo(
        foreign_key="author_id",
        inverse_of="books",
        loader=CustomAuthorLoader()
    )
    chapters: ClassVar[HasMany["Chapter"]] = HasMany(
        foreign_key="book_id",
        inverse_of="book",
        loader=CustomChapterLoader()  # Add the loader here
    )

class Chapter(RelationManagementMixin, BaseModel):
    id: int
    title: str
    book_id: int
    book: ClassVar[BelongsTo["Book"]] = BelongsTo(
        foreign_key="book_id",
        inverse_of="chapters"
    )

class Profile(RelationManagementMixin, BaseModel):
    id: int
    bio: str
    author_id: int
    author: ClassVar[BelongsTo["Author"]] = BelongsTo(
        foreign_key="author_id",
        inverse_of="profile",
        loader=CustomAuthorProfileLoader()  # Add loader
    )

@pytest.fixture
def author():
    return Author(id=1, name="Test Author")

@pytest.fixture
def book():
    return Book(id=1, title="Test Book", author_id=1)

@pytest.fixture
def chapter():
    return Chapter(id=1, title="Chapter 1", book_id=1)

@pytest.fixture
def profile():
    return Profile(id=1, bio="Test Bio", author_id=1)