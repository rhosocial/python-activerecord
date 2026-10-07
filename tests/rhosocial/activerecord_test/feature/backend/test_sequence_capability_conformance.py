# tests/rhosocial/activerecord_test/feature/backend/test_sequence_capability_conformance.py
"""A dialect's sequence declaration and its sequence renderer must agree.

``SequenceMixin`` carries three real formatters *and* the probes that decide
whether the capability exists at all. A dialect that answers
``supports_sequence()`` with ``False`` -- or does not answer it -- must not also
carry the mixin, because the mixin's formatters would then be reachable through
the dispatch and could render a ``CREATE SEQUENCE`` the server rejects. That is
exactly what MySQL, ClickHouse and Snowflake did before the mixin was left out
of their base lists.

The other direction: a dialect that answers ``True`` must have a real
implementation behind each name the sequence expressions dispatch to. A
``runtime_checkable`` protocol is satisfied by its own ``...`` bodies, so a
protocol sitting ahead of the mixin in the base list would answer ``getattr``
with a function that returns ``None`` -- and the dispatch would take that
``None`` as SQL (``test_to_sql_dispatch_contract.py`` covers that failure
mode). "Resolves'' therefore has to mean "resolves to something that is not the
protocol's own body''.

Both directions are asserted per dialect rather than once for the tree, because
the defect was a dialect disagreeing with the mixin it inherited, and a
tree-wide assertion would not have seen it.
"""

import pytest

from rhosocial.activerecord.backend.dialect.mixins.ddl_sequence import SequenceMixin
from rhosocial.activerecord.backend.dialect.protocols import (
    AlterSequenceSupport,
    CreateSequenceSupport,
    DropSequenceSupport,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.objects import Sequence
from rhosocial.activerecord.backend.expression.statements import (
    AlterSequenceExpression,
    CreateSequenceExpression,
    DropSequenceExpression,
)


#: Every dialect core ships. Each is checked against its own declaration.
CORE_DIALECTS = (DummyDialect, SQLiteDialect)

#: Each sequence formatter name -> the protocol that declares the same name.
#: The duplicated name is the hazard: a protocol body and a formatter look
#: alike to ``getattr``.
SEQUENCE_FORMATTERS = {
    "format_create_sequence_statement": CreateSequenceSupport,
    "format_drop_sequence_statement": DropSequenceSupport,
    "format_alter_sequence_statement": AlterSequenceSupport,
}

#: The three expression classes, so a rename of ``format_method`` fails here.
SEQUENCE_EXPRESSIONS = (
    CreateSequenceExpression,
    DropSequenceExpression,
    AlterSequenceExpression,
)


def _declares_sequences(dialect_cls: type) -> bool:
    """Whether the dialect's master switch says it has a sequence object.

    A dialect that does not answer ``supports_sequence`` at all is treated the
    same as one that answers ``False``: neither has declared the capability,
    and neither may therefore carry the mixin that renders it.
    """
    probe = getattr(dialect_cls, "supports_sequence", None)
    return probe is not None and probe(dialect_cls()) is True


class TestSequenceCapabilityConformance:
    """Each core dialect's sequence declaration matches what it can render."""

    @pytest.mark.parametrize("dialect_cls", CORE_DIALECTS, ids=lambda c: c.__name__)
    def test_declaration_matches_implementation(self, dialect_cls):
        if _declares_sequences(dialect_cls):
            missing = []
            protocol_bodies = []
            for name, protocol in SEQUENCE_FORMATTERS.items():
                method = getattr(dialect_cls, name, None)
                if method is None:
                    missing.append(name)
                elif method is getattr(protocol, name):
                    protocol_bodies.append(name)
            assert not missing, (
                f"{dialect_cls.__name__} answers supports_sequence() with True, "
                f"but the dispatch has no formatter for {missing}. A declared "
                f"capability needs a real implementation."
            )
            assert not protocol_bodies, (
                f"{dialect_cls.__name__} answers supports_sequence() with True, "
                f"but these names resolve to the protocol's own '...' body: "
                f"{protocol_bodies}. A runtime_checkable protocol satisfies "
                f"getattr, and the dispatch would take its None as SQL."
            )
            return

        # The dialect declares no sequence object (False, or no answer at all).
        assert SequenceMixin not in dialect_cls.__mro__, (
            f"{dialect_cls.__name__} does not declare sequence support, yet "
            f"SequenceMixin is on its MRO, so its three formatters are reachable "
            f"through the dispatch and would render CREATE/DROP/ALTER SEQUENCE "
            f"the server rejects. Leave the mixin out of the base list, as "
            f"MySQL, ClickHouse and Snowflake do."
        )


class TestSequenceConformanceIsNotVacuous:
    """Guards so the check above cannot be true by accident."""

    def test_formatter_names_match_the_expressions(self):
        """The map is keyed by the names the expressions actually dispatch to.

        A ``format_method`` rename that missed this map would leave the check
        asserting against names no expression uses.
        """
        actual = {expr.format_method.fget(None) for expr in SEQUENCE_EXPRESSIONS}
        assert actual == set(SEQUENCE_FORMATTERS), (
            "the sequence formatter names changed. "
            f"expressions dispatch to {sorted(actual)}, the check covers "
            f"{sorted(SEQUENCE_FORMATTERS)}"
        )

    def test_at_least_one_dialect_declares_sequences(self):
        """Both branches must have a subject, or half the check never runs."""
        declaring = [c.__name__ for c in CORE_DIALECTS if _declares_sequences(c)]
        declining = [c.__name__ for c in CORE_DIALECTS if not _declares_sequences(c)]
        assert declaring, "no core dialect declares sequence support"
        assert declining, "no core dialect declines sequence support"


class AlterStartRefusingDialect(DummyDialect):
    """``DummyDialect`` with the ALTER-side START probe withdrawn.

    Core's two dialects do not include a subject for the ALTER-side split:
    ``DummyDialect`` answers both START probes ``True``, and ``SQLiteDialect``
    has no sequence object at all. A dialect that declares sequences but whose
    server refuses ``ALTER ... START`` is the shape four of the six real
    backends have (Oracle, SQL Server, Firebird and Snowflake), so the split is
    modelled here rather than left unexercised. The override returns ``False``
    -- the mixin's own default -- while everything else is Dummy's.
    """

    def supports_alter_sequence_start(self) -> bool:
        return False


#: Subjects for the declaration/renderer agreement check on the ALTER side.
#: The core dialects alone are not enough: ``DummyDialect`` declares the clause
#: ``True`` and ``SQLiteDialect`` has no sequence object, so a dialect that
#: answered ``False`` yet still rendered the clause could not be caught -- the
#: ``False`` branch would only ever be exercised by a dialect with no ALTER
#: formatter at all. ``AlterStartRefusingDialect`` declares sequences but
#: withdraws the ALTER-side START probe, the shape four of the six real
#: backends have, so the gate has a subject it can be caught ignoring.
SPLIT_SUBJECTS = CORE_DIALECTS + (AlterStartRefusingDialect,)


def _answers_alter_sequence_start(dialect_cls: type):
    """The dialect's ALTER-side START answer, or ``None`` if it does not answer."""
    probe = getattr(dialect_cls, "supports_alter_sequence_start", None)
    return None if probe is None else probe(dialect_cls())


def _render_alter_start(dialect_cls: type):
    """Render ``ALTER SEQUENCE ... START WITH 5`` and classify the outcome.

    Returns ``(rendered, sql)``. ``rendered`` is ``False`` when the dialect
    refused the clause -- either the formatter raised ``UnsupportedFeatureError``
    because the probe is ``False``, or the dialect has no ALTER formatter at all
    (SQLite). Any other exception propagates, so a new failure mode cannot hide
    behind the classification.
    """
    dialect = dialect_cls()
    expr = AlterSequenceExpression(dialect, Sequence(dialect, "s"), start=5)
    try:
        return True, expr.to_sql()[0]
    except UnsupportedFeatureError:
        return False, None


class TestAlterSequenceStartSplit:
    """START on ALTER is gated by its own probe, not the CREATE one.

    ``supports_sequence_start`` answers for ``CREATE SEQUENCE ... START WITH``.
    Reusing it for ALTER let Firebird -- which declares ``False`` for the
    ALTER side but has no ALTER formatter of its own -- render
    ``ALTER SEQUENCE ... START WITH``, which its server rejects with ``Token
    unknown - START``. The two clauses are separate, so the gate must be the
    ALTER probe, and a ``False`` answer must fail closed.
    """

    def test_false_probe_refuses_alter_start(self):
        """A dialect whose ALTER probe is False must not render START."""
        dialect = AlterStartRefusingDialect()
        expr = AlterSequenceExpression(dialect, Sequence(dialect, "s"), start=5)
        with pytest.raises(UnsupportedFeatureError, match="ALTER SEQUENCE START"):
            expr.to_sql()

    def test_false_probe_leaves_create_start_alone(self):
        """The split is real: the same dialect still renders CREATE ... START."""
        dialect = AlterStartRefusingDialect()
        sql, _ = CreateSequenceExpression(
            dialect, Sequence(dialect, "s"), start=5
        ).to_sql()
        assert "START WITH 5" in sql

    def test_true_probe_renders_alter_start(self):
        """The two dialects that accept ALTER ... START declare True and render."""
        dialect = DummyDialect()
        sql, _ = AlterSequenceExpression(
            dialect, Sequence(dialect, "s"), start=5
        ).to_sql()
        assert "START WITH 5" in sql

    def test_restart_is_not_gated_by_the_start_probe(self):
        """RESTART is ALTER-only and independent of the START probe."""
        dialect = AlterStartRefusingDialect()
        sql, _ = AlterSequenceExpression(
            dialect, Sequence(dialect, "s"), restart=5
        ).to_sql()
        assert "RESTART WITH 5" in sql

    def test_mixin_default_is_false(self):
        """The shared default fails closed, so a new dialect must opt in."""
        class _Bare(SequenceMixin):
            pass

        assert _Bare().supports_alter_sequence_start() is False

    @pytest.mark.parametrize("dialect_cls", SPLIT_SUBJECTS, ids=lambda c: c.__name__)
    def test_core_dialects_render_start_only_when_declared(self, dialect_cls):
        """Declaration and renderer agree on the ALTER side, per dialect."""
        declared = _answers_alter_sequence_start(dialect_cls)
        rendered, sql = _render_alter_start(dialect_cls)
        if declared is True:
            assert rendered and "START WITH 5" in sql, (
                f"{dialect_cls.__name__} answers supports_alter_sequence_start() "
                f"with True but did not render ALTER ... START WITH 5"
            )
        else:
            assert not rendered, (
                f"{dialect_cls.__name__} answers supports_alter_sequence_start() "
                f"with {declared!r} yet rendered {sql!r} with START; a non-True "
                f"answer must fail closed"
            )


def _withdrawing_dialect(probe_name: str) -> type:
    """A ``DummyDialect`` that answers one probe ``False``, everything else Dummy's.

    The shape being modelled: a dialect that supports sequences but whose
    server refuses one specific option.
    """
    return type(
        f"DummyWithout_{probe_name}",
        (DummyDialect,),
        {probe_name: lambda self: False},
    )


#: One sequence option spelling -> the probe that gates it, the node that
#: carries it, the constructor kwargs that request it, the SQL fragment it
#: renders, and the feature name the refusal must carry. Both CREATE and ALTER
#: are covered: the two statements name their options differently in refusals.
SEQUENCE_OPTION_CASES = (
    (
        "supports_sequence_cycle",
        CreateSequenceExpression,
        {"cycle": True},
        "CYCLE",
        "SEQUENCE CYCLE",
    ),
    (
        "supports_sequence_cycle",
        CreateSequenceExpression,
        {"no_cycle": True},
        "NO CYCLE",
        "SEQUENCE CYCLE",
    ),
    (
        "supports_sequence_cache",
        CreateSequenceExpression,
        {"cache": 10},
        "CACHE 10",
        "SEQUENCE CACHE",
    ),
    (
        "supports_sequence_cache",
        CreateSequenceExpression,
        {"no_cache": True},
        "NO CACHE",
        "SEQUENCE CACHE",
    ),
    (
        "supports_sequence_order",
        CreateSequenceExpression,
        {"order": True},
        "ORDER",
        "SEQUENCE ORDER",
    ),
    (
        "supports_sequence_order",
        CreateSequenceExpression,
        {"no_order": True},
        "NO ORDER",
        "SEQUENCE ORDER",
    ),
    (
        "supports_sequence_cycle",
        AlterSequenceExpression,
        {"cycle": True},
        "CYCLE",
        "ALTER SEQUENCE CYCLE",
    ),
    (
        "supports_sequence_cycle",
        AlterSequenceExpression,
        {"no_cycle": True},
        "NO CYCLE",
        "ALTER SEQUENCE CYCLE",
    ),
    (
        "supports_sequence_cache",
        AlterSequenceExpression,
        {"cache": 10},
        "CACHE 10",
        "ALTER SEQUENCE CACHE",
    ),
    (
        "supports_sequence_cache",
        AlterSequenceExpression,
        {"no_cache": True},
        "NO CACHE",
        "ALTER SEQUENCE CACHE",
    ),
    (
        "supports_sequence_order",
        AlterSequenceExpression,
        {"order": True},
        "ORDER",
        "ALTER SEQUENCE ORDER",
    ),
    (
        "supports_sequence_order",
        AlterSequenceExpression,
        {"no_order": True},
        "NO ORDER",
        "ALTER SEQUENCE ORDER",
    ),
)

SEQUENCE_OPTION_IDS = [
    f"{node.__name__}-{sorted(kwargs)}" for _, node, kwargs, _, _ in SEQUENCE_OPTION_CASES
]


class TestSequenceOptionGates:
    """Each two-spelling sequence option has a parameter per spelling."""

    @pytest.mark.parametrize(
        "probe_name,node,kwargs,fragment,feature",
        SEQUENCE_OPTION_CASES,
        ids=SEQUENCE_OPTION_IDS,
    )
    def test_false_probe_refuses_the_option_by_name(
        self, probe_name, node, kwargs, fragment, feature
    ):
        """Withdrawing the probe must refuse, naming the option -- never drop it."""
        dialect = _withdrawing_dialect(probe_name)()
        expr = node(dialect, Sequence(dialect, "s"), **kwargs)
        with pytest.raises(UnsupportedFeatureError, match=feature):
            expr.to_sql()

    @pytest.mark.parametrize(
        "probe_name,node,kwargs,fragment,feature",
        SEQUENCE_OPTION_CASES,
        ids=SEQUENCE_OPTION_IDS,
    )
    def test_true_probe_renders_the_option(self, probe_name, node, kwargs, fragment, feature):
        """The reference switchboard renders every spelling it declares."""
        dialect = DummyDialect()
        sql = node(dialect, Sequence(dialect, "s"), **kwargs).to_sql()[0]
        assert fragment in sql, f"expected {fragment!r} in {sql!r}"

    @pytest.mark.parametrize(
        "probe_name,node,kwargs,fragment,feature",
        SEQUENCE_OPTION_CASES,
        ids=SEQUENCE_OPTION_IDS,
    )
    def test_gate_is_per_option(self, probe_name, node, kwargs, fragment, feature):
        """Withdrawing one probe must not disable the other options."""
        dialect = _withdrawing_dialect(probe_name)()
        for other_probe, other_node, other_kwargs, other_fragment, _ in SEQUENCE_OPTION_CASES:
            if other_probe == probe_name:
                continue
            sql = other_node(dialect, Sequence(dialect, "s"), **other_kwargs).to_sql()[0]
            assert other_fragment in sql, (
                f"withdrawing {probe_name} also disabled {other_probe}: "
                f"{other_fragment!r} missing from {sql!r}"
            )

    def test_neither_spelling_renders_nothing(self):
        """The reference dialect renders no option when the pair is unset."""
        dialect = DummyDialect()
        sql = CreateSequenceExpression(dialect, Sequence(dialect, "s")).to_sql()[0]
        assert "CYCLE" not in sql and "ORDER" not in sql and "CACHE" not in sql
        sql = AlterSequenceExpression(dialect, Sequence(dialect, "s")).to_sql()[0]
        assert sql == 'ALTER SEQUENCE "s"'

    def test_both_spellings_of_a_pair_are_refused(self):
        dialect = DummyDialect()
        with pytest.raises(ValueError, match="cycle and no_cycle are mutually exclusive"):
            CreateSequenceExpression(dialect, Sequence(dialect, "s"), cycle=True, no_cycle=True)
        with pytest.raises(ValueError, match="cache and no_cache are mutually exclusive"):
            AlterSequenceExpression(dialect, Sequence(dialect, "s"), cache=10, no_cache=True)
        with pytest.raises(ValueError, match="order and no_order are mutually exclusive"):
            CreateSequenceExpression(dialect, Sequence(dialect, "s"), order=True, no_order=True)
