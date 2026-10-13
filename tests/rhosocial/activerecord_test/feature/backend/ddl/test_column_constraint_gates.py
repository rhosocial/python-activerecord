# tests/rhosocial/activerecord_test/feature/backend/ddl/test_column_constraint_gates.py
"""Capability gates on column-constraint rendering.

A column constraint clause is rendered only when the dialect declares it can
express it; otherwise the spelling is refused by name instead of being dropped.
These tests pin the gates that were declared but never consulted, plus the two
paths that render the same constraint -- ``ColumnDefinition`` and
``ColumnConstraint.to_sql()`` -- which must agree.
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
    TableUniqueConstraint,
)
from rhosocial.activerecord.base.ddl import CharacterSetAttribute, CollationAttribute
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnDefinition,
    ReferentialAction,
    TableConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError



def probed(**answers):
    """Return a dialect class whose capability probes answer as ``answers``."""
    namespace = {
        name: (lambda self, answer=answer: answer)
        for name, answer in answers.items()
    }
    return type("ProbedDialect", (SQLiteDialect,), namespace)


def check_constraint(dialect):
    return ColumnConstraint(dialect, branch=ColumnCheckConstraint(dialect, Column(dialect, "age") > Literal(dialect, 0)))


def fk_constraint(dialect, **kwargs):
    # The referential actions belong to the branch; the deferral traits are
    # the production's, which is where they went when the two levels split.
    branch_traits = ("on_delete", "on_update", "match_type")
    clause_traits = ("deferrable", "initially_deferred")
    branch = ColumnForeignKeyConstraint(
        dialect,
        (Table(dialect, "parent"), ["id"]),
        **{k: v for k, v in kwargs.items() if k in branch_traits},
    )
    return ColumnConstraint(
        dialect,
        branch=branch,
        **{k: v for k, v in kwargs.items() if k in clause_traits},
    )


class TestSimpleConstraintGates:
    """PRIMARY KEY / NOT NULL / NULL / UNIQUE consult their own probes."""

    def test_supported_spellings_render(self):
        dialect = SQLiteDialect()
        for branch_cls, expected in (
            (ColumnPrimaryKeyConstraint, " PRIMARY KEY"),
            (ColumnNotNullConstraint, " NOT NULL"),
            (ColumnNullableConstraint, " NULL"),
            (ColumnUniqueConstraint, " UNIQUE"),
        ):
            constraint = ColumnConstraint(dialect, branch=branch_cls(dialect))
            assert constraint.to_sql() == (expected, ())

    @pytest.mark.parametrize(
        "probe, branch_cls, spelling",
        (
            ("supports_primary_key_constraint", ColumnPrimaryKeyConstraint, "PRIMARY KEY"),
            ("supports_not_null_constraint", ColumnNotNullConstraint, "NOT NULL"),
            ("supports_unique_constraint", ColumnUniqueConstraint, "UNIQUE"),
        ),
    )
    def test_unsupported_spelling_is_refused_by_name(self, probe, branch_cls, spelling):
        dialect = probed(**{probe: False})()
        constraint = ColumnConstraint(dialect, branch=branch_cls(dialect))

        with pytest.raises(UnsupportedFeatureError) as excinfo:
            constraint.to_sql()

        assert spelling in str(excinfo.value)

    def test_null_has_no_gate_to_close(self):
        """NULL stays renderable: an explicitly nullable column is universal."""
        dialect = probed(
            supports_primary_key_constraint=False,
            supports_not_null_constraint=False,
            supports_unique_constraint=False,
        )()
        constraint = ColumnConstraint(dialect, branch=ColumnNullableConstraint(dialect))

        assert constraint.to_sql() == (" NULL", ())


class TestForeignKeyGate:
    """A column-level REFERENCES clause consults the foreign key probe."""

    def test_unsupported_reference_is_refused_by_name(self):
        dialect = probed(supports_foreign_key_constraint=False)()

        with pytest.raises(UnsupportedFeatureError, match="REFERENCES"):
            fk_constraint(dialect).to_sql()

    def test_reference_renders_where_supported(self):
        dialect = SQLiteDialect()

        assert fk_constraint(dialect).to_sql() == (
            ' REFERENCES "parent"("id")',
            (),
        )


class TestCheckConstraintGate:
    """CHECK consults its probe and never carries bind parameters into DDL."""

    def test_predicate_is_inlined(self):
        dialect = SQLiteDialect()

        sql, params = check_constraint(dialect).to_sql()

        assert params == ()
        # The dialect normalises ``a > b`` to ``b < a``; what this test pins is
        # that the literal is spelled out rather than bound.
        assert sql == ' CHECK (0 < "age")'

    def test_unsupported_check_is_refused_by_name(self):
        dialect = probed(supports_check_constraint=False)()

        with pytest.raises(UnsupportedFeatureError, match="CHECK"):
            check_constraint(dialect).to_sql()

    def test_missing_condition_is_a_declaration_error(self):
        """Refused at construction: the branch that states the condition is how
        a CHECK is expressed, so a CHECK without one cannot be written."""

        with pytest.raises(ValueError, match="needs a condition"):
            ColumnCheckConstraint(SQLiteDialect(), None)


class TestDeferralGates:
    """DEFERRABLE and INITIALLY are gated, not rendered unconditionally."""

    def test_deferrable_is_refused_where_unsupported(self):
        dialect = probed(supports_deferrable_constraint=False)()

        with pytest.raises(UnsupportedFeatureError, match="DEFERRABLE"):
            fk_constraint(dialect, deferrable=True).to_sql()

    def test_initially_deferred_is_refused_where_unsupported(self):
        dialect = probed(supports_deferrable_constraint=False)()

        with pytest.raises(UnsupportedFeatureError, match="DEFERRABLE"):
            fk_constraint(dialect, initially_deferred=True).to_sql()

    def test_deferrable_renders_where_supported(self):
        dialect = probed(supports_deferrable_constraint=True)()

        assert fk_constraint(
            dialect, deferrable=True, initially_deferred=True
        ).to_sql() == (
            ' REFERENCES "parent"("id") DEFERRABLE INITIALLY DEFERRED',
            (),
        )


class TestColumnAttributeGates:
    """COLLATE and CHARACTER SET attributes consult their probes."""

    def test_collation_is_refused_where_unsupported(self):
        dialect = probed(supports_column_collation=False)()

        with pytest.raises(UnsupportedFeatureError, match="COLLATE"):
            dialect.format_column_attribute(CollationAttribute(name="NOCASE"))

    def test_collation_renders_where_supported(self):
        dialect = SQLiteDialect()

        assert dialect.format_column_attribute(
            CollationAttribute(name="NOCASE")
        ) == (" COLLATE NOCASE", ())

    def test_character_set_is_refused_where_unsupported(self):
        dialect = SQLiteDialect()  # declares character sets unsupported

        with pytest.raises(UnsupportedFeatureError, match="CHARACTER SET"):
            dialect.format_column_attribute(CharacterSetAttribute(name="utf8"))

    def test_character_set_renders_where_supported(self):
        dialect = probed(supports_column_character_set=True)()

        assert dialect.format_column_attribute(
            CharacterSetAttribute(name="utf8")
        ) == (" CHARACTER SET utf8", ())


class TestBothRenderPathsAgree:
    """``ColumnDefinition`` and ``ColumnConstraint.to_sql()`` must agree.

    A constraint rendered one way inside ``CREATE TABLE`` and another way on its
    own is how a column silently lost a ``CHECK`` or a foreign key in the first
    place, so the two paths are compared directly.
    """

    @pytest.mark.parametrize(
        "build",
        (
            lambda d: ColumnConstraint(d, branch=ColumnPrimaryKeyConstraint(d)),
            lambda d: ColumnConstraint(d, branch=ColumnNotNullConstraint(d)),
            lambda d: ColumnConstraint(d, branch=ColumnNullableConstraint(d)),
            lambda d: ColumnConstraint(d, branch=ColumnUniqueConstraint(d)),
            lambda d: ColumnConstraint(d, branch=ColumnDefaultConstraint(d, 0)),
            check_constraint,
            lambda d: fk_constraint(
                d,
                on_delete=ReferentialAction.CASCADE,
                on_update=ReferentialAction.SET_NULL,
            ),
        ),
    )
    def test_column_definition_ends_with_the_constraint_sql(self, build):
        dialect = SQLiteDialect()
        constraint = build(dialect)

        definition_sql, _ = ColumnDefinition(
            dialect, "c", IntegerType(dialect), constraints=[constraint]
        ).to_sql()
        constraint_sql, _ = constraint.to_sql()

        assert definition_sql == f'"c" INTEGER{constraint_sql}'

    def test_check_inside_a_definition_carries_no_bind_parameters(self):
        dialect = SQLiteDialect()
        constraint = check_constraint(dialect)

        sql, params = ColumnDefinition(
            dialect, "age", IntegerType(dialect), constraints=[constraint]
        ).to_sql()

        assert params == ()
        # Compared against the constraint's own SQL rather than a literal, so
        # the assertion is about the two paths agreeing, not about how a
        # comparison happens to be spelled.
        assert sql == f'"age" INTEGER{constraint.to_sql()[0]}'


class TestConstraintNamingGates:
    """The ``CONSTRAINT <name>`` prefix is gated, not silently dropped."""

    def test_name_renders_on_the_column_path(self):
        dialect = SQLiteDialect()

        sql, _ = ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect), name="uq_e").to_sql()

        assert sql == ' CONSTRAINT "uq_e" UNIQUE'

    def test_name_is_refused_where_unsupported(self):
        dialect = probed(supports_constraint_naming=False)()

        with pytest.raises(UnsupportedFeatureError, match="CONSTRAINT name"):
            ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect), name="uq_e").to_sql()

    def test_table_path_gates_the_name_too(self):
        dialect = probed(supports_constraint_naming=False)()
        constraint = TableConstraint(dialect, branch=TableUniqueConstraint(dialect, ["e"]), name="uq_e")

        with pytest.raises(UnsupportedFeatureError, match="CONSTRAINT name"):
            constraint.to_sql()

    def test_naming_defaults_true_on_the_shared_mixin(self):
        from rhosocial.activerecord.backend.dialect.mixins.ddl_table import (
            ConstraintMixin,
        )

        class Bare(ConstraintMixin):
            pass

        assert Bare().supports_constraint_naming() is True


class TestEnforcementGates:
    """``[NOT] ENFORCED`` renders on the ENFORCABLE kinds and refuses the rest.

    The SQL:2016 kinds are PRIMARY KEY, UNIQUE, FOREIGN KEY and CHECK; a
    dialect narrows the set in its own formatter and may not widen it.
    """

    def test_enforced_renders_on_unique(self):
        dialect = probed(supports_constraint_enforced=True)()

        sql, _ = ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect), enforced=True).to_sql()

        assert sql == " UNIQUE ENFORCED"

    def test_not_enforced_renders_on_primary_key(self):
        dialect = probed(supports_constraint_enforced=True)()

        sql, _ = ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect), not_enforced=True).to_sql()

        assert sql == " PRIMARY KEY NOT ENFORCED"

    def test_enforced_is_refused_where_unsupported(self):
        dialect = probed(supports_constraint_enforced=False)()

        with pytest.raises(UnsupportedFeatureError, match="ENFORCED"):
            ColumnConstraint(dialect, branch=ColumnCheckConstraint(dialect, Column(dialect, "age") > Literal(dialect, 0)), enforced=True).to_sql()

    def test_not_null_cannot_carry_the_trait(self):
        dialect = probed(supports_constraint_enforced=True)()

        with pytest.raises(ValueError, match="cannot ride a ColumnNotNullConstraint"):
            ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect), enforced=True)

    def test_default_cannot_carry_the_trait(self):
        dialect = probed(supports_constraint_enforced=True)()

        with pytest.raises(ValueError, match="cannot ride a ColumnDefaultConstraint"):
            ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 0), enforced=True)

    def test_both_spellings_at_once_are_refused_by_the_formatter(self):
        """The constructor guard does not cover attribute injection.

        A pair injected after construction bypasses ``__init__``; the
        formatter re-checks the exclusion as the last line of defence.
        """
        dialect = probed(supports_constraint_enforced=True)()
        constraint = ColumnConstraint(dialect, branch=ColumnCheckConstraint(dialect, Column(dialect, "age") > Literal(dialect, 0)), enforced=True)
        constraint.not_enforced = True

        with pytest.raises(ValueError, match="mutually exclusive"):
            constraint.to_sql()
