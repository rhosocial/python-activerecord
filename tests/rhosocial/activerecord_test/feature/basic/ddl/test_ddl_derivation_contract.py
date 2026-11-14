# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_derivation_contract.py
"""Contract tests for DDLSource -> statement derivation."""

try:  # Python 3.8 has no typing.Annotated
    from typing import Annotated, Optional
except ImportError:  # pragma: no cover - only on 3.8
    from typing import Optional

    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.base import (
    IdentityAttribute,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.base.derivation import (
    build_comment_statements,
    build_create_index_statements,
    build_create_table_statement,
    build_drop_table_statement,
)
from rhosocial.activerecord.backend.expression import ColumnUniqueConstraint
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.model import ActiveRecord


class DerivedUser(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "derived_users"

    id: Annotated[
        Optional[int],
        UseSqlType(IntegerType()),
        UseColumnAttributes(IdentityAttribute()),
    ] = None
    name: Annotated[
        str,
        UseSqlType(VarCharType(length=128)),
        UseConstraint(ColumnUniqueConstraint),
        UseComment("display name"),
    ]
    email: Annotated[
        Optional[str],
        UseSqlType(VarCharType(length=255)),
        UseIndex("ix_derived_users_email"),
    ] = None


DIALECT = SQLiteDialect()


def test_create_table_uses_declared_columns_and_identity():
    statement = build_create_table_statement(DerivedUser, DIALECT)
    sql, _ = statement.to_sql()
    assert "AUTOINCREMENT" in sql
    assert "UNIQUE" in sql
    assert '"name"' in sql


def test_column_order_is_owned_by_the_caller():
    statement = build_create_table_statement(
        DerivedUser, DIALECT, column_order=["id", "name", "email"]
    )
    sql, _ = statement.to_sql()
    assert sql.index('"id"') < sql.index('"name"') < sql.index('"email"')


def test_column_order_must_cover_every_column():
    with pytest.raises(ValueError, match="missing column"):
        build_create_table_statement(
            DerivedUser, DIALECT, column_order=["id", "name"]
        )


def test_indexes_and_comments_are_separate_by_default():
    indexes = build_create_index_statements(DerivedUser, DIALECT)
    assert len(indexes) == 1
    assert "CREATE INDEX" in indexes[0].to_sql()[0]

    comments = build_comment_statements(DerivedUser, DIALECT)
    assert len(comments) == 1
    assert comments[0].comment == "display name"


def test_drop_statement_honours_if_exists():
    sql, _ = build_drop_table_statement(
        DerivedUser, DIALECT, if_exists=True
    ).to_sql()
    assert "IF EXISTS" in sql


def test_migration_mixin_executes_actions_on_the_configured_backend():
    config = SQLiteConnectionConfig(database=":memory:")
    DerivedUser.configure(config, SQLiteBackend)
    backend = DerivedUser.backend()
    try:
        DerivedUser.create_table()
        DerivedUser.create_indexes()
        rows = backend.execute(
            "SELECT type, name FROM sqlite_master",
            options=ExecutionOptions(
                stmt_type=StatementType.SELECT, process_result_set=True
            ),
        ).data or []
        names = {row["name"] for row in rows}
        assert "derived_users" in names
        assert "ix_derived_users_email" in names

        DerivedUser.drop_indexes(if_exists=True)
        DerivedUser.drop_table(if_exists=True)
        rows = backend.execute(
            "SELECT type, name FROM sqlite_master",
            options=ExecutionOptions(
                stmt_type=StatementType.SELECT, process_result_set=True
            ),
        ).data or []
        names = {row["name"] for row in rows}
        assert "derived_users" not in names
        assert "ix_derived_users_email" not in names
    finally:
        DerivedUser.__backend__ = None
