# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_ddl_column_mixin_paths.py
"""
Cover DDLColumnMixin formatting surface via DummyDialect.

Targets uncovered branches in backend/dialect/mixins/ddl_column.py:
- format_column_definition: every constraint kind + comment
- format_column_constraint: PRIMARY KEY/NOT NULL/NULL/UNIQUE/DEFAULT/CHECK/FK
- table constraints: PK/UNIQUE/CHECK/FK + name-less rendering
- ALTER actions: AddColumn/DropColumn(if_exists)/AlterColumn(value kinds/cascade)
- AddTableConstraintAction / DropTableConstraintAction rendering
- format_storage_options
"""

import pytest

from rhosocial.activerecord.backend.dialect.mixins.ddl_column import DDLColumnMixin
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AddColumn,
    AddTableConstraint,
    AlterColumn,
    ColumnAlterOperation,
    DropColumn,
    DropTableConstraint,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect():
    return DummyDialect()


class TestColumnDefinition:
    def test_with_comment(self, dialect):
        col = ColumnDefinition(
            "name", TextType(), comment="user name"
        )
        sql, params = dialect.format_column_definition(col)
        assert "COMMENT" in sql

    def test_all_simple_constraints(self, dialect):
        for ctype in (ColumnConstraintType.PRIMARY_KEY, ColumnConstraintType.NOT_NULL,
                      ColumnConstraintType.NULL, ColumnConstraintType.UNIQUE):
            col = ColumnDefinition("x", IntegerType(), constraints=[
                ColumnConstraint(ctype)
            ])
            sql, params = dialect.format_column_definition(col)
            assert ctype.value in sql

    def test_default_constraint(self, dialect):
        col = ColumnDefinition("x", IntegerType(), constraints=[
            ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=5)
        ])
        sql, params = dialect.format_column_definition(col)
        assert "DEFAULT" in sql

    def test_check_constraint(self, dialect):
        col = ColumnDefinition("x", IntegerType(), constraints=[
            ColumnConstraint(
                ColumnConstraintType.CHECK,
                check_condition=Column(dialect, "x") > Literal(dialect, 0),
            )
        ])
        sql, params = dialect.format_column_definition(col)
        assert "CHECK" in sql


class TestAlterActions:
    def test_add_column(self, dialect):
        action = AddColumn(dialect, ColumnDefinition("age", IntegerType()))
        sql, params = dialect.format_add_column_action(action)
        assert sql.startswith("ADD COLUMN")

    def test_drop_column(self, dialect):
        action = DropColumn(dialect, column_name="age")
        sql, _ = dialect.format_drop_column_action(action)
        assert sql.startswith("DROP COLUMN")

    def test_drop_column_if_exists(self, dialect):
        action = DropColumn(dialect, column_name="age", if_exists=True)
        sql, _ = dialect.format_drop_column_action(action)
        assert "IF EXISTS" in sql

    def test_alter_column_set_default(self, dialect):
        action = AlterColumn(
            dialect, "age", ColumnAlterOperation.SET_DEFAULT, new_value=0
        )
        sql, params = dialect.format_alter_column_action(action)
        assert "SET DEFAULT" in sql
        assert len(params) == 1

    def test_alter_column_drop_default(self, dialect):
        action = AlterColumn(dialect, "age", ColumnAlterOperation.DROP_DEFAULT)
        sql, params = dialect.format_alter_column_action(action)
        assert "DROP DEFAULT" in sql
        assert params == ()

    def test_alter_column_cascade(self, dialect):
        action = AlterColumn(
            dialect, "age", ColumnAlterOperation.DROP_NOT_NULL, cascade=True
        )
        sql, _ = dialect.format_alter_column_action(action)
        assert "CASCADE" in sql

    def test_alter_column_set_data_type_invalid(self, dialect):
        action = AlterColumn(
            dialect, "age", "SET DATA TYPE", new_value="NOT A TYPE !!!"
        )
        with pytest.raises(ValueError):
            dialect.format_alter_column_action(action)

    def test_alter_column_set_data_type_valid(self, dialect):
        action = AlterColumn(
            dialect, "age", "SET DATA TYPE", new_value="INTEGER"
        )
        sql, _ = dialect.format_alter_column_action(action)
        assert "INTEGER" in sql


class TestTableConstraints:
    def test_pk_constraint(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.PRIMARY_KEY,
            columns=["id"],
        )
        assert "PRIMARY KEY" in dialect.format_pk_constraint(t)

    def test_unique_constraint(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.UNIQUE, columns=["email"]
        )
        assert "UNIQUE" in dialect.format_unique_constraint(t)

    def test_check_constraint(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.CHECK,
            check_condition=Column(dialect, "age") > Literal(dialect, 0),
        )
        sql, _ = dialect.format_table_check_constraint(t)
        assert "CHECK" in sql

    def test_foreign_key_constraint(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.FOREIGN_KEY,
            columns=["role_id"],
            foreign_key_table="roles",
            foreign_key_columns=["id"],
        )
        assert "REFERENCES" in dialect.format_foreign_key_constraint(t)

    def test_table_constraint_dispatch(self, dialect):
        t = TableConstraint(
            constraint_type=TableConstraintType.UNIQUE, columns=["a"]
        )
        sql, _ = dialect.format_table_constraint_sql(t)
        assert sql

    def test_storage_options(self, dialect):
        sql, params = dialect.format_storage_options({"key": "value"})
        assert isinstance(sql, str)


class TestAddDropConstraintActions:
    def _constraint(self, dialect):
        return TableConstraint(
            constraint_type=TableConstraintType.UNIQUE,
            columns=["email"],
        )

    def test_add_table_constraint_action(self, dialect):
        action = AddTableConstraint(
            dialect, constraint=self._constraint(dialect)
        )
        sql, _ = dialect.format_add_table_constraint_action(action)
        assert sql

    def test_drop_table_constraint_action(self, dialect):
        action = DropTableConstraint(dialect, constraint_name="uq_email")
        sql, _ = dialect.format_drop_table_constraint_action(action)
        assert sql
