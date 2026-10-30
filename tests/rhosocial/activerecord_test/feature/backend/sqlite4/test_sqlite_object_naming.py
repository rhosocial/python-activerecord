# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_sqlite_object_naming.py
"""SQLite's schema is an attached database, not the SQL-standard construct.

The distinction these tests pin is the whole point of
:class:`SQLiteObjectNameMixin`: the DDL probes stay ``False`` -- SQLite has no
``CREATE SCHEMA`` -- while object *naming* accepts a schema level for SQLite's
own kind of table. One flag cannot answer both questions, and a single flag would
either make ``main.sqlite_master`` inexpressible or make SQLite look as though it
had schemas it could create.

So the acceptance rule is keyed on the node's identity, and these tests pin each
side of it:

* a **core** table carrying ``schema_name`` is still refused, because SQLite has
  no schema of that kind;
* a :class:`SQLiteTable` carrying ``schema_name`` renders, because it stands for
  an attached-database name;
* ``catalog_name`` is refused either way -- SQLite has no level above the
  attached-database name.

The pragma-path coverage of table listing is a different thing and is not what
this file is about; this is the path that builds a SELECT through the dialect's
object-name formatter.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression import SQLiteTable
from rhosocial.activerecord.backend.expression.objects.relation import Table


@pytest.fixture
def dialect():
    d = SQLiteDialect()
    d._version = (3, 46, 1)
    return d


# ---------------------------------------------------------------------------
# The two questions are answered separately
# ---------------------------------------------------------------------------


def test_ddl_probes_stay_false(dialect):
    """The naming fix must not have moved the DDL answers.

    This is the regression guard for the design: answering the naming question
    by flipping a DDL flag would make SQLite look as though it supports schemas.
    """
    assert dialect.supports_schema() is False
    assert dialect.supports_schema_qualification() is False
    assert dialect.supports_catalog() is False
    assert dialect.supports_catalog_qualification() is False


def test_core_table_with_schema_is_still_refused(dialect):
    """A standard schema is still refused: SQLite does not have one.

    The node that carries a ``schema_name`` decides what it means, so the core
    node keeps the old refusal rather than silently starting to work.
    """
    with pytest.raises(UnsupportedFeatureError):
        Table(dialect, "users", schema_name="public").to_sql()


def test_core_table_with_catalog_is_refused(dialect):
    with pytest.raises(UnsupportedFeatureError):
        Table(dialect, "users", catalog_name="db").to_sql()


# ---------------------------------------------------------------------------
# SQLiteTable carries the attached-database name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "schema,expected",
    [
        ("main", "main.sqlite_master"),
        ("other", "other.sqlite_master"),
        ("attached_1", "attached_1.sqlite_master"),
    ],
)
def test_sqlite_table_renders_its_schema_level(dialect, schema, expected):
    """The attached-database name reaches the SQL, unquoted."""
    sql, params = SQLiteTable(
        dialect,
        "sqlite_master",
        schema_name=schema,
        schema_need_quote=False,
        name_need_quote=False,
    ).to_sql()
    assert sql == expected
    assert params == ()


def test_sqlite_table_without_a_schema_is_still_usable(dialect):
    """No schema means a plain table name, exactly as before."""
    sql, params = SQLiteTable(dialect, "sqlite_master").to_sql()
    assert sql == '"sqlite_master"'
    assert params == ()


def test_sqlite_table_quoting_is_per_level(dialect):
    """Each level's quoting flag is honoured independently."""
    sql, _ = SQLiteTable(
        dialect,
        "sqlite_master",
        schema_name="main",
        schema_need_quote=False,
        name_need_quote=True,
    ).to_sql()
    assert sql == 'main."sqlite_master"'


def test_sqlite_table_refuses_a_catalog(dialect):
    """SQLite has nothing above the attached-database name.

    The refusal names where the database belongs, so the caller is told how to
    spell it rather than only that it was wrong.
    """
    with pytest.raises(UnsupportedFeatureError) as exc:
        SQLiteTable(dialect, "sqlite_master", catalog_name="db").to_sql()
    assert "schema_name" in (exc.value.suggestion or "")


def test_sqlite_table_is_a_table(dialect):
    """It must stay usable wherever a relation object is accepted."""
    from rhosocial.activerecord.backend.expression.objects.relation import (
        RelationObject,
    )
    from rhosocial.activerecord.backend.expression.sources.relation import (
        NamedRelationRef,
    )

    assert issubclass(SQLiteTable, RelationObject)
    sql, params = NamedRelationRef(
        dialect,
        SQLiteTable(
            dialect,
            "sqlite_master",
            schema_name="main",
            schema_need_quote=False,
            name_need_quote=False,
        ),
    ).to_sql()
    assert sql == "main.sqlite_master"
    assert params == ()
