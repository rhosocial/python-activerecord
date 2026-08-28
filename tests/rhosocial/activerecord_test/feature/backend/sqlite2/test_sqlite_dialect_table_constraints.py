# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_dialect_table_constraints.py
"""Regression tests for TABLE-level constraint formatting (Sprint: unique
table constraint shadowed by a same-named COLUMN-level handler).

History: ``SQLiteBackend``'s mixin defined a *column*-level
``format_unique_constraint(constraint) -> Tuple[str, tuple]`` which shadowed
the *table*-level ``format_unique_constraint(t_const) -> str`` from
``backend.dialect.mixins.ddl_column``. Dispatching a
``TableConstraintType.UNIQUE`` therefore received a tuple where the table
dispatcher joins plain strings -> TypeError. The column-level handler is now
renamed ``format_column_unique_constraint``; these tests pin both levels.
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType, TextType,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _make_table(ctype, *, named=None):
    return CreateTableExpression(
        dialect=SQLiteDialect(),
        table="demo",
        columns=[
            ColumnDefinition("id", IntegerType()),
            ColumnDefinition("code", TextType(),
                             constraints=[ColumnConstraint(
                                 ColumnConstraintType.NOT_NULL)]),
        ],
        table_constraints=[
            TableConstraint(constraint_type=ctype, columns=["code"],
                            name=named)
        ],
    )


class TestTableLevelUnique:

    def test_unique_table_constraint_compiles(self):
        """The original failure: UNIQUE table constraint used to raise
        TypeError (tuple joined as str)."""
        expr = _make_table(TableConstraintType.UNIQUE)
        sql = "".join(str(part) for part in expr.to_sql())
        assert "UNIQUE" in sql
        assert '"code"' in sql

    def test_unique_full_statement_shape(self):
        expr = _make_table(TableConstraintType.UNIQUE)
        stmt = expr.to_sql()[0]
        assert stmt == ('CREATE TABLE "demo" ("id" INTEGER, '
                        '"code" TEXT NOT NULL, UNIQUE ("code"))')

    def test_named_unique_keeps_constraint_name(self):
        expr = _make_table(TableConstraintType.UNIQUE,
                           named="uq_demo_code")
        stmt = expr.to_sql()[0]
        assert 'CONSTRAINT "uq_demo_code" UNIQUE' in stmt

    def test_primary_key_still_works(self):
        expr = _make_table(TableConstraintType.PRIMARY_KEY)
        stmt = expr.to_sql()[0]
        assert 'PRIMARY KEY ("code")' in stmt


class TestLevelSeparation:

    def test_impl_mixin_no_longer_shadows(self):
        """Guard: the backend mixin must not define the table-level name."""
        assert "format_unique_constraint" not in vars(SQLiteDialect)

    def test_column_level_handler_reachable_under_new_name(self):
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(
            constraint_type=ColumnConstraintType.UNIQUE)
        sql, params = dialect.format_column_unique_constraint(constraint)
        assert sql == " UNIQUE"
        assert params == ()

    def test_dispatch_resolves_to_base_for_table_input(self):
        """Table dispatcher must resolve to the base str-returning method."""
        dialect = SQLiteDialect()
        owner = None
        # walk MRO: find defining class of format_unique_constraint
        for klass in type(dialect).__mro__:
            if "format_unique_constraint" in vars(klass):
                owner = klass
                break
        assert owner is not None
        assert owner.__name__ != SQLiteDialect.__name__
