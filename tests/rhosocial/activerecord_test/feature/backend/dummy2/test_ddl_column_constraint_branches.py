# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_ddl_column_constraint_branches.py
"""
Cover DDLColumnMixin constraint formatting edge branches.

Targets remaining uncovered lines in backend/dialect/mixins/ddl_column.py:
- DEFAULT value variants: BaseExpression / str / numeric / missing
- CHECK with missing condition
- column-level FK: referential actions, deferrable variants, missing reference
- format_pk/unique constraint name rendering
- format_table_constraint_sql unsupported type fallback
"""

import pytest

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
    ReferentialAction,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect():
    return DummyDialect()


class TestColumnConstraintDispatch:
    def test_unknown_type_returns_empty(self, dialect):
        c = ColumnConstraint(ColumnConstraintType.COLLATE, collation="utf8mb4_general_ci")
        sql, params = dialect.format_column_constraint(c)
        assert sql == "" and params == ()

    def test_check_without_condition(self, dialect):
        c = ColumnConstraint(ColumnConstraintType.CHECK)
        sql, params = dialect.format_column_constraint(c)
        assert sql == ""


class TestDefaultConstraint:
    def test_missing_default_raises(self, dialect):
        c = ColumnConstraint(ColumnConstraintType.DEFAULT)
        with pytest.raises(ValueError):
            dialect.format_default_constraint(c)

    def test_expression_default(self, dialect):
        c = ColumnConstraint(
            ColumnConstraintType.DEFAULT, default_value=Literal(dialect, 5)
        )
        sql, params = dialect.format_default_constraint(c)
        assert sql.startswith(" DEFAULT")

    def test_string_default(self, dialect):
        c = ColumnConstraint(
            ColumnConstraintType.DEFAULT, default_value="active"
        )
        sql, params = dialect.format_default_constraint(c)
        assert "'active'" in sql

    def test_numeric_default(self, dialect):
        c = ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=42)
        sql, params = dialect.format_default_constraint(c)
        assert "42" in sql
        assert params == ()

    def test_check_constraint_with_condition(self, dialect):
        c = ColumnConstraint(
            ColumnConstraintType.CHECK,
            check_condition=Column(dialect, "x") > Literal(dialect, 0),
        )
        sql, params = dialect.format_column_check_constraint(c)
        assert "CHECK" in sql and len(params) >= 1


class TestColumnFKConstraint:
    def _fk(self, **kw):
        base = dict(
            constraint_type=ColumnConstraintType.FOREIGN_KEY,
            foreign_key_reference=("roles", ["id"]),
        )
        base.update(kw)
        return ColumnConstraint(**base)

    def test_missing_reference_raises(self, dialect):
        with pytest.raises(ValueError):
            dialect.format_column_fk_constraint(
                ColumnConstraint(ColumnConstraintType.FOREIGN_KEY)
            )

    def test_no_actions(self, dialect):
        sql, params = dialect.format_column_fk_constraint(self._fk())
        assert "REFERENCES" in sql

    def test_on_delete_on_update(self, dialect):
        sql, _ = dialect.format_column_fk_constraint(
            self._fk(on_delete=ReferentialAction.CASCADE,
                     on_update=ReferentialAction.SET_NULL)
        )
        assert "ON DELETE CASCADE" in sql
        assert "ON UPDATE SET NULL" in sql

    def test_no_action_omitted(self, dialect):
        sql, _ = dialect.format_column_fk_constraint(
            self._fk(on_delete=ReferentialAction.NO_ACTION)
        )
        assert "ON DELETE" not in sql

    def test_deferrable_variants(self, dialect):
        sql, _ = dialect.format_column_fk_constraint(
            self._fk(deferrable=True, initially_deferred=True)
        )
        assert "DEFERRABLE INITIALLY DEFERRED" in sql
        sql, _ = dialect.format_column_fk_constraint(
            self._fk(deferrable=True, initially_deferred=False)
        )
        assert "DEFERRABLE INITIALLY IMMEDIATE" in sql
        sql, _ = dialect.format_column_fk_constraint(self._fk(deferrable=True))
        assert sql.rstrip().endswith("DEFERRABLE")
        sql, _ = dialect.format_column_fk_constraint(self._fk(deferrable=False))
        assert "NOT DEFERRABLE" in sql


class TestTableConstraintEdge:
    def test_pk_with_name(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.PRIMARY_KEY,
            name="pk_users", columns=["id"],
        )
        sql = dialect.format_pk_constraint(t)
        assert "PRIMARY KEY" in sql and "id" in sql

    def test_table_constraint_sql_check(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.CHECK,
            check_condition=Column(dialect, "a") > Literal(dialect, 0),
        )
        sql, _ = dialect.format_table_constraint_sql(t)
        assert "CHECK" in sql

    def test_table_constraint_sql_fk(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.FOREIGN_KEY,
            columns=["rid"],
            foreign_key_table="roles",
            foreign_key_columns=["id"],
        )
        sql, _ = dialect.format_table_constraint_sql(t)
        assert "FOREIGN KEY" in sql

    def test_table_constraint_sql_pk(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.PRIMARY_KEY, columns=["id"]
        )
        sql, _ = dialect.format_table_constraint_sql(t)
        assert "PRIMARY KEY" in sql

    def test_table_constraint_sql_unknown(self, dialect):
        t = TableConstraint(TableConstraintType.EXCLUDE, columns=["a"])
        result = dialect.format_table_constraint_sql(t)
        assert result is not None
