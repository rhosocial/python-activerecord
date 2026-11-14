# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/ddl/test_ddl_view_surface.py
"""SQLite view DDL: the spellings it has and the ones it refuses.

SQLite keeps a view's text, so a bind parameter inside the body has nothing to
bind at read time. The body renders, but the statement warns rather than
storing a broken view silently.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column, Literal, QueryStatement, WhereClause
from rhosocial.activerecord.backend.expression.objects import View
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements import (
    CreateViewStatement,
    DropViewStatement,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

DIALECT = SQLiteDialect(version=(3, 53, 0))

TRUE_PROBES = (
    "supports_create_view",
    "supports_drop_view",
    "supports_if_not_exists_view",
    "supports_temporary_view",
    "supports_if_exists_view",
)

FALSE_PROBES = (
    "supports_create_view_bind_parameters",
    "supports_or_replace_view",
    "supports_create_or_replace_view",
    "supports_materialized_view",
    "supports_refresh_materialized_view",
    "supports_materialized_view_tablespace",
    "supports_materialized_view_storage_options",
    "supports_view_check_option",
    "supports_cascade_view",
    "supports_with_data_clause",
)


def _query():
    return QueryStatement(DIALECT, select=[Column(DIALECT, "id")], from_="users")


def test_view_capability_matrix():
    for name in TRUE_PROBES:
        assert getattr(DIALECT, name)() is True, name
    for name in FALSE_PROBES:
        assert getattr(DIALECT, name)() is False, name


def test_if_not_exists_and_column_aliases():
    sql, params = CreateViewStatement(
        DIALECT,
        view=View(DIALECT, "active_users"),
        query=_query(),
        if_not_exists=True,
        column_aliases=["user_id"],
    ).to_sql()
    assert sql == (
        'CREATE VIEW IF NOT EXISTS "active_users" ("user_id") ' 'AS SELECT "id" FROM "users"'
    )
    assert params == ()


def test_replace_request_is_refused():
    """SQLite has no CREATE OR REPLACE VIEW; the request is refused.

    Rendering it as ``IF NOT EXISTS`` would leave an existing view's old
    definition untouched while reporting success, so the dialect refuses
    instead of silently changing what "replace" means.
    """
    with pytest.raises(UnsupportedFeatureError, match="CREATE OR REPLACE VIEW"):
        CreateViewStatement(
            DIALECT,
            view=View(DIALECT, "users_view"),
            query=_query(),
            replace=True,
        ).to_sql()


def test_temporary_view():
    sql, params = CreateViewStatement(
        DIALECT,
        view=View(DIALECT, "session_users"),
        query=_query(),
        temporary=True,
    ).to_sql()
    assert sql == 'CREATE TEMPORARY VIEW "session_users" AS SELECT "id" FROM "users"'
    assert params == ()


def test_view_body_with_bind_parameters_warns_and_still_renders():
    query = QueryStatement(
        DIALECT,
        select=[Column(DIALECT, "id")],
        from_="users",
        where=WhereClause(
            DIALECT, ComparisonPredicate(DIALECT, "eq", Column(DIALECT, "id"), Literal(DIALECT, 1))
        ),
    )
    with pytest.warns(UserWarning, match="does not allow parameters in VIEW"):
        sql, params = CreateViewStatement(
            DIALECT, view=View(DIALECT, "one_user"), query=query
        ).to_sql()
    assert sql == 'CREATE VIEW "one_user" AS SELECT "id" FROM "users" WHERE "id" = ?'
    assert params == (1,)


def test_drop_view_if_exists():
    sql, params = DropViewStatement(
        DIALECT, view=View(DIALECT, "active_users"), if_exists=True
    ).to_sql()
    assert sql == 'DROP VIEW IF EXISTS "active_users"'
    assert params == ()


@pytest.mark.parametrize("keyword,feature", [("cascade", "CASCADE"), ("restrict", "RESTRICT")])
def test_drop_view_dependent_object_clauses_are_refused(keyword, feature):
    with pytest.raises(UnsupportedFeatureError, match=feature):
        DropViewStatement(DIALECT, view=View(DIALECT, "master_view"), **{keyword: True}).to_sql()
