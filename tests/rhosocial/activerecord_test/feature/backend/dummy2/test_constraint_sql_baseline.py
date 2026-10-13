# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_constraint_sql_baseline.py
# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_constraint_sql_baseline.py
"""The SQL every constraint form renders, byte for byte.

This is the baseline the two-level constraint nodes (S3) must not move. That
refactor changes which node carries which field and where the constraint-level
prefix and the trailing traits are rendered; it does not change a character of
the output. Every form the grammar allows is rendered here once, so a diff after
the refactor names the form that moved instead of leaving it to be found in a
diff of everything.

Two entries below record **current behaviour that S3 is meant to change**, and
say so where they live: a column-level PRIMARY KEY drops the deferral traits,
and a column-level FOREIGN KEY renders only the ``REFERENCES`` half. They are
here as measurements, not endorsements -- see
``s3-constraint-branch-nodes-design.md``.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _check(dialect):
    """``age > 0`` -- DDL takes no bind parameters, so this renders inlined."""
    return ComparisonPredicate(dialect, ">", Column(dialect, "age"), Literal(dialect, 0))


def _probed(dialect_cls=DummyDialect, **answers):
    """A dialect subclass whose capability probes answer as ``answers``."""
    namespace = {name: (lambda self, answer=answer: answer) for name, answer in answers.items()}
    return type("ProbedDialect", (dialect_cls,), namespace)


class TestColumnConstraintBaseline:
    def test_bare_kinds(self, dummy_dialect):
        for ctype, expected in (
            (ColumnConstraintType.NOT_NULL, " NOT NULL"),
            (ColumnConstraintType.NULL, " NULL"),
            (ColumnConstraintType.UNIQUE, " UNIQUE"),
        ):
            assert ColumnConstraint(dummy_dialect, ctype).to_sql() == (expected, ())

    def test_named_prefix(self, dummy_dialect):
        assert ColumnConstraint(
            dummy_dialect, ColumnConstraintType.NOT_NULL, name="nn_users_age"
        ).to_sql() == (' CONSTRAINT "nn_users_age" NOT NULL', ())

    def test_primary_key(self, dummy_dialect):
        assert ColumnConstraint(
            dummy_dialect, ColumnConstraintType.PRIMARY_KEY
        ).to_sql() == (" PRIMARY KEY", ())

    def test_primary_key_autoincrement_is_sqlite_only(self, dummy_dialect):
        """AUTOINCREMENT is part of SQLite's grammar and nowhere else."""
        assert ColumnConstraint(
            dummy_dialect, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True
        ).to_sql() == (" PRIMARY KEY", ())
        assert ColumnConstraint(
            SQLiteDialect(), ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True
        ).to_sql() == (" PRIMARY KEY AUTOINCREMENT", ())

    def test_check_inlines_its_literal(self, dummy_dialect):
        assert ColumnConstraint(
            dummy_dialect, ColumnConstraintType.CHECK, check_condition=_check(dummy_dialect)
        ).to_sql() == (' CHECK ("age" > 0)', ())

    def test_default_inlines_its_value(self, dummy_dialect):
        assert ColumnConstraint(
            dummy_dialect, ColumnConstraintType.DEFAULT, default_value=Literal(dummy_dialect, 7)
        ).to_sql() == (" DEFAULT 7", ())

    def test_foreign_key_renders_the_references_half_only(self, dummy_dialect):
        """Current shape: no ``FOREIGN KEY (col)`` prefix, and no space before
        the column list. S3 keeps the bytes; fixing the spelling is a separate
        change with its own before/after."""
        assert ColumnConstraint(
            dummy_dialect,
            ColumnConstraintType.FOREIGN_KEY,
            foreign_key_reference=(Table(dummy_dialect, "users"), ["id"]),
        ).to_sql() == (' REFERENCES "users"("id")', ())

    def test_foreign_key_renders_the_deferral_traits(self, dummy_dialect):
        dialect = _probed(supports_deferrable_constraint=True)()
        assert ColumnConstraint(
            dialect,
            ColumnConstraintType.FOREIGN_KEY,
            foreign_key_reference=(Table(dialect, "users"), ["id"]),
            deferrable=True,
            initially_deferred=True,
        ).to_sql() == (' REFERENCES "users"("id") DEFERRABLE INITIALLY DEFERRED', ())

    def test_foreign_key_refuses_deferral_without_support(self, dummy_dialect):
        dialect = _probed(supports_deferrable_constraint=False)()
        with pytest.raises(UnsupportedFeatureError, match="DEFERRABLE"):
            ColumnConstraint(
                dialect,
                ColumnConstraintType.FOREIGN_KEY,
                foreign_key_reference=(Table(dialect, "users"), ["id"]),
                deferrable=True,
            ).to_sql()

    def test_primary_key_drops_the_deferral_traits(self, dummy_dialect):
        """Current behaviour S3 is meant to change: only the foreign-key
        formatter reads them, so a request on a PRIMARY KEY is accepted and
        then dropped -- silently, even on a dialect that declares support."""
        dialect = _probed(supports_deferrable_constraint=True)()
        assert ColumnConstraint(
            dialect,
            ColumnConstraintType.PRIMARY_KEY,
            deferrable=True,
            initially_deferred=True,
        ).to_sql() == (" PRIMARY KEY", ())

    def test_enforced_trait(self, dummy_dialect):
        dialect = _probed(supports_constraint_enforcement=True)()
        assert ColumnConstraint(
            dialect,
            ColumnConstraintType.CHECK,
            check_condition=_check(dialect),
            not_enforced=True,
        ).to_sql() == (' CHECK ("age" > 0) NOT ENFORCED', ())

    def test_default_is_not_an_enforceable_kind(self, dummy_dialect):
        """A kind that cannot carry the trait says so by name, and says which
        kinds can -- the constructor accepted the request, so the refusal
        belongs here."""
        dialect = _probed(supports_constraint_enforcement=True)()
        with pytest.raises(ValueError, match="cannot ride a DEFAULT constraint"):
            ColumnConstraint(
                dialect,
                ColumnConstraintType.DEFAULT,
                default_value=Literal(dialect, 1),
                enforced=True,
            ).to_sql()

    def test_named_prefix_needs_the_capability(self, dummy_dialect):
        dialect = _probed(supports_constraint_naming=False)()
        with pytest.raises(UnsupportedFeatureError, match="CONSTRAINT"):
            ColumnConstraint(
                dialect, ColumnConstraintType.NOT_NULL, name="nn"
            ).to_sql()


class TestTableConstraintBaseline:
    def test_primary_key_and_unique(self, dummy_dialect):
        assert TableConstraint(
            dummy_dialect, TableConstraintType.PRIMARY_KEY, columns=["id"]
        ).to_sql() == ('PRIMARY KEY ("id")', ())
        assert TableConstraint(
            dummy_dialect, TableConstraintType.UNIQUE, columns=["email"]
        ).to_sql() == ('UNIQUE ("email")', ())

    def test_foreign_key(self, dummy_dialect):
        assert TableConstraint(
            dummy_dialect,
            TableConstraintType.FOREIGN_KEY,
            columns=["user_id"],
            foreign_key_table=Table(dummy_dialect, "users"),
            foreign_key_columns=["id"],
        ).to_sql() == ('FOREIGN KEY ("user_id") REFERENCES "users"("id")', ())

    def test_check(self, dummy_dialect):
        assert TableConstraint(
            dummy_dialect, TableConstraintType.CHECK, check_condition=_check(dummy_dialect)
        ).to_sql() == ('CHECK ("age" > 0)', ())

    def test_named_prefix_and_enforced(self, dummy_dialect):
        dialect = _probed(supports_constraint_enforcement=True)()
        assert TableConstraint(
            dialect,
            TableConstraintType.CHECK,
            name="ck_users_age",
            check_condition=_check(dialect),
            not_enforced=True,
        ).to_sql() == ('CONSTRAINT "ck_users_age" CHECK ("age" > 0) NOT ENFORCED', ())

    def test_validation_is_a_field_the_node_keeps(self, dummy_dialect):
        """``NOT VALID`` is refused by the CREATE TABLE path, not here -- the
        constraint alone has no say in where it is being added."""
        assert TableConstraint(
            dummy_dialect,
            TableConstraintType.CHECK,
            check_condition=_check(dummy_dialect),
            validation="NOTVALID",
        ).validation == "NOTVALID"