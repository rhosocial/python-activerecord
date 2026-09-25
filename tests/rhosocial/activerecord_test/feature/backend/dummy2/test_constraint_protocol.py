# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_constraint_protocol.py
"""Tests for ConstraintSupport protocol and ConstraintMixin."""

import pytest
from rhosocial.activerecord.backend.dialect.protocols import ConstraintSupport
from rhosocial.activerecord.backend.dialect.mixins import ConstraintMixin
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestConstraintProtocol:
    """Tests for ConstraintSupport protocol compliance on DummyDialect."""

    def test_dummy_dialect_implements_constraint_support(self, dummy_dialect: DummyDialect):
        """Test that DummyDialect implements ConstraintSupport protocol."""
        assert isinstance(dummy_dialect, ConstraintSupport)

    # Basic constraint types (SQL-86/SQL-92)
    def test_supports_primary_key_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_primary_key_constraint() is True

    def test_supports_unique_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_unique_constraint() is True

    def test_supports_not_null_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_not_null_constraint() is True

    def test_supports_check_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_check_constraint() is True

    def test_supports_foreign_key_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_foreign_key_constraint() is True

    # FK referential actions (SQL-92)
    def test_supports_fk_on_delete(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_fk_on_delete() is True

    def test_supports_fk_on_update(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_fk_on_update() is True

    # FK match modes (SQL:1999)
    def test_supports_fk_match(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_fk_match() is True

    # Constraint deferral (SQL:1999)
    def test_supports_deferrable_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_deferrable_constraint() is True

    # Constraint enforcement control (SQL:2016)
    def test_supports_constraint_enforced(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_constraint_enforced() is True

    # ALTER TABLE constraint operations (SQL-92)
    def test_supports_add_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_add_constraint() is True

    def test_supports_drop_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_drop_constraint() is True

    # PostgreSQL-proprietary features (DummyDialect enables all via PostgresConstraintMixin)
    def test_supports_constraint_novalidate(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_constraint_novalidate() is True

    def test_supports_exclude_constraint(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_exclude_constraint() is True


class TestConstraintMixinDefaults:
    """Tests for ConstraintMixin default values.

    All ConstraintMixin methods default to True so that DummyDialect
    can validate the full constraint implementation by simply inheriting.
    Actual backends override methods as needed.
    """

    def test_basic_constraint_types_default_true(self):
        """Basic constraint types default to True."""

        class TestDialect(ConstraintMixin):
            pass

        dialect = TestDialect()
        assert dialect.supports_primary_key_constraint() is True
        assert dialect.supports_unique_constraint() is True
        assert dialect.supports_not_null_constraint() is True
        assert dialect.supports_check_constraint() is True
        assert dialect.supports_foreign_key_constraint() is True

    def test_fk_actions_default_true(self):
        """FK referential actions default to True."""

        class TestDialect(ConstraintMixin):
            pass

        dialect = TestDialect()
        assert dialect.supports_fk_on_delete() is True
        assert dialect.supports_fk_on_update() is True

    def test_advanced_sql_standard_features_default_true(self):
        """Advanced SQL standard features default to True.

        All ConstraintMixin methods default to True to enable DummyDialect
        to validate the full constraint implementation. Backends that don't
        support these features must explicitly override them.
        """

        class TestDialect(ConstraintMixin):
            pass

        dialect = TestDialect()
        assert dialect.supports_fk_match() is True
        assert dialect.supports_deferrable_constraint() is True
        assert dialect.supports_constraint_enforced() is True

    def test_alter_table_constraint_operations_default_true(self):
        """ALTER TABLE constraint operations default to True."""

        class TestDialect(ConstraintMixin):
            pass

        dialect = TestDialect()
        assert dialect.supports_add_constraint() is True
        assert dialect.supports_drop_constraint() is True


class TestPostgresConstraintMixinDefaults:
    """Tests for PG-proprietary constraint features on DummyDialect.

    DummyDialect inherits PostgresConstraintMixin which provides
    supports_constraint_novalidate() and supports_exclude_constraint().
    We test these via DummyDialect without importing the PG package.
    """

    def test_pg_proprietary_features_enabled(self, dummy_dialect: DummyDialect):
        """PostgreSQL-proprietary constraint features are enabled on DummyDialect."""
        assert dummy_dialect.supports_constraint_novalidate() is True
        assert dummy_dialect.supports_exclude_constraint() is True


class TestConstraintSQLFormatting:
    """Tests for constraint SQL generation using DummyDialect.

    These tests verify that constraint formatting methods produce
    valid SQL when the corresponding capability is enabled.
    """

    @pytest.fixture
    def dialect(self):
        return DummyDialect()

    def test_format_add_primary_key_constraint(self, dialect):
        """Test ADD PRIMARY KEY constraint SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraint
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
            TableConstraintType,
        )

        action = AddTableConstraint(
            dialect,
            constraint=TableConstraint(dialect, 
                constraint_type=TableConstraintType.PRIMARY_KEY,
                columns=["id"],
            ),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "PRIMARY KEY" in sql
        assert "id" in sql

    def test_format_add_unique_constraint(self, dialect):
        """Test ADD UNIQUE constraint SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraint
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
            TableConstraintType,
        )

        action = AddTableConstraint(
            dialect,
            constraint=TableConstraint(dialect, 
                constraint_type=TableConstraintType.UNIQUE,
                columns=["email"],
            ),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "UNIQUE" in sql
        assert "email" in sql

    def test_format_add_check_constraint(self, dialect):
        """Test ADD CHECK constraint SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraint
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
            TableConstraintType,
        )
        from rhosocial.activerecord.backend.expression import Column as ExprColumn, Literal

        check_condition = ExprColumn(dialect, "age") > Literal(dialect, 0)
        action = AddTableConstraint(
            dialect,
            constraint=TableConstraint(dialect, 
                constraint_type=TableConstraintType.CHECK,
                check_condition=check_condition,
            ),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "CHECK" in sql
        assert "age" in sql

    def test_format_add_foreign_key_constraint(self, dialect):
        """Test ADD FOREIGN KEY constraint SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraint
        from rhosocial.activerecord.backend.expression.statements.ddl_table import ForeignKeyConstraint

        action = AddTableConstraint(
            dialect,
            constraint=ForeignKeyConstraint(dialect, 
                columns=["user_id"],
                foreign_key_table="users",
                foreign_key_columns=["id"],
            ),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "FOREIGN KEY" in sql
        assert "user_id" in sql
        assert "users" in sql

    def test_format_add_named_constraint(self, dialect):
        """Test ADD CONSTRAINT with name SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraint
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
            TableConstraintType,
        )

        action = AddTableConstraint(
            dialect,
            constraint=TableConstraint(dialect, 
                constraint_type=TableConstraintType.UNIQUE,
                name="uk_email",
                columns=["email"],
            ),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "CONSTRAINT" in sql
        assert "uk_email" in sql
        assert "UNIQUE" in sql

    def test_format_drop_constraint(self, dialect):
        """Test DROP CONSTRAINT SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraint

        action = DropTableConstraint(
            dialect,
            constraint_name="uk_email",
        )
        sql, params = dialect.format_drop_table_constraint_action(action)
        assert "DROP CONSTRAINT" in sql
        assert "uk_email" in sql


class TestConstraintEnforcementAndValidation:
    def test_table_and_column_enforcement(self):
        from rhosocial.activerecord.backend.expression import (
            Column,
            ColumnConstraint,
            ColumnConstraintType,
            ColumnDefinition,
            CreateTableExpression,
            Literal,
            TableConstraint,
            TableConstraintType,
        )
        from rhosocial.activerecord.backend.expression.types import IntegerType
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        dialect = DummyDialect()
        condition = Column(dialect, "age") > Literal(dialect, 0, inline_literals=True)
        table_constraint = TableConstraint(
            dialect,
            TableConstraintType.CHECK,
            name="age_check",
            check_condition=condition,
            enforced=False,
        )
        column_constraint = ColumnConstraint(
            dialect,
            ColumnConstraintType.CHECK,
            check_condition=condition,
            enforced=False,
        )
        expression = CreateTableExpression(
            dialect,
            "people",
            [ColumnDefinition(dialect, "age", IntegerType(dialect), [column_constraint])],
            table_constraints=[table_constraint],
        )

        sql, params = expression.to_sql()

        assert sql == (
            'CREATE TABLE "people" ("age" INTEGER CHECK ("age" > 0) NOT ENFORCED, '
            'CONSTRAINT "age_check" CHECK ("age" > 0) NOT ENFORCED)'
        )
        assert params == ()

    def test_add_constraint_validation_is_type_specific(self):
        from rhosocial.activerecord.backend.expression import AddTableConstraint, TableConstraint, TableConstraintType
        from rhosocial.activerecord.backend.expression.statements import ConstraintValidation
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        dialect = DummyDialect()
        for constraint_type in (TableConstraintType.PRIMARY_KEY, TableConstraintType.UNIQUE):
            constraint = TableConstraint(
                dialect,
                constraint_type,
                columns=["id"],
                validation=ConstraintValidation.NOVALIDATE,
            )
            with pytest.raises(ValueError, match="NOT VALID"):
                AddTableConstraint(dialect, constraint).to_sql()

    def test_enforcement_capability_is_gated(self):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression import Column, ColumnConstraint, ColumnConstraintType, Literal
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        condition = Column(dialect, "age") > Literal(dialect, 0, inline_literals=True)
        constraint = ColumnConstraint(
            dialect,
            ColumnConstraintType.CHECK,
            check_condition=condition,
            enforced=False,
        )
        with pytest.raises(UnsupportedFeatureError):
            constraint.to_sql()

    def test_binder_preserves_column_enforcement(self):
        from rhosocial.activerecord.backend.expression import ColumnConstraint, ColumnConstraintType
        from rhosocial.activerecord.ddl.binder import DialectBinder
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        declared = ColumnConstraint(
            None,
            ColumnConstraintType.NOT_NULL,
            enforced=False,
        )
        bound = DialectBinder(DummyDialect()).bind(declared)

        assert bound.enforced is False

    def test_alter_constraint_actions(self):
        from rhosocial.activerecord.backend.expression import (
            AlterConstraint,
            ColumnConstraintType,
            TableConstraintType,
            ValidateConstraint,
        )
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        dialect = DummyDialect()

        action = AlterConstraint(
            dialect,
            "age_check",
            False,
            constraint_type=ColumnConstraintType.CHECK,
        )
        assert action.constraint_type is TableConstraintType.CHECK
        assert action.to_sql()[0] == 'ALTER CONSTRAINT "age_check" NOT ENFORCED'
        assert ValidateConstraint(dialect, "age_check").to_sql()[0] == (
            'VALIDATE CONSTRAINT "age_check"'
        )
        with pytest.raises(TypeError):
            AlterConstraint(dialect, "age_check", False)

    def test_constraint_type_and_validation_strings_are_normalized(self):
        from rhosocial.activerecord.backend.expression import (
            AddTableConstraint,
            Column,
            Literal,
            TableConstraint,
        )
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        dialect = DummyDialect()
        constraint = TableConstraint(
            dialect,
            " check ",
            check_condition=Column(dialect, "age") > Literal(dialect, 0),
            validation=" not valid ",
        )

        assert AddTableConstraint(dialect, constraint).to_sql()[0].endswith("NOT VALID")
        assert "NOT VALID" not in constraint.to_sql()[0]

    def test_check_predicate_inlines_literals_and_rejects_raw_parameters(self):
        from rhosocial.activerecord.backend.expression import (
            Column,
            Literal,
            RawSQLPredicate,
            TableConstraint,
        )
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        dialect = DummyDialect()
        trusted = TableConstraint(
            dialect,
            "CHECK",
            check_condition=Column(dialect, "age") > Literal(dialect, 0),
        )
        assert trusted.to_sql() == ('CHECK ("age" > 0)', ())

        unsafe = TableConstraint(
            dialect,
            "CHECK",
            check_condition=RawSQLPredicate(dialect, "age > %s", (0,)),
        )
        with pytest.raises(ValueError, match="must not contain bind parameters"):
            unsafe.to_sql()

    def test_exclude_is_rejected_on_unsupported_dialect(self):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression import TableConstraint, TableConstraintType
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        constraint = TableConstraint(SQLiteDialect(), TableConstraintType.EXCLUDE)
        with pytest.raises(UnsupportedFeatureError, match="EXCLUDE"):
            constraint.to_sql()
