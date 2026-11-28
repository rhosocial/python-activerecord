# tests/rhosocial/activerecord_test/feature/backend/dummy/ddl/test_constraint_protocol.py
"""Tests for ConstraintSupport protocol and ConstraintMixin."""

import pytest
from rhosocial.activerecord.backend.expression.statements import (
    ColumnCheckConstraint,
    TableCheckConstraint,
    TableConstraint,
    TableExcludeConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.dialect.mixins import ConstraintMixin
from rhosocial.activerecord.backend.dialect.protocols import ConstraintSupport
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

    def test_supports_drop_constraint_by_kind_defaults_false(self, dummy_dialect: DummyDialect):
        """A by-kind drop is opt-in; core's dummy spells names only."""
        assert dummy_dialect.supports_drop_constraint_by_kind() is False

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

    def test_modifiers_default_false_and_constructors_default_true(self):
        """A modifier defaults to False; a constructor to True.

        Constraint kinds (PRIMARY KEY, UNIQUE, ...) are things every grammar
        has, so they default True and a dialect overrides to refuse. The
        SQL:1999/SQL:2016 modifiers (DEFERRABLE, ENFORCED) are optional
        grammar, so they default False and the dialects that have them opt
        in. Constraint naming is part of the SQL-92 production itself, so it
        defaults True.
        """

        class TestDialect(ConstraintMixin):
            pass

        dialect = TestDialect()
        assert dialect.supports_fk_match() is True
        assert dialect.supports_primary_key_constraint() is True
        assert dialect.supports_unique_constraint() is True
        assert dialect.supports_constraint_naming() is True
        assert dialect.supports_deferrable_constraint() is False
        assert dialect.supports_constraint_enforced() is False
        assert dialect.supports_alter_constraint_enforced() is False

    def test_alter_table_constraint_operations_default_true(self):
        """ALTER TABLE constraint operations default to True."""

        class TestDialect(ConstraintMixin):
            pass

        dialect = TestDialect()
        assert dialect.supports_add_constraint() is True
        assert dialect.supports_drop_constraint() is True
        assert dialect.supports_drop_constraint_by_kind() is False


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
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraintAction
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
        )

        action = AddTableConstraintAction(
            dialect,
            constraint=TableConstraint(dialect, branch=TablePrimaryKeyConstraint(dialect, ["id"])),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "PRIMARY KEY" in sql
        assert "id" in sql

    def test_format_add_unique_constraint(self, dialect):
        """Test ADD UNIQUE constraint SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraintAction
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
        )

        action = AddTableConstraintAction(
            dialect,
            constraint=TableConstraint(dialect, branch=TableUniqueConstraint(dialect, ["email"])),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "UNIQUE" in sql
        assert "email" in sql

    def test_format_add_check_constraint(self, dialect):
        """Test ADD CHECK constraint SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraintAction
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
        )
        from rhosocial.activerecord.backend.expression import NumericColumn, Parameter

        check_condition = NumericColumn(dialect, "age") > Parameter(dialect, 0, inline=True)
        action = AddTableConstraintAction(
            dialect,
            constraint=TableConstraint(dialect, branch=TableCheckConstraint(dialect, check_condition)),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "CHECK" in sql
        assert "age" in sql

    def test_format_add_foreign_key_constraint(self, dialect):
        """Test ADD FOREIGN KEY constraint SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraintAction
        from rhosocial.activerecord.backend.expression.statements.ddl_table import ForeignKeyConstraint

        action = AddTableConstraintAction(
            dialect,
            constraint=ForeignKeyConstraint(dialect, 
                columns=["user_id"],
                foreign_key_table=Table(dialect, "users"),
                foreign_key_columns=["id"],
            ),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "FOREIGN KEY" in sql
        assert "user_id" in sql
        assert "users" in sql

    def test_format_add_named_constraint(self, dialect):
        """Test ADD CONSTRAINT with name SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import AddTableConstraintAction
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            TableConstraint,
            TableUniqueConstraint,
        )

        action = AddTableConstraintAction(
            dialect,
            constraint=TableConstraint(dialect, branch=TableUniqueConstraint(dialect, ["email"]), name="uk_email"),
        )
        sql, params = dialect.format_add_table_constraint_action(action)
        assert "CONSTRAINT" in sql
        assert "uk_email" in sql
        assert "UNIQUE" in sql

    def test_format_drop_constraint(self, dialect):
        """Test DROP CONSTRAINT SQL generation."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        action = DropTableConstraintAction(
            dialect,
            constraint_name="uk_email",
        )
        sql, params = dialect.format_drop_table_constraint_action(action)
        assert "DROP CONSTRAINT" in sql
        assert "uk_email" in sql

    def test_format_drop_constraint_by_declaration_is_refused_by_name(self, dialect):
        """A name-only dialect refuses a kind-based drop by feature name."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        constraint = TableConstraint(
            dialect,
            branch=TableUniqueConstraint(dialect, ["email"]),
            name="uk_email",
        )
        action = DropTableConstraintAction(dialect, constraint=constraint)
        with pytest.raises(UnsupportedFeatureError, match="DROP CONSTRAINT by kind") as excinfo:
            dialect.format_drop_table_constraint_action(action)
        assert excinfo.value.feature_name == "DROP CONSTRAINT by kind"

    def test_format_drop_constraint_confirmed_by_an_equal_name(self, dialect):
        """Both forms present and agreeing: the declaration confirms the name."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        constraint = TableConstraint(
            dialect,
            branch=TableUniqueConstraint(dialect, ["email"]),
            name="uk_email",
        )
        action = DropTableConstraintAction(
            dialect,
            constraint_name="uk_email",
            constraint=constraint,
        )
        sql, params = dialect.format_drop_table_constraint_action(action)
        assert sql == 'DROP CONSTRAINT "uk_email"'
        assert params == ()

    def test_format_drop_constraint_different_names_are_ambiguous(self, dialect):
        """Two disagreeing addresses are refused, never resolved by preference."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        constraint = TableConstraint(
            dialect,
            branch=TableUniqueConstraint(dialect, ["email"]),
            name="uk_mail",
        )
        action = DropTableConstraintAction(
            dialect,
            constraint_name="uk_email",
            constraint=constraint,
        )
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            dialect.format_drop_table_constraint_action(action)
        assert excinfo.value.feature_name == "DROP CONSTRAINT address"
        message = str(excinfo.value)
        assert "'uk_email'" in message
        assert "'uk_mail'" in message
        assert "ambiguous address is refused" in message

    def test_format_drop_constraint_unnamed_declaration_is_ambiguous(self, dialect):
        """A declaration with no name cannot confirm the given name."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        constraint = TableConstraint(
            dialect,
            branch=TableUniqueConstraint(dialect, ["email"]),
        )
        action = DropTableConstraintAction(
            dialect,
            constraint_name="uk_email",
            constraint=constraint,
        )
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            dialect.format_drop_table_constraint_action(action)
        assert excinfo.value.feature_name == "DROP CONSTRAINT address"
        message = str(excinfo.value)
        assert "'uk_email'" in message
        assert "None" in message
        assert "ambiguous address is refused" in message

    def test_format_drop_constraint_requires_one_address(self, dialect):
        """Neither a name nor a declaration is a malformed action."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        action = DropTableConstraintAction(dialect)
        with pytest.raises(ValueError, match="requires constraint_name or constraint"):
            dialect.format_drop_table_constraint_action(action)

    def test_format_drop_constraint_rejects_a_non_table_constraint(self, dialect):
        """A stray string is not a declaration and must not masquerade as one."""
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        action = DropTableConstraintAction(
            dialect,
            constraint_name="uk_email",
            constraint="uk_email",
        )
        with pytest.raises(TypeError, match="must be a TableConstraint"):
            dialect.format_drop_table_constraint_action(action)


class TestDropConstraintAddressResolution:
    """The address rule itself, exercised through the shared resolver."""

    @pytest.fixture
    def dialect(self):
        return DummyDialect()

    def _action(self, dialect, **kwargs):
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        return DropTableConstraintAction(dialect, **kwargs)

    def _declaration(self, dialect, name=None):
        return TableConstraint(
            dialect,
            branch=TableUniqueConstraint(dialect, ["email"]),
            name=name,
        )

    def test_name_only_resolves_to_name(self, dialect):
        action = self._action(dialect, constraint_name="uk_email")
        assert dialect._resolve_drop_constraint_address(action) == "name"

    def test_kind_only_on_a_name_only_dialect_is_refused(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        action = self._action(dialect, constraint=self._declaration(dialect, "uk_email"))
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            dialect._resolve_drop_constraint_address(action)
        assert excinfo.value.feature_name == "DROP CONSTRAINT by kind"
        assert str(excinfo.value) == (
            "'Dummy' dialect does not support DROP CONSTRAINT by kind. "
            "Suggestion: Dummy does not support DROP CONSTRAINT by kind; "
            "address the constraint by name instead."
        )

    def test_kind_only_on_a_kind_dialect_resolves_to_kind(self):
        class KindDropDialect(DummyDialect):
            def supports_drop_constraint_by_kind(self) -> bool:
                return True

        kind_dialect = KindDropDialect()
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropTableConstraintAction

        action = DropTableConstraintAction(
            kind_dialect, constraint=self._declaration(kind_dialect, "uk_email")
        )
        assert kind_dialect._resolve_drop_constraint_address(action) == "kind"
        with pytest.raises(NotImplementedError, match="override format_drop_table_constraint_action"):
            kind_dialect.format_drop_table_constraint_action(action)

    def test_equal_names_resolve_to_name(self, dialect):
        action = self._action(
            dialect,
            constraint_name="uk_email",
            constraint=self._declaration(dialect, "uk_email"),
        )
        assert dialect._resolve_drop_constraint_address(action) == "name"

    def test_different_names_are_an_ambiguous_address(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        action = self._action(
            dialect,
            constraint_name="uk_email",
            constraint=self._declaration(dialect, "uk_mail"),
        )
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            dialect._resolve_drop_constraint_address(action)
        assert excinfo.value.feature_name == "DROP CONSTRAINT address"
        message = str(excinfo.value)
        assert "'uk_email'" in message
        assert "'uk_mail'" in message
        assert "ambiguous address is refused" in message

    def test_unnamed_declaration_is_an_ambiguous_address(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        action = self._action(
            dialect,
            constraint_name="uk_email",
            constraint=self._declaration(dialect),
        )
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            dialect._resolve_drop_constraint_address(action)
        assert excinfo.value.feature_name == "DROP CONSTRAINT address"
        assert "ambiguous address is refused" in str(excinfo.value)

    def test_no_address_is_value_error(self, dialect):
        action = self._action(dialect)
        with pytest.raises(ValueError, match="requires constraint_name or constraint"):
            dialect._resolve_drop_constraint_address(action)

    def test_non_table_constraint_is_type_error(self, dialect):
        action = self._action(
            dialect, constraint_name="uk_email", constraint="uk_email"
        )
        with pytest.raises(TypeError, match="must be a TableConstraint"):
            dialect._resolve_drop_constraint_address(action)


class TestConstraintEnforcementAndValidation:
    def test_table_and_column_enforcement(self):
        from rhosocial.activerecord.backend.expression import (
            Column,
            ColumnConstraint,
            ColumnDefinition,
            ComparisonPredicate,
            CreateTableStatement,
            Parameter,
            TableConstraint,)
        from rhosocial.activerecord.backend.expression.types import IntegerType

        dialect = DummyDialect()
        condition = ComparisonPredicate(dialect, ">", Column(dialect, "age"), Parameter(dialect, 0, inline=True))
        table_constraint = TableConstraint(
            dialect,
            branch=TableCheckConstraint(dialect, condition),
            name="age_check",
            not_enforced=True,
        )
        column_constraint = ColumnConstraint(
            dialect,
            branch=ColumnCheckConstraint(dialect, condition),
            not_enforced=True,
        )
        expression = CreateTableStatement(
            dialect,
            Table(dialect, 'people'),
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
        from rhosocial.activerecord.backend.expression import (
    AddTableConstraintAction,
    TableConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
        from rhosocial.activerecord.backend.expression.statements import ConstraintValidation

        dialect = DummyDialect()
        for branch_cls in (TablePrimaryKeyConstraint, TableUniqueConstraint):
            constraint = TableConstraint(
                dialect,
                branch=branch_cls(dialect, ["id"]),
                validation=ConstraintValidation.NOVALIDATE,
            )
            with pytest.raises(ValueError, match="NOT VALID"):
                AddTableConstraintAction(dialect, constraint).to_sql()

    def test_enforcement_capability_is_gated(self):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression import (
            ColumnCheckConstraint,
            ColumnConstraint,
            Parameter,
            NumericColumn,
        )
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        condition = NumericColumn(dialect, "age") > Parameter(dialect, 0, inline=True)
        constraint = ColumnConstraint(dialect, branch=ColumnCheckConstraint(dialect, condition), not_enforced=True)
        with pytest.raises(UnsupportedFeatureError):
            constraint.to_sql()

    def test_alter_constraint_actions(self):
        from rhosocial.activerecord.backend.expression import (
            AlterConstraintAction,
            ValidateConstraintAction,
            TableCheckConstraint,
        )

        dialect = DummyDialect()

        action = AlterConstraintAction(
            dialect,
            "age_check",
            not_enforced=True,
            constraint_kind=TableCheckConstraint,
        )
        assert action.constraint_branch is TableCheckConstraint
        assert action.to_sql()[0] == 'ALTER CONSTRAINT "age_check" NOT ENFORCED'
        assert ValidateConstraintAction(dialect, "age_check").to_sql()[0] == (
            'VALIDATE CONSTRAINT "age_check"'
        )
        # The enforcement keyword is mandatory, and that is judged at render
        # time: the node itself always builds, so a stored artifact can be
        # read back and refused by name.
        incomplete = AlterConstraintAction(
            dialect, "age_check", constraint_kind=TableCheckConstraint
        )
        with pytest.raises(TypeError, match="requires exactly one of"):
            incomplete.to_sql()

    def test_branch_and_validation_types_are_refused(self):
        """The branch names the kind and ``validation`` names its spelling;
        neither accepts a string in place of the declared type.

        The kind used to be a runtime-normalised enum member or its name, and
        ``validation`` was normalised at render time — a fallback that let a
        mistyped value reach the dialect before failing. The kind is now a
        class, which cannot be spelled at all, and ``validation`` is refused
        where it is read.
        """
        from rhosocial.activerecord.backend.expression import (
            AddTableConstraintAction,
            ConstraintValidation,
            Parameter,
            NumericColumn,
            TableConstraint,
            TableCheckConstraint,
        )

        dialect = DummyDialect()
        condition = NumericColumn(dialect, "age") > Parameter(dialect, 0, inline=True)
        typed = TableConstraint(
            dialect,
            branch=TableCheckConstraint(dialect, condition),
            validation=ConstraintValidation.NOVALIDATE,
        )

        assert AddTableConstraintAction(dialect, typed).to_sql()[0].endswith("NOT VALID")
        assert "NOT VALID" not in typed.to_sql()[0]

        with pytest.raises(TypeError, match="TableConstraintBranch"):
            TableConstraint(dialect, branch=" check ")
        with pytest.raises(TypeError, match="ConstraintValidation"):
            AddTableConstraintAction(
                dialect,
                TableConstraint(
                    dialect,
                    branch=TableCheckConstraint(
                        dialect, NumericColumn(dialect, "age") > Parameter(dialect, 0, inline=True)
                    ),
                    validation=" not valid ",
                ),
            ).to_sql()

    def test_check_predicate_inlines_marked_literals_and_carries_the_rest(self):
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Parameter,
            RawSQLPredicate,
            TableConstraint,
            TableCheckConstraint,
        )

        dialect = DummyDialect()
        condition = ComparisonPredicate(
            dialect, ">", Column(dialect, "age"), Parameter(dialect, 0, inline=True)
        )
        trusted = TableConstraint(
            dialect, branch=TableCheckConstraint(dialect, condition)
        )
        assert trusted.to_sql() == ('CHECK ("age" > 0)', ())

        # A value the caller left as a bind value stays one: the statement
        # carries it in params, and the engine refuses it if it cannot take it.
        raw = RawSQLPredicate(dialect, "age > %s", (0,))
        unsafe = TableConstraint(
            dialect, branch=TableCheckConstraint(dialect, raw)
        )
        sql, params = unsafe.to_sql()
        assert params == (0,)

    def test_exclude_is_rejected_on_unsupported_dialect(self):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        from rhosocial.activerecord.backend.expression import (
            TableConstraint,
        )
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        constraint = TableConstraint(dialect, branch=TableExcludeConstraint(dialect, ["ts"]))
        with pytest.raises(UnsupportedFeatureError, match="EXCLUDE"):
            constraint.to_sql()


class TestInPredicateInDDLCheckConstraints:
    """``IN`` must be usable inside a CHECK constraint.

    PostgreSQL and MySQL both reject bind parameters in DDL, and the CHECK
    classes declare ``inline_binding = True``: the dialect preparation pass
    marks every literal inside a CHECK predicate ``inline``, the decision
    whose strategy is inline. ``InPredicate`` reads that class-level strategy
    when rendering the value list, so the ``IN`` shape participates in the
    same lift as every other predicate.
    """

    def _check(self, dialect, condition):
        from rhosocial.activerecord.backend.expression import (
            TableConstraint,
            TableCheckConstraint,
        )
        return TableConstraint(dialect, branch=TableCheckConstraint(dialect, condition))

    def test_in_list_inlines_inside_a_check(self, dummy_dialect: DummyDialect):
        from rhosocial.activerecord.backend.expression import InPredicate, Parameter, Column

        constraint = self._check(
            dummy_dialect,
            InPredicate(dummy_dialect,
                       Column(dummy_dialect, "direction"), Parameter(dummy_dialect, ("debit", "credit"), inline=True)),
        )
        assert constraint.to_sql() == (
            'CHECK ("direction" IN (\'debit\', \'credit\'))', (),
        )

    def test_in_tuple_inlines_inside_a_check(self, dummy_dialect: DummyDialect):
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter

        condition = InPredicate(
            dummy_dialect,
            Column(dummy_dialect, "direction"),
            Parameter(dummy_dialect, ("debit", "credit"), inline=True),
        )
        assert self._check(dummy_dialect, condition).to_sql() == (
            'CHECK ("direction" IN (\'debit\', \'credit\'))', (),
        )

    def test_not_in_inlines_inside_a_check(self, dummy_dialect: DummyDialect):
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter, LogicalPredicate

        constraint = self._check(
            dummy_dialect,
            LogicalPredicate(
                dummy_dialect,
                "NOT",
                InPredicate(dummy_dialect,
                           Column(dummy_dialect, "state"), Parameter(dummy_dialect, ("a", "b"), inline=True)),
            ),
        )
        assert constraint.to_sql() == (
            'CHECK (NOT ("state" IN (\'a\', \'b\')))', (),
        )

    def test_numeric_in_list_inlines_inside_a_check(self, dummy_dialect: DummyDialect):
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter

        constraint = self._check(
            dummy_dialect,
            InPredicate(dummy_dialect,
                       Column(dummy_dialect, "priority"), Parameter(dummy_dialect, (1, 2, 3), inline=True)),
        )
        assert constraint.to_sql() == (
            'CHECK ("priority" IN (1, 2, 3))', (),
        )

    def test_in_list_escapes_quotes_when_inlined(self, dummy_dialect: DummyDialect):
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter

        constraint = self._check(
            dummy_dialect,
            InPredicate(dummy_dialect, Column(dummy_dialect, "label"), Parameter(dummy_dialect, ("a'b",), inline=True)),
        )
        assert constraint.to_sql() == ('CHECK ("label" IN (\'a\'\'b\'))', ())

    def test_in_list_with_null_inlines_inside_a_check(self, dummy_dialect: DummyDialect):
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter

        constraint = self._check(
            dummy_dialect,
            InPredicate(dummy_dialect, Column(dummy_dialect, "parent"), Parameter(dummy_dialect, (None, 1), inline=True)),
        )
        assert constraint.to_sql() == ('CHECK ("parent" IN (NULL, 1))', ())

    def test_empty_in_list_stays_empty_parens(self, dummy_dialect: DummyDialect):
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter

        constraint = self._check(
            dummy_dialect,
            InPredicate(dummy_dialect, Column(dummy_dialect, "direction"), Parameter(dummy_dialect, ())),
        )
        assert constraint.to_sql() == ('CHECK ("direction" IN ())', ())

    def test_in_list_still_binds_outside_ddl(self, dummy_dialect: DummyDialect):
        """The DML path must be untouched: inlining there would be an injection."""
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter

        condition = InPredicate(
            dummy_dialect, Column(dummy_dialect, "direction"), Parameter(dummy_dialect, ("debit", "credit"))
        )
        assert condition.to_sql() == ('"direction" IN (?, ?)', ("debit", "credit"))

    def test_subquery_in_does_not_go_through_the_value_list_path(
        self, dummy_dialect: DummyDialect
    ):
        """A subquery renders through its own to_sql(), so the collection fix
        must not touch it -- that path has no Parameter and no inline flag."""
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Subquery

        condition = InPredicate(
            dummy_dialect,
            Column(dummy_dialect, "id"),
            Subquery(dummy_dialect, "SELECT id FROM other", ()),
        )
        sql, params = condition.to_sql()
        assert "SELECT id FROM other" in sql
        assert params == ()

    def test_literal_wrapping_a_list_outside_ddl_still_binds(
        self, dummy_dialect: DummyDialect
    ):
        """Hand-building the Parameter is the documented IN form; it must behave
        the same as the plain list call when the inline flag is off."""
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter

        condition = InPredicate(
            dummy_dialect,
            Column(dummy_dialect, "direction"),
            Parameter(dummy_dialect, ["debit", "credit"]),
        )
        assert condition.to_sql() == ('"direction" IN (?, ?)', ("debit", "credit"))

    def test_ddl_literal_list_renders_inline_without_ddl(
        self, dummy_dialect: DummyDialect
    ):
        """The DDL-position literal class inlines on its own, not only via
        DDL preparation."""
        from rhosocial.activerecord.backend.expression import Column, InPredicate, Parameter

        condition = InPredicate(
            dummy_dialect,
            Column(dummy_dialect, "direction"),
            Parameter(dummy_dialect, ("debit", "credit"), inline=True),
        )
        assert condition.to_sql() == ('"direction" IN (\'debit\', \'credit\')', ())
