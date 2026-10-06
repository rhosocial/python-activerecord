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
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
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
