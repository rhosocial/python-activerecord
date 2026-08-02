# src/rhosocial/activerecord/testsuite/feature/relation/fixtures/models_py312.py
"""
Python 3.12+ fixture model definitions for relation tests.

This file contains model classes using Python 3.12+ syntax features:
- `@override` decorator for inheritance safety
- `Self` type for methods that return an instance of the same class
- `X | Y` syntax (inherited from 3.10+)

Note: This file should only be imported and used in Python 3.12+ environments.
"""
from __future__ import annotations

from typing import ClassVar, Self, override

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation.descriptors import BelongsTo, HasMany, HasOne


# Declare that this module requires Python 3.12+
__requires_python__ = (3, 12)


class Employee(ActiveRecord):
    """Employee model with department relation.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "employees"

    id: int | None = None
    username: str
    department_id: int

    # Define the relation to department
    department: ClassVar[BelongsTo["Department"]] = BelongsTo(
        foreign_key="department_id",
        inverse_of="employees"
    )

    @override
    def save(self, **kwargs) -> Self:
        """Save the employee and return self for chaining."""
        super().save(**kwargs)
        return self

    def transfer_to(self, new_department_id: int) -> Self:
        """Transfer employee to another department and return self for chaining."""
        self.department_id = new_department_id
        return self


class Department(ActiveRecord):
    """Department model with employees relation.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "departments"

    id: int | None = None
    name: str
    description: str = ""

    # Define the relation to employees
    employees: ClassVar[HasMany["Employee"]] = HasMany(
        foreign_key="department_id",
        inverse_of="department"
    )

    @override
    def save(self, **kwargs) -> Self:
        """Save the department and return self for chaining."""
        super().save(**kwargs)
        return self

    def set_description(self, new_description: str) -> Self:
        """Set description and return self for chaining."""
        self.description = new_description
        return self


class Author(ActiveRecord):
    """Author model with books and profile relations.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "authors"

    id: int | None = None
    name: str

    # Relations
    books: ClassVar[HasMany["Book"]] = HasMany(
        foreign_key="author_id",
        inverse_of="author"
    )
    profile: ClassVar[HasOne["Profile"]] = HasOne(
        foreign_key="author_id",
        inverse_of="author"
    )

    @override
    def save(self, **kwargs) -> Self:
        """Save the author and return self for chaining."""
        super().save(**kwargs)
        return self

    def rename(self, new_name: str) -> Self:
        """Rename author and return self for chaining."""
        self.name = new_name
        return self


class Book(ActiveRecord):
    """Book model with author and chapters relations.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "books"

    id: int | None = None
    title: str
    author_id: int

    # Relations
    author: ClassVar[BelongsTo["Author"]] = BelongsTo(
        foreign_key="author_id",
        inverse_of="books"
    )
    chapters: ClassVar[HasMany["Chapter"]] = HasMany(
        foreign_key="book_id",
        inverse_of="book"
    )

    @override
    def save(self, **kwargs) -> Self:
        """Save the book and return self for chaining."""
        super().save(**kwargs)
        return self

    def retitle(self, new_title: str) -> Self:
        """Change book title and return self for chaining."""
        self.title = new_title
        return self


class Chapter(ActiveRecord):
    """Chapter model with book relation.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "chapters"

    id: int | None = None
    title: str
    book_id: int

    # Relations
    book: ClassVar[BelongsTo["Book"]] = BelongsTo(
        foreign_key="book_id",
        inverse_of="chapters"
    )

    @override
    def save(self, **kwargs) -> Self:
        """Save the chapter and return self for chaining."""
        super().save(**kwargs)
        return self

    def rename(self, new_title: str) -> Self:
        """Rename chapter and return self for chaining."""
        self.title = new_title
        return self


class Profile(ActiveRecord):
    """Profile model with author relation.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "profiles"

    id: int | None = None
    bio: str
    author_id: int

    # Relations
    author: ClassVar[BelongsTo["Author"]] = BelongsTo(
        foreign_key="author_id",
        inverse_of="profile"
    )

    @override
    def save(self, **kwargs) -> Self:
        """Save the profile and return self for chaining."""
        super().save(**kwargs)
        return self

    def update_bio(self, new_bio: str) -> Self:
        """Update bio and return self for chaining."""
        self.bio = new_bio
        return self
