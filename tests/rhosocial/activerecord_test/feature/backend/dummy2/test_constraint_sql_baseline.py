# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_constraint_sql_baseline.py
"""The SQL every constraint form renders, byte for byte.

This is the baseline the two-level constraint nodes (S3) must not move, and
it is written against the branch nodes: each form is now spelled the way a
caller must spell it, so the test doubles as evidence that the branch is what
says which kind a constraint is. The refactor changed which node carries which
field and where the constraint-level prefix and the trailing traits are
rendered; it did not change a character of the output.

Two entries record **behaviour S3 deliberately changed**, and say so where
they live: the deferral traits now render on every branch that can carry them
(a column-level PRIMARY KEY used to drop them silently, because only the
foreign-key formatter read them), and a request for a trait a branch cannot
carry is refused where the node is built instead of being accepted and
dropped.
"""

import pytest
from rhosocial.activerecord.backend.expression.statements import (
    ColumnCheckConstraint,
    ColumnDefaultConstraint,
    ColumnForeignKeyConstraint,
    ColumnNotNullConstraint,
    ColumnNullableConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
    TableCheckConstraint,
    TableExcludeConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    TableConstraint,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError



def _check(dialect):
    """``age > 0`` -- DDL takes no bind parameters, so this renders inlined."""
    return ComparisonPredicate(dialect, ">", Column(dialect, "age"), Literal(dialect, 0))


def _probed(dialect_cls=DummyDialect, **answers):
    """A dialect subclass whose capability probes answer as ``answers``."""
    namespace = {name: (lambda self, answer=answer: answer) for name, answer in answers.items()}
    return type("ProbedDialect", (dialect_cls,), namespace)


class TestColumnConstraintBaseline:
    def test_bare_branches(self, dummy_dialect):
        cases = (
            (ColumnNotNullConstraint, " NOT NULL"),
            (ColumnNullableConstraint, " NULL"),
            (ColumnUniqueConstraint, " UNIQUE"),
            (ColumnPrimaryKeyConstraint, " PRIMARY KEY"),
        )
        for branch_cls, expected in cases:
            clause = ColumnConstraint(dummy_dialect, branch=branch_cls(dummy_dialect))
            assert clause.to_sql() == (expected, ())

    def test_named_prefix(self, dummy_dialect):
        clause = ColumnConstraint(
            dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect), name="nn_users_age"
        )
        assert clause.to_sql() == (' CONSTRAINT "nn_users_age" NOT NULL', ())

    def test_primary_key_autoincrement_is_sqlite_only(self, dummy_dialect):
        """AUTOINCREMENT is part of SQLite's grammar and nowhere else."""
        clause = ColumnConstraint(
            dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect, True)
        )
        assert clause.to_sql() == (" PRIMARY KEY", ())
        sqlite = SQLiteDialect()
        assert ColumnConstraint(
            sqlite, branch=ColumnPrimaryKeyConstraint(sqlite, True)
        ).to_sql() == (" PRIMARY KEY AUTOINCREMENT", ())

    def test_check_inlines_its_literal(self, dummy_dialect):
        clause = ColumnConstraint(
            dummy_dialect, branch=ColumnCheckConstraint(dummy_dialect, _check(dummy_dialect))
        )
        assert clause.to_sql() == (' CHECK ("age" > 0)', ())

    def test_default_inlines_its_value(self, dummy_dialect):
        clause = ColumnConstraint(
            dummy_dialect,
            branch=ColumnDefaultConstraint(dummy_dialect, Literal(dummy_dialect, 7)),
        )
        assert clause.to_sql() == (" DEFAULT 7", ())

    def test_foreign_key_renders_the_references_half_only(self, dummy_dialect):
        """Current shape: no ``FOREIGN KEY (col)`` prefix, and no space before
        the column list. S3 keeps the bytes; fixing the spelling is a separate
        change with its own before/after."""
        clause = ColumnConstraint(
            dummy_dialect,
            branch=ColumnForeignKeyConstraint(
                dummy_dialect, (Table(dummy_dialect, "users"), ["id"])
            ),
        )
        assert clause.to_sql() == (' REFERENCES "users"("id")', ())

    def test_foreign_key_renders_the_deferral_traits(self, dummy_dialect):
        dialect = _probed(supports_deferrable_constraint=True)()
        clause = ColumnConstraint(
            dialect,
            branch=ColumnForeignKeyConstraint(
                dialect, (Table(dialect, "users"), ["id"])
            ),
            deferrable=True,
            initially_deferred=True,
        )
        assert clause.to_sql() == (' REFERENCES "users"("id") DEFERRABLE INITIALLY DEFERRED', ())

    def test_foreign_key_refuses_deferral_without_support(self, dummy_dialect):
        dialect = _probed(supports_deferrable_constraint=False)()
        clause = ColumnConstraint(
            dialect,
            branch=ColumnForeignKeyConstraint(
                dialect, (Table(dialect, "users"), ["id"])
            ),
            deferrable=True,
        )
        with pytest.raises(UnsupportedFeatureError, match="DEFERRABLE"):
            clause.to_sql()

    def test_primary_key_renders_the_deferral_traits_now(self, dummy_dialect):
        """Changed by S3: the traits are the production's, so every branch that
        can carry them renders them. They used to be read by the foreign-key
        formatter alone and dropped on everything else."""
        dialect = _probed(supports_deferrable_constraint=True)()
        clause = ColumnConstraint(
            dialect,
            branch=ColumnPrimaryKeyConstraint(dialect),
            deferrable=True,
            initially_deferred=True,
        )
        assert clause.to_sql() == (" PRIMARY KEY DEFERRABLE INITIALLY DEFERRED", ())

    def test_a_trait_the_branch_cannot_carry_is_refused_at_construction(self, dummy_dialect):
        """The defect this refactor exists to remove: a request that could not
        mean anything used to be accepted and then dropped."""
        with pytest.raises(ValueError, match="cannot ride a ColumnDefaultConstraint"):
            ColumnConstraint(
                dummy_dialect,
                branch=ColumnDefaultConstraint(dummy_dialect, Literal(dummy_dialect, 1)),
                enforced=True,
            )
        with pytest.raises(ValueError, match="cannot ride a ColumnNotNullConstraint"):
            ColumnConstraint(
                dummy_dialect,
                branch=ColumnNotNullConstraint(dummy_dialect),
                deferrable=True,
            )

    def test_enforced_trait(self, dummy_dialect):
        dialect = _probed(supports_constraint_enforced=True)()
        clause = ColumnConstraint(
            dialect,
            branch=ColumnCheckConstraint(dialect, _check(dialect)),
            not_enforced=True,
        )
        assert clause.to_sql() == (' CHECK ("age" > 0) NOT ENFORCED', ())

    def test_enforcement_refused_without_support(self, dummy_dialect):
        dialect = _probed(supports_constraint_enforced=False)()
        clause = ColumnConstraint(
            dialect,
            branch=ColumnCheckConstraint(dialect, _check(dialect)),
            enforced=True,
        )
        with pytest.raises(UnsupportedFeatureError):
            clause.to_sql()

    def test_named_prefix_needs_the_capability(self, dummy_dialect):
        dialect = _probed(supports_constraint_naming=False)()
        clause = ColumnConstraint(
            dialect, branch=ColumnNotNullConstraint(dialect), name="nn"
        )
        with pytest.raises(UnsupportedFeatureError, match="CONSTRAINT"):
            clause.to_sql()

    def test_the_tag_field_is_gone(self, dummy_dialect):
        clause = ColumnConstraint(
            dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect)
        )
        with pytest.raises(AttributeError, match="ColumnNotNullConstraint"):
            clause.constraint_type

    def test_a_branch_is_required(self, dummy_dialect):
        with pytest.raises(TypeError, match="branch"):
            ColumnConstraint(dummy_dialect, branch=ColumnNotNullConstraint)


class TestTableConstraintBaseline:
    def test_primary_key_and_unique(self, dummy_dialect):
        assert TableConstraint(
            dummy_dialect, branch=TablePrimaryKeyConstraint(dummy_dialect, ["id"])
        ).to_sql() == ('PRIMARY KEY ("id")', ())
        assert TableConstraint(
            dummy_dialect, branch=TableUniqueConstraint(dummy_dialect, ["email"])
        ).to_sql() == ('UNIQUE ("email")', ())

    def test_foreign_key(self, dummy_dialect):

        assert TableConstraint(
            dummy_dialect,
            branch=TableForeignKeyConstraint(
                dummy_dialect, ["user_id"], (Table(dummy_dialect, "users"), ["id"])
            ),
        ).to_sql() == ('FOREIGN KEY ("user_id") REFERENCES "users"("id")', ())

    def test_check(self, dummy_dialect):
        assert TableConstraint(
            dummy_dialect, branch=TableCheckConstraint(dummy_dialect, _check(dummy_dialect))
        ).to_sql() == ('CHECK ("age" > 0)', ())

    def test_named_prefix_and_enforced(self, dummy_dialect):
        dialect = _probed(supports_constraint_enforced=True)()
        assert TableConstraint(
            dialect,
            branch=TableCheckConstraint(dialect, _check(dialect)),
            name="ck_users_age",
            not_enforced=True,
        ).to_sql() == ('CONSTRAINT "ck_users_age" CHECK ("age" > 0) NOT ENFORCED', ())

    def test_exclude_is_a_branch_that_refuses_by_name(self, dummy_dialect):
        """Enumerable, so modelled -- and refused where the constraint is
        spelled, since no dialect here can spell EXCLUDE."""

        clause = TableConstraint(
            dummy_dialect, branch=TableExcludeConstraint(dummy_dialect, ["ts"])
        )
        with pytest.raises(UnsupportedFeatureError, match="EXCLUDE"):
            clause.to_sql()

    def test_validation_is_a_field_the_node_keeps(self, dummy_dialect):
        """``NOT VALID`` is refused by the CREATE TABLE path, not here -- the
        constraint alone has no say in where it is being added."""
        clause = TableConstraint(
            dummy_dialect,
            branch=TableCheckConstraint(dummy_dialect, _check(dummy_dialect)),
            validation="NOTVALID",
        )
        assert clause.validation == "NOTVALID"
