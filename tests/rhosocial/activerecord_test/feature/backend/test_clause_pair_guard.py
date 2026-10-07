# tests/rhosocial/activerecord_test/feature/backend/test_clause_pair_guard.py
"""Guard: every two-spelling clause has one parameter per spelling.

The rule this file enforces (the round's rule 1/2/3/4):

* each spellable alternative has its own parameter;
* "unspecified" is the state where none of the group's parameters is set;
* setting more than one of them is API misuse and raises ``ValueError`` at
  construction time;
* no ``Optional[bool]`` tri-state and no sentinel value.

For every clause pair the four states must be pairwise distinguishable:

====================  =============================================
neither parameter     neither spelling rendered
parameter A           A's spelling rendered (and not B's)
parameter B           B's spelling rendered (and not A's)
both parameters       ``ValueError``
====================  =============================================

The guard renders through ``DummyDialect``, the reference switchboard that
declares every capability ``True``. A pair whose formatter ignores one of the
new parameters fails here because that state becomes indistinguishable from
"neither".

One pair is mandatory in its grammar rather than optional:
``AlterConstraint.enforced`` / ``not_enforced`` -- the action *is* the
enforcement keyword, so "neither" is refused as well. That case carries
``neither_error`` and is asserted accordingly.
"""

import re

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.objects import (
    Function,
    MaterializedView,
    Schema,
    Sequence,
    Table,
    View,
)
from rhosocial.activerecord.backend.expression.pivot import UnpivotExpression
from rhosocial.activerecord.backend.expression.query_sources import (
    CTEExpression,
    SetOperationExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AlterConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_function import (
    DropFunctionExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_schema import (
    DropSchemaExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_sequence import (
    AlterSequenceExpression,
    CreateSequenceExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    CreateTableAsExpression,
    DropTableExpression,
    IdentityClause,
    IndexDefinition,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    CreateMaterializedViewExpression,
    DropMaterializedViewExpression,
    DropViewExpression,
    RefreshMaterializedViewExpression,
)
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _dummy():
    return DummyDialect()


def _table(d, name="t"):
    return Table(d, name)


def _query(d):
    return QueryExpression(d, select=[Column(d, "id")], from_=_table(d))


def _fk(d, **kw):
    return TableConstraint(
        d,
        TableConstraintType.FOREIGN_KEY,
        name="fk",
        columns=["a"],
        foreign_key_table=_table(d, "t2"),
        foreign_key_columns=["b"],
        **kw,
    )


def _check(d, **kw):
    from rhosocial.activerecord.backend.expression.predicates import (
        ComparisonPredicate,
    )

    return TableConstraint(
        d,
        TableConstraintType.CHECK,
        name="ck",
        check_condition=ComparisonPredicate(d, "=", Column(d, "a"), Column(d, "b")),
        **kw,
    )


def _column_check(d, **kw):
    from rhosocial.activerecord.backend.expression.predicates import (
        ComparisonPredicate,
    )

    return ColumnConstraint(
        d,
        ColumnConstraintType.CHECK,
        name="ck",
        check_condition=ComparisonPredicate(d, "=", Column(d, "a"), Column(d, "b")),
        **kw,
    )


def _column_fk(d, **kw):
    return ColumnConstraint(
        d,
        ColumnConstraintType.FOREIGN_KEY,
        name="fk",
        foreign_key_reference=(_table(d, "t2"), ["b"]),
        **kw,
    )


#: Switchboard dialects for the probe gates: DummyDialect declares every
#: capability True, so flipping exactly one probe to False isolates the gate.
class _NoMaterializedCTE(DummyDialect):
    def supports_materialized_cte(self) -> bool:
        return False


class _NoTruncate(DummyDialect):
    def supports_truncate(self) -> bool:
        return False


class _NoWithDataClause(DummyDialect):
    def supports_with_data_clause(self) -> bool:
        return False


class _NoTransactionWait(DummyDialect):
    def supports_transaction_wait(self) -> bool:
        return False


class PairCase:
    """One two-spelling clause and how to render it in each state."""

    def __init__(
        self,
        case_id,
        builder,
        a,
        b,
        a_pattern,
        b_pattern,
        neither_error=None,
        a_value=True,
        b_value=True,
    ):
        self.case_id = case_id
        self.builder = builder
        self.a = a
        self.b = b
        self.a_pattern = re.compile(a_pattern)
        self.b_pattern = re.compile(b_pattern)
        self.neither_error = neither_error
        self.a_value = a_value
        self.b_value = b_value

    def render(self, dialect, **kwargs):
        sql, _params = self.builder(dialect, **kwargs).to_sql()
        return sql

    def matches_a(self, sql):
        return bool(self.a_pattern.search(sql))

    def matches_b(self, sql):
        return bool(self.b_pattern.search(sql))


#: Positive fragments use a negative lookbehind where the positive spelling is
#: a substring of the negative one ("CYCLE" inside "NO CYCLE", and friends).
PAIR_CASES = (
    PairCase(
        "CreateSequenceExpression.cycle",
        lambda d, **kw: CreateSequenceExpression(d, Sequence(d, "s"), **kw),
        "cycle",
        "no_cycle",
        r"(?<!NO )CYCLE\b",
        r"NO CYCLE\b",
    ),
    PairCase(
        "CreateSequenceExpression.order",
        lambda d, **kw: CreateSequenceExpression(d, Sequence(d, "s"), **kw),
        "order",
        "no_order",
        r"(?<!NO )ORDER\b",
        r"NO ORDER\b",
    ),
    PairCase(
        "CreateSequenceExpression.cache",
        lambda d, **kw: CreateSequenceExpression(d, Sequence(d, "s"), **kw),
        "cache",
        "no_cache",
        r"CACHE 10\b",
        r"NO CACHE\b",
        a_value=10,
    ),
    PairCase(
        "AlterSequenceExpression.cycle",
        lambda d, **kw: AlterSequenceExpression(d, Sequence(d, "s"), **kw),
        "cycle",
        "no_cycle",
        r"(?<!NO )CYCLE\b",
        r"NO CYCLE\b",
    ),
    PairCase(
        "AlterSequenceExpression.order",
        lambda d, **kw: AlterSequenceExpression(d, Sequence(d, "s"), **kw),
        "order",
        "no_order",
        r"(?<!NO )ORDER\b",
        r"NO ORDER\b",
    ),
    PairCase(
        "AlterSequenceExpression.cache",
        lambda d, **kw: AlterSequenceExpression(d, Sequence(d, "s"), **kw),
        "cache",
        "no_cache",
        r"CACHE 10\b",
        r"NO CACHE\b",
        a_value=10,
    ),
    PairCase(
        "IdentityClause.cycle",
        lambda d, **kw: IdentityClause(d, **kw),
        "cycle",
        "no_cycle",
        r"(?<!NO )CYCLE\b",
        r"NO CYCLE\b",
    ),
    PairCase(
        "IdentityClause.order",
        lambda d, **kw: IdentityClause(d, **kw),
        "order",
        "no_order",
        r"(?<!NO )ORDER\b",
        r"NO ORDER\b",
    ),
    PairCase(
        "IdentityClause.cache",
        lambda d, **kw: IdentityClause(d, **kw),
        "cache",
        "no_cache",
        r"CACHE 10\b",
        r"NO CACHE\b",
        a_value=10,
    ),
    PairCase(
        "DropSchemaExpression.cascade",
        lambda d, **kw: DropSchemaExpression(d, Schema(d, "s"), **kw),
        "cascade",
        "restrict",
        r"CASCADE\b",
        r"RESTRICT\b",
    ),
    PairCase(
        "DropViewExpression.cascade",
        lambda d, **kw: DropViewExpression(d, View(d, "v"), **kw),
        "cascade",
        "restrict",
        r"CASCADE\b",
        r"RESTRICT\b",
    ),
    PairCase(
        "DropMaterializedViewExpression.cascade",
        lambda d, **kw: DropMaterializedViewExpression(d, MaterializedView(d, "mv"), **kw),
        "cascade",
        "restrict",
        r"CASCADE\b",
        r"RESTRICT\b",
    ),
    PairCase(
        "DropFunctionExpression.cascade",
        lambda d, **kw: DropFunctionExpression(d, Function(d, "f"), **kw),
        "cascade",
        "restrict",
        r"CASCADE\b",
        r"RESTRICT\b",
    ),
    PairCase(
        "DropTableExpression.cascade",
        lambda d, **kw: DropTableExpression(d, _table(d), **kw),
        "cascade",
        "restrict",
        r"CASCADE\b",
        r"RESTRICT\b",
    ),
    PairCase(
        "TruncateExpression.cascade",
        lambda d, **kw: TruncateExpression(d, _table(d), **kw),
        "cascade",
        "restrict",
        r"CASCADE\b",
        r"RESTRICT\b",
    ),
    PairCase(
        "TruncateExpression.restart_identity",
        lambda d, **kw: TruncateExpression(d, _table(d), **kw),
        "restart_identity",
        "continue_identity",
        r"RESTART IDENTITY\b",
        r"CONTINUE IDENTITY\b",
    ),
    PairCase(
        "UnpivotExpression.include_nulls",
        lambda d, **kw: UnpivotExpression(
            d, value_column="v", pivot_column="k", columns=["a", "b"], **kw
        ),
        "include_nulls",
        "exclude_nulls",
        r"INCLUDE NULLS\b",
        r"EXCLUDE NULLS\b",
    ),
    PairCase(
        "AlterConstraint.enforced",
        lambda d, **kw: AlterConstraint(
            d, "c", constraint_type=TableConstraintType.CHECK, **kw
        ),
        "enforced",
        "not_enforced",
        r"(?<!NOT )ENFORCED\b",
        r"NOT ENFORCED\b",
        neither_error="AlterConstraint requires exactly one of",
    ),
    PairCase(
        "CreateMaterializedViewExpression.with_data",
        lambda d, **kw: CreateMaterializedViewExpression(
            d, MaterializedView(d, "mv"), _query(d), **kw
        ),
        "with_data",
        "no_data",
        r"WITH DATA\b",
        r"WITH NO DATA\b",
    ),
    PairCase(
        "RefreshMaterializedViewExpression.with_data",
        lambda d, **kw: RefreshMaterializedViewExpression(
            d, MaterializedView(d, "mv"), **kw
        ),
        "with_data",
        "no_data",
        r"WITH DATA\b",
        r"WITH NO DATA\b",
    ),
    PairCase(
        "CreateTableAsExpression.with_data",
        lambda d, **kw: CreateTableAsExpression(d, _table(d), _query(d), **kw),
        "with_data",
        "no_data",
        r"WITH DATA\b",
        r"WITH NO DATA\b",
    ),
    PairCase(
        "CTEExpression.materialized",
        lambda d, **kw: CTEExpression(d, "c", _query(d), **kw),
        "materialized",
        "not_materialized",
        r"(?<!NOT )MATERIALIZED\b",
        r"NOT MATERIALIZED\b",
    ),
    PairCase(
        "TableConstraint.deferrable",
        _fk,
        "deferrable",
        "not_deferrable",
        r"(?<!NOT )DEFERRABLE\b",
        r"NOT DEFERRABLE\b",
    ),
    PairCase(
        "TableConstraint.initially_deferred",
        _fk,
        "initially_deferred",
        "initially_immediate",
        r"INITIALLY DEFERRED\b",
        r"INITIALLY IMMEDIATE\b",
    ),
    PairCase(
        "TableConstraint.enforced",
        _check,
        "enforced",
        "not_enforced",
        r"(?<!NOT )ENFORCED\b",
        r"NOT ENFORCED\b",
    ),
    PairCase(
        "ColumnConstraint.enforced",
        _column_check,
        "enforced",
        "not_enforced",
        r"(?<!NOT )ENFORCED\b",
        r"NOT ENFORCED\b",
    ),
    # Same-clause carriers: the clause was inventoried once (on TableConstraint),
    # but ColumnConstraint/ReferencesClause carry the same two spellings, so the
    # split must reach them too or the same clause would be encoded two ways.
    PairCase(
        "ColumnConstraint.deferrable",
        _column_fk,
        "deferrable",
        "not_deferrable",
        r"(?<!NOT )DEFERRABLE\b",
        r"NOT DEFERRABLE\b",
    ),
    PairCase(
        "ColumnConstraint.initially_deferred",
        _column_fk,
        "initially_deferred",
        "initially_immediate",
        r"INITIALLY DEFERRED\b",
        r"INITIALLY IMMEDIATE\b",
    ),
    PairCase(
        "SetOperationExpression.all_",
        lambda d, **kw: SetOperationExpression(
            d,
            left=QueryExpression(d, select=[Column(d, "a")], from_=_table(d, "t1")),
            right=QueryExpression(d, select=[Column(d, "a")], from_=_table(d, "t2")),
            operation="UNION",
            **kw,
        ),
        "all_",
        "distinct",
        r"\bALL\b",
        r"\bDISTINCT\b",
    ),
    PairCase(
        "BeginTransactionExpression.deferrable",
        lambda d, **kw: BeginTransactionExpression(d, **kw),
        "deferrable",
        "not_deferrable",
        r"(?<!NOT )DEFERRABLE\b",
        r"NOT DEFERRABLE\b",
    ),
    # The same clause on SET TRANSACTION; the audit recorded the field there too.
    PairCase(
        "SetTransactionExpression.deferrable",
        lambda d, **kw: SetTransactionExpression(d, **kw),
        "deferrable",
        "not_deferrable",
        r"(?<!NOT )DEFERRABLE\b",
        r"NOT DEFERRABLE\b",
    ),
    # Firebird's two-spelling transaction lock-wait clause. The parameter was
    # missing from the expression layer entirely, so the dead dialect helper
    # (_format_begin_sql(wait=...)) could never be reached.
    PairCase(
        "BeginTransactionExpression.wait",
        lambda d, **kw: BeginTransactionExpression(d, **kw),
        "wait",
        "no_wait",
        r"(?<!NO )WAIT\b",
        r"NO WAIT\b",
    ),
    PairCase(
        "SetTransactionExpression.wait",
        lambda d, **kw: SetTransactionExpression(d, **kw),
        "wait",
        "no_wait",
        r"(?<!NO )WAIT\b",
        r"NO WAIT\b",
    ),
)

PAIR_IDS = [case.case_id for case in PAIR_CASES]


class TestFourStatesArePairwiseDistinguishable:
    """The four states of every pair are pairwise distinguishable."""

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_neither_set_renders_neither_spelling(self, case):
        if case.neither_error is not None:
            with pytest.raises(ValueError, match=case.neither_error):
                case.render(_dummy())
            return
        sql = case.render(_dummy())
        assert not case.matches_a(sql), (
            f"{case.case_id}: with neither parameter set the SQL still spells "
            f"{case.a!r}: {sql!r}"
        )
        assert not case.matches_b(sql), (
            f"{case.case_id}: with neither parameter set the SQL still spells "
            f"{case.b!r}: {sql!r}"
        )

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_a_set_renders_a_only(self, case):
        sql = case.render(_dummy(), **{case.a: case.a_value})
        assert case.matches_a(sql), f"{case.case_id}: {case.a!r} was not rendered: {sql!r}"
        assert not case.matches_b(sql), (
            f"{case.case_id}: setting {case.a!r} also rendered {case.b!r}: {sql!r}"
        )

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_b_set_renders_b_only(self, case):
        sql = case.render(_dummy(), **{case.b: case.b_value})
        assert case.matches_b(sql), f"{case.case_id}: {case.b!r} was not rendered: {sql!r}"
        assert not case.matches_a(sql), (
            f"{case.case_id}: setting {case.b!r} also rendered {case.a!r}: {sql!r}"
        )

    @pytest.mark.parametrize("case", PAIR_CASES, ids=PAIR_IDS)
    def test_both_set_is_refused(self, case):
        with pytest.raises(
            ValueError, match=f"{case.a} and {case.b} are mutually exclusive options"
        ):
            case.render(
                _dummy(), **{case.a: case.a_value, case.b: case.b_value}
            )


class TestSentinelIsGone:
    """``cache=0`` is no longer a spelling of NO CACHE."""

    @pytest.mark.parametrize(
        "factory",
        [
            lambda d, **kw: CreateSequenceExpression(d, Sequence(d, "s"), **kw),
            lambda d, **kw: AlterSequenceExpression(d, Sequence(d, "s"), **kw),
            lambda d, **kw: IdentityClause(d, **kw),
        ],
        ids=["CreateSequenceExpression", "AlterSequenceExpression", "IdentityClause"],
    )
    def test_cache_zero_is_refused(self, factory):
        with pytest.raises(ValueError, match="cache must be a positive integer"):
            factory(_dummy(), cache=0)


class TestShapeERedundantTriStateIsGone:
    """``IndexDefinition.if_exists`` / ``if_not_exists`` are plain bools."""

    def test_defaults_are_false_bools(self):
        expr = IndexDefinition(_dummy(), "i", ["c"])
        assert expr.if_exists is False
        assert expr.if_not_exists is False

    def test_true_is_preserved(self):
        expr = IndexDefinition(_dummy(), "i", ["c"], if_exists=True, if_not_exists=True)
        assert expr.if_exists is True
        assert expr.if_not_exists is True

    def test_none_is_coerced_to_false(self):
        """The model-layer marker passes ``None`` for "not declared"."""
        expr = IndexDefinition(_dummy(), "i", ["c"], if_exists=None, if_not_exists=None)
        assert expr.if_exists is False
        assert expr.if_not_exists is False


class TestSilentIgnoresAreRefusedOrMadeLegal:
    """The same family: requests that used to be dropped are no longer dropped."""

    def test_initially_deferred_without_deferrable_is_rendered(self):
        """INITIALLY ... is an independent constraint attribute; render it."""
        sql = _fk(_dummy(), initially_deferred=True).to_sql()[0]
        assert "INITIALLY DEFERRED" in sql, sql

    def test_initially_immediate_without_deferrable_is_rendered(self):
        sql = _fk(_dummy(), initially_immediate=True).to_sql()[0]
        assert "INITIALLY IMMEDIATE" in sql, sql

    def test_deferrable_without_serializable_is_rendered(self):
        """Dummy renders [NOT] DEFERRABLE as a transaction mode on its own."""
        sql = BeginTransactionExpression(_dummy(), deferrable=True).to_sql()[0]
        assert "DEFERRABLE" in sql, sql

    def test_not_deferrable_without_serializable_is_rendered(self):
        sql = BeginTransactionExpression(_dummy(), not_deferrable=True).to_sql()[0]
        assert "NOT DEFERRABLE" in sql, sql

    def test_set_transaction_renders_not_deferrable(self):
        sql = SetTransactionExpression(_dummy(), not_deferrable=True).to_sql()[0]
        assert "NOT DEFERRABLE" in sql, sql

    def test_sqlite_refuses_deferrable_it_declines(self):
        """SQLite answers supports_deferrable_transaction() False: refuse."""
        sqlite = SQLiteDialect()
        assert sqlite.supports_deferrable_transaction() is False
        with pytest.raises(UnsupportedFeatureError):
            BeginTransactionExpression(sqlite, deferrable=True).to_sql()

    def test_sqlite_refuses_not_deferrable_it_declines(self):
        sqlite = SQLiteDialect()
        with pytest.raises(UnsupportedFeatureError):
            BeginTransactionExpression(sqlite, not_deferrable=True).to_sql()


class TestDeclaredProbeGatesTheClause:
    """A clause the dialect's probe declines is refused by name, never dropped.

    Three clauses had no gate at all before this round:

    * ``MATERIALIZED`` / ``NOT MATERIALIZED`` on a CTE must consult
      ``supports_materialized_cte()``;
    * ``TRUNCATE`` itself must consult ``supports_truncate()``;
    * ``WITH [NO] DATA`` (CTAS, CREATE/REFRESH MATERIALIZED VIEW) must consult
      the clause probe ``supports_with_data_clause()``.

    ``DummyDialect`` declares every capability ``True``, so a subclass that
    flips one probe to ``False`` is the switchboard for the refusal path.
    """

    def test_materialized_cte_is_refused_without_the_probe(self):
        d = _NoMaterializedCTE()
        assert d.supports_materialized_cte() is False
        with pytest.raises(UnsupportedFeatureError, match="MATERIALIZED CTE"):
            CTEExpression(d, "c", _query(d), materialized=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match="NOT MATERIALIZED CTE"):
            CTEExpression(d, "c", _query(d), not_materialized=True).to_sql()
        # Neither spelling requested: the probe is not consulted, nothing refused.
        sql, _params = CTEExpression(d, "c", _query(d)).to_sql()
        assert "MATERIALIZED" not in sql

    def test_truncate_is_refused_without_the_probe(self):
        d = _NoTruncate()
        assert d.supports_truncate() is False
        with pytest.raises(UnsupportedFeatureError, match="TRUNCATE"):
            TruncateExpression(d, _table(d)).to_sql()

    def test_with_data_is_refused_without_the_probe(self):
        d = _NoWithDataClause()
        assert d.supports_with_data_clause() is False
        for builder, kwargs, feature in (
            (
                lambda dd, **kw: CreateTableAsExpression(dd, _table(dd), _query(dd), **kw),
                {"with_data": True},
                "WITH DATA",
            ),
            (
                lambda dd, **kw: CreateTableAsExpression(dd, _table(dd), _query(dd), **kw),
                {"no_data": True},
                "WITH NO DATA",
            ),
            (
                lambda dd, **kw: CreateMaterializedViewExpression(
                    dd, MaterializedView(dd, "mv"), _query(dd), **kw
                ),
                {"with_data": True},
                "WITH DATA",
            ),
            (
                lambda dd, **kw: CreateMaterializedViewExpression(
                    dd, MaterializedView(dd, "mv"), _query(dd), **kw
                ),
                {"no_data": True},
                "WITH NO DATA",
            ),
            (
                lambda dd, **kw: RefreshMaterializedViewExpression(
                    dd, MaterializedView(dd, "mv"), **kw
                ),
                {"with_data": True},
                "WITH DATA",
            ),
            (
                lambda dd, **kw: RefreshMaterializedViewExpression(
                    dd, MaterializedView(dd, "mv"), **kw
                ),
                {"no_data": True},
                "WITH NO DATA",
            ),
        ):
            with pytest.raises(UnsupportedFeatureError, match=feature):
                builder(d, **kwargs).to_sql()

    def test_transaction_wait_is_refused_without_the_probe(self):
        d = _NoTransactionWait()
        assert d.supports_transaction_wait() is False
        with pytest.raises(UnsupportedFeatureError, match="WAIT"):
            BeginTransactionExpression(d, wait=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match="NO WAIT"):
            BeginTransactionExpression(d, no_wait=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match="WAIT"):
            SetTransactionExpression(d, wait=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match="NO WAIT"):
            SetTransactionExpression(d, no_wait=True).to_sql()

    def test_sqlite_refuses_wait_it_declines(self):
        """SQLite answers supports_transaction_wait() False: refuse by name."""
        sqlite = SQLiteDialect()
        assert sqlite.supports_transaction_wait() is False
        with pytest.raises(UnsupportedFeatureError, match="WAIT"):
            BeginTransactionExpression(sqlite, wait=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match="NO WAIT"):
            BeginTransactionExpression(sqlite, no_wait=True).to_sql()
        # SQLite has no SET TRANSACTION statement at all, so the clause is
        # subsumed by that refusal (NotImplementedError from the core mixin).
        with pytest.raises((UnsupportedFeatureError, NotImplementedError)):
            SetTransactionExpression(sqlite, no_wait=True).to_sql()


class TestGuardIsNotVacuous:
    """Guards so the checks above cannot pass by accident."""

    def test_every_case_has_two_distinct_parameters(self):
        for case in PAIR_CASES:
            assert case.a != case.b, case.case_id

    def test_every_pair_is_covered(self):
        """The audited core pairs are all in this table (plus same-family carriers)."""
        expected = {
            "CreateSequenceExpression.cycle",
            "CreateSequenceExpression.order",
            "CreateSequenceExpression.cache",
            "AlterSequenceExpression.cycle",
            "AlterSequenceExpression.order",
            "AlterSequenceExpression.cache",
            "IdentityClause.cycle",
            "IdentityClause.order",
            "IdentityClause.cache",
            "DropSchemaExpression.cascade",
            "DropViewExpression.cascade",
            "DropMaterializedViewExpression.cascade",
            "DropFunctionExpression.cascade",
            "DropTableExpression.cascade",
            "TruncateExpression.cascade",
            "TruncateExpression.restart_identity",
            "UnpivotExpression.include_nulls",
            "AlterConstraint.enforced",
            "CreateMaterializedViewExpression.with_data",
            "RefreshMaterializedViewExpression.with_data",
            "CreateTableAsExpression.with_data",
            "CTEExpression.materialized",
            "TableConstraint.deferrable",
            "TableConstraint.initially_deferred",
            "TableConstraint.enforced",
            "ColumnConstraint.enforced",
            "SetOperationExpression.all_",
            "BeginTransactionExpression.deferrable",
            "BeginTransactionExpression.wait",
            "SetTransactionExpression.wait",
        }
        covered = {case.case_id for case in PAIR_CASES}
        missing = expected - covered
        assert not missing, f"pairs in scope but not guarded: {sorted(missing)}"
