# tests/rhosocial/activerecord_test/feature/cli/conftest.py
"""Shared fixtures for the ActiveRecord CLI feature tests."""

import io
import sqlite3
import textwrap
import uuid
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace

import pytest

from rhosocial.activerecord.cli import main

from logging_isolation import preserve_logging

SQLITE_BACKEND = "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend"
ASYNC_SQLITE_BACKEND = (
    "rhosocial.activerecord.backend.impl.sqlite.backend:AsyncSQLiteBackend"
)
SQLITE_CONFIG = (
    "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig"
)


def connection_args(database, backend=SQLITE_BACKEND):
    """Build the explicit backend, config class, and database arguments."""
    return [
        "--backend-class",
        backend,
        "--config-class",
        SQLITE_CONFIG,
        "--config",
        f"database={database}",
    ]


def run_cli(argv, capture=True):
    """Run the CLI in-process and return (exit_code, stdout, stderr)."""
    with preserve_logging():
        if not capture:
            try:
                return main(argv), "", ""
            except SystemExit as exc:
                return (exc.code if exc.code is not None else 0), "", ""
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code if exc.code is not None else 0
        return code, out.getvalue(), err.getvalue()


def write_module(path, module_name, body):
    (path / f"{module_name}.py").write_text(textwrap.dedent(body), encoding="utf-8")


def create_users_table(database, rows=None):
    if rows is None:
        rows = (
            (1, "Alice", "alice@example.com", 30),
            (2, "Bob", "bob@example.com", 25),
            (3, "Alice", "alice2@example.com", 40),
            (4, "Dan", "dan@example.com", 22),
        )
    conn = sqlite3.connect(str(database))
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
        "email TEXT, age INTEGER DEFAULT 0, deleted_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO users (id, name, email, age) VALUES (?, ?, ?, ?)", rows
    )
    conn.commit()
    conn.close()


def create_order_items_table(database):
    conn = sqlite3.connect(str(database))
    conn.execute(
        "CREATE TABLE order_items (order_id INTEGER, product_id INTEGER, "
        "note TEXT DEFAULT '', PRIMARY KEY (order_id, product_id))"
    )
    conn.executemany(
        "INSERT INTO order_items (order_id, product_id, note) VALUES (?, ?, ?)",
        [(1, 101, "first"), (1, 102, "second"), (2, 101, "third")],
    )
    conn.commit()
    conn.close()


MODEL_BODY = """
from datetime import datetime
from typing import ClassVar, Optional

from pydantic import Field, field_validator, model_validator

from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import (
    AsyncSoftDeleteMixin,
    ReadOnlyMixin,
    SoftDeleteMixin,
)
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.query import AsyncCTEQuery, CTEQuery


class User(ActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0


class AsyncUser(AsyncActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0


class ReadOnlyUser(ActiveRecord, ReadOnlyMixin):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0


class AsyncReadOnlyUser(AsyncActiveRecord, ReadOnlyMixin):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0


class SoftUser(SoftDeleteMixin, ActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0
    deleted_at: Optional[datetime] = None


class AsyncSoftUser(AsyncSoftDeleteMixin, AsyncActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: int
    name: str
    email: Optional[str] = None
    age: int = 0
    deleted_at: Optional[datetime] = None


class ValidatedUser(ActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str = Field(min_length=2)
    email: Optional[str] = None
    age: int = Field(default=0, ge=0, le=100)

    @field_validator("name")
    @classmethod
    def reject_admin_name(cls, value):
        if value.lower() == "admin":
            raise ValueError("name must not be 'admin'")
        return value

    @model_validator(mode="after")
    def check_senior_age(self):
        if self.name == "senior" and self.age < 60:
            raise ValueError("senior users need age >= 60")
        return self


class AsyncValidatedUser(AsyncActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str = Field(min_length=2)
    email: Optional[str] = None
    age: int = Field(default=0, ge=0, le=100)

    @field_validator("name")
    @classmethod
    def reject_admin_name(cls, value):
        if value.lower() == "admin":
            raise ValueError("name must not be 'admin'")
        return value

    @model_validator(mode="after")
    def check_senior_age(self):
        if self.name == "senior" and self.age < 60:
            raise ValueError("senior users need age >= 60")
        return self


class KeylessUser(ActiveRecord):
    __table_name__ = "users"
    __primary_key__ = None
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    email: Optional[str] = None
    age: int = 0


class OrderItem(ActiveRecord):
    __table_name__ = "order_items"
    __primary_key__ = ("order_id", "product_id")
    order_id: int
    product_id: int
    note: str = ""


class NotAModel:
    pass


def active_users():
    return User.query().where(User.c.age >= 30)


def user_union():
    return User.query().where(User.c.age == 30).union(
        User.query().where(User.c.age == 40)
    )


def user_cte():
    cte = CTEQuery(User.backend())
    cte.with_cte("older_users", User.query().where(User.c.age >= 30))
    return cte.from_cte("older_users")


def async_user_union():
    return AsyncUser.query().where(AsyncUser.c.age == 30).union(
        AsyncUser.query().where(AsyncUser.c.age == 40)
    )


def async_user_cte():
    cte = AsyncCTEQuery(AsyncUser.backend())
    cte.with_cte("older_users", AsyncUser.query().where(AsyncUser.c.age >= 30))
    return cte.from_cte("older_users")


def broken_connection():
    raise RuntimeError("connection resolver exploded")
"""


@pytest.fixture
def cli_env(tmp_path):
    module_name = "cli_models_" + uuid.uuid4().hex
    database = tmp_path / "app.db"
    create_users_table(database)
    create_order_items_table(database)
    write_module(tmp_path, module_name, MODEL_BODY)
    base = ["--path", str(tmp_path), *connection_args(database)]
    async_base = [
        "--path",
        str(tmp_path),
        *connection_args(database, backend=ASYNC_SQLITE_BACKEND),
    ]
    return SimpleNamespace(
        tmp_path=tmp_path,
        database=database,
        module_name=module_name,
        user_model=f"{module_name}:User",
        async_model=f"{module_name}:AsyncUser",
        read_only_model=f"{module_name}:ReadOnlyUser",
        async_read_only_model=f"{module_name}:AsyncReadOnlyUser",
        soft_model=f"{module_name}:SoftUser",
        async_soft_model=f"{module_name}:AsyncSoftUser",
        validated_model=f"{module_name}:ValidatedUser",
        async_validated_model=f"{module_name}:AsyncValidatedUser",
        keyless_model=f"{module_name}:KeylessUser",
        order_model=f"{module_name}:OrderItem",
        active_users=f"{module_name}:active_users",
        user_union=f"{module_name}:user_union",
        user_cte=f"{module_name}:user_cte",
        async_user_union=f"{module_name}:async_user_union",
        async_user_cte=f"{module_name}:async_user_cte",
        base=base,
        async_base=async_base,
    )
