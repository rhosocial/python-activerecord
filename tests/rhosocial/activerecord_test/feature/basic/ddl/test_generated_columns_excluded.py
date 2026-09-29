# tests/rhosocial/activerecord_test/feature/basic/ddl/test_generated_columns_excluded.py
"""Generated columns must never appear in INSERT/UPDATE payloads.

``get_generated_columns()`` used to read ``__table_generated_columns__``, an
attribute nothing in the tree ever wrote, so it always returned an empty tuple
and every one of its six call sites was inert. Declaring a generated column
(``UseGeneratedColumn``) therefore did not exclude it from writes.

That is a hard error on SQLite: ``cannot INSERT into generated column``.

Two views are needed and they are not interchangeable:

* ``get_generated_field_names()`` -- field names, for call sites holding a
  ``model_dump()`` result (``_prepare_save_data``)
* ``get_generated_columns()`` -- column names, for call sites holding an
  already-mapped payload (``_insert_internal``)

They diverge whenever a field renames its column, which ``test_renamed_
generated_column_is_excluded_from_both_views`` pins down.
"""

from typing import Annotated, ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.statements import (
    GeneratedColumnExpression,
    GeneratedColumnType,
)
from rhosocial.activerecord.base import UseColumn, UseGeneratedColumn
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.model import ActiveRecord


def _double(dialect):
    return GeneratedColumnExpression(
        dialect,
        expression=Column(dialect, "views") * 2,
        storage_type=GeneratedColumnType.STORED,
    )


class GeneratedPost(ActiveRecord):
    """Model with a generated column whose field name matches its column name."""

    __table_name__ = "ar_generated_posts"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    title: str
    views: int = 0
    double_views: Annotated[int, UseGeneratedColumn(_double)] = 0


class RenamedGeneratedPost(ActiveRecord):
    """Model whose generated column has a *different* column name."""

    __table_name__ = "ar_renamed_generated_posts"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    title: str
    views: int = 0
    doubled: Annotated[
        int,
        UseColumn("double_views_col"),
        UseGeneratedColumn(_double),
    ] = 0


class PlainPost(ActiveRecord):
    """Control model with no generated column at all."""

    __table_name__ = "ar_plain_posts"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    title: str
    views: int = 0


DDL = [
    "CREATE TABLE ar_generated_posts ("
    "id INTEGER PRIMARY KEY, title TEXT NOT NULL, views INTEGER DEFAULT 0, "
    "double_views INTEGER GENERATED ALWAYS AS (views * 2) STORED)",
    "CREATE TABLE ar_renamed_generated_posts ("
    "id INTEGER PRIMARY KEY, title TEXT NOT NULL, views INTEGER DEFAULT 0, "
    "double_views_col INTEGER GENERATED ALWAYS AS (views * 2) STORED)",
    "CREATE TABLE ar_plain_posts ("
    "id INTEGER PRIMARY KEY, title TEXT NOT NULL, views INTEGER DEFAULT 0)",
]


@pytest.fixture
def generated_tables(user_class):
    """Create the generated-column tables and bind the models to the backend.

    The models here are declared locally rather than supplied by the provider,
    so they need the same ``__backend__`` binding the provider does for its own
    fixture models.
    """
    backend = user_class.backend()
    for model in (GeneratedPost, RenamedGeneratedPost, PlainPost):
        model.__backend__ = backend
    cursor = backend.connection.cursor()
    for statement in DDL:
        cursor.execute(statement.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS "))
    backend.connection.commit()
    cursor.close()
    yield backend


class TestGeneratedColumnDeclarations:
    """The declaration is what makes a column generated -- no extra plumbing."""

    def test_generated_field_is_reported(self):
        assert GeneratedPost.get_generated_field_names() == ("double_views",)

    def test_generated_column_is_reported(self):
        assert GeneratedPost.get_generated_columns() == ("double_views",)

    def test_renamed_field_maps_to_its_column(self):
        assert RenamedGeneratedPost.get_generated_field_names() == ("doubled",)
        assert RenamedGeneratedPost.get_generated_columns() == ("double_views_col",)

    def test_renamed_generated_column_is_excluded_from_both_views(self):
        """The two views must not be collapsed into one.

        Filtering a mapped payload by field name would miss the column; the
        field view is ``doubled`` and the column view is ``double_views_col``.
        """
        assert RenamedGeneratedPost.get_generated_field_names() == ("doubled",)
        assert "doubled" not in RenamedGeneratedPost.get_generated_columns()
        assert RenamedGeneratedPost.get_generated_columns() == ("double_views_col",)

    def test_plain_model_reports_nothing(self):
        assert PlainPost.get_generated_field_names() == ()
        assert PlainPost.get_generated_columns() == ()


class TestGeneratedColumnWriteExclusion:
    """A model declaring a generated column can still be written."""

    def test_prepare_save_data_drops_the_generated_field(self):
        post = GeneratedPost(title="hello", views=3, double_views=999)
        prepared = post._prepare_save_data()
        assert "double_views" not in prepared
        assert prepared["views"] == 3

    def test_insert_computes_the_generated_column(self, generated_tables):
        post = GeneratedPost(title="hello", views=3)
        post.save()

        assert post.id is not None
        row = (
            generated_tables.connection.cursor()
            .execute("SELECT views, double_views FROM ar_generated_posts WHERE id = ?", (post.id,))
            .fetchone()
        )
        assert row is not None
        assert row[1] == row[0] * 2, "the database, not the model, supplies the value"

    def test_update_does_not_write_the_generated_column(self, generated_tables):
        post = GeneratedPost(title="hello", views=3)
        post.save()

        post.views = 5
        post.save()

        cursor = generated_tables.connection.cursor()
        row = cursor.execute(
            "SELECT views, double_views FROM ar_generated_posts WHERE id = ?", (post.id,)
        ).fetchone()
        assert tuple(row) == (5, 10)

    def test_renamed_generated_column_survives_an_insert(self, generated_tables):
        post = RenamedGeneratedPost(title="renamed", views=4)
        post.save()

        assert post.id is not None
        cursor = generated_tables.connection.cursor()
        row = cursor.execute(
            "SELECT views, double_views_col FROM ar_renamed_generated_posts WHERE id = ?", (post.id,)
        ).fetchone()
        assert tuple(row) == (4, 8)
