# docs/examples/chapter_13_cli/models.py
"""Models shared by the command-line examples.

The CLI imports these classes by reference, for example ``models:User``.
Nothing here calls ``configure()``: each example passes the backend and
connection classes on the command line instead, which is the pattern to use
when a project keeps configuration decisions outside the model module.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Optional

from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import ReadOnlyMixin, SoftDeleteMixin
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.query import CTEQuery


class User(ActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    age: int = 0


class Admin(ActiveRecord):
    __table_name__ = "admins"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    age: int = 0


class ReadOnlyUser(ActiveRecord, ReadOnlyMixin):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    age: int = 0


class Task(SoftDeleteMixin, ActiveRecord):
    __table_name__ = "tasks"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    title: str
    done: bool = False
    deleted_at: Optional[datetime] = None


def create_schema(database):
    """Create the demo tables and seed rows in a fresh SQLite file."""
    conn = sqlite3.connect(str(database))
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
        "email TEXT, age INTEGER DEFAULT 0)"
    )
    conn.execute(
        "CREATE TABLE admins (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
        "email TEXT, age INTEGER DEFAULT 0)"
    )
    conn.execute(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, "
        "done INTEGER DEFAULT 0, deleted_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO users (id, name, email, age) VALUES (?, ?, ?, ?)",
        [
            (1, "Alice", "alice@example.com", 30),
            (2, "Bob", "bob@example.com", 25),
            (3, "Carol", "carol@example.com", 40),
            (4, "Dan", "dan@example.com", 22),
        ],
    )
    conn.executemany(
        "INSERT INTO admins (id, name, email, age) VALUES (?, ?, ?, ?)",
        [(10, "Erin", "erin@example.com", 35), (11, "Frank", "frank@example.com", 30)],
    )
    conn.executemany(
        "INSERT INTO tasks (id, title, done) VALUES (?, ?, ?)",
        [(1, "Write docs", 0), (2, "Review CLI", 1)],
    )
    conn.commit()
    conn.close()


def active_users():
    """Query factory for ``dql run``; returns an ``ActiveQuery``."""
    return User.query().where(User.c.age >= 30)


def user_union():
    """Set-operation factory for ``set run``."""
    return User.query().where(User.c.age == 30).union(
        User.query().where(User.c.age == 40)
    )


def older_users_cte():
    """CTE factory for ``cte run``."""
    cte = CTEQuery(User.backend())
    cte.with_cte("older_users", User.query().where(User.c.age >= 30))
    return cte.from_cte("older_users")


def temporary_database(directory):
    """Return a database path inside ``directory``, already seeded."""
    database = Path(directory) / "cli_examples.db"
    create_schema(database)
    return database
