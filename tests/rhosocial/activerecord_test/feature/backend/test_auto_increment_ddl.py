# tests/rhosocial/activerecord_test/feature/backend/test_auto_increment_ddl.py
"""Regression tests for DDL compilation of auto-increment, standard types,
boolean defaults, and timestamps.

Covers bugs found in rbac cross-backend testing:
- is_auto_increment=True on PRIMARY_KEY must produce AUTOINCREMENT.
- format_create_table_statement must return a string for all types.
- BooleanType with DEFAULT True must be accepted.
- TimestampType must map to NUMERIC (SQLite affinity).
"""

import pytest
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefaultConstraint,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.types import (
    BooleanType, IntegerType, TextType, TimestampType, VarCharType,
)
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement,
    ColumnDefinition,
    ColumnConstraint,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect



@pytest.fixture
def dialect():
    return SQLiteDialect()


def _pk():
    # _pk() 在测试函数内调用，那里 dialect 是 fixture。
    dialect = SQLiteDialect()
    return [
        ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True))
    ]


def _build_table(dialect):
    return CreateTableStatement(
        dialect=dialect, table=Table(dialect, 'test_tbl'),
        columns=[
            ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=_pk()),
            ColumnDefinition(dialect, "name", TextType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]),
            ColumnDefinition(dialect, "flag", BooleanType(dialect),
                constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                             ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, True))]),
            ColumnDefinition(dialect, "code", VarCharType(dialect, 16)),
            ColumnDefinition(dialect, "created_at", TimestampType(dialect=dialect)),
        ],
    )


class TestAutoIncrementDDL:

    def test_auto_increment_in_ddl(self, dialect):
        sql, _ = dialect.format_create_table_statement(_build_table(dialect))
        assert "AUTOINCREMENT" in sql.upper(), f"auto-increment missing: {sql}"

    def test_all_standard_types_compile(self, dialect):
        sql, params = dialect.format_create_table_statement(_build_table(dialect))
        assert isinstance(sql, str)
        assert isinstance(params, tuple)

    def test_boolean_default_true(self, dialect):
        expr = CreateTableStatement(
            dialect=dialect, table=Table(dialect, 'bool_test'),
            columns=[
                ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=_pk()),
                ColumnDefinition(dialect, "flag", BooleanType(dialect),
                    constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                                 ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, True))]),
            ],
        )
        sql, _ = dialect.format_create_table_statement(expr)
        assert "NUMERIC" in sql.upper()

    def test_timestamp_type(self, dialect):
        expr = CreateTableStatement(
            dialect=dialect, table=Table(dialect, 'ts_test'),
            columns=[
                ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=_pk()),
                ColumnDefinition(dialect, "created_at", TimestampType(dialect=dialect)),
            ],
        )
        sql, _ = dialect.format_create_table_statement(expr)
        assert "NUMERIC" in sql.upper()
