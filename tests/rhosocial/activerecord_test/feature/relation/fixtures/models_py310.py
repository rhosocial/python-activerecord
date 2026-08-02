# src/rhosocial/activerecord/testsuite/feature/relation/fixtures/models_py310.py
"""
Python 3.10+ fixture model definitions for relation tests.

This file contains model classes using Python 3.10+ syntax features:
- `X | Y` syntax instead of `Optional[X]` or `Union[X, Y]`

Note: This file should only be imported and used in Python 3.10+ environments.
"""
from typing import ClassVar

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation.descriptors import BelongsTo, HasMany, HasOne


# Declare that this module requires Python 3.10+
__requires_python__ = (3, 10)


class Employee(ActiveRecord):
    """Employee model with department relation.

    Python 3.10+ version.
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


class Department(ActiveRecord):
    """Department model with employees relation.

    Python 3.10+ version.
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


class Author(ActiveRecord):
    """Author model with books and profile relations.

    Python 3.10+ version.
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


class Book(ActiveRecord):
    """Book model with author and chapters relations.

    Python 3.10+ version.
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


class Chapter(ActiveRecord):
    """Chapter model with book relation.

    Python 3.10+ version.
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


class Profile(ActiveRecord):
    """Profile model with author relation.

    Python 3.10+ version.
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
