# tests/rhosocial/activerecord_test/feature/backend/test_to_sql_dispatch_contract.py
"""What ``to_sql`` does when the attribute it finds is not a formatter.

A ``runtime_checkable`` protocol is satisfied by its own ``...`` bodies. So a
probe-only protocol sitting in a dialect's base list answers ``getattr`` on the
formatting method's name, passes the callable check, and returns ``None`` --
which the caller then treats as the rendered SQL. Three backends hit that
independently before it was closed:

* ``CreateFunctionExpression(...).to_sql()`` answering ``None``, because
  postgres wired ``CreateRoutineSupport`` / ``DropRoutineSupport`` into a base
  list without implementing their formatters;
* ``Domain.to_sql()`` answering ``None`` on snowflake, where
  ``TypeObjectSupport`` satisfied ``format_domain_object`` through
  ``TypeNameMixin`` and the protocol body answered instead;
* a formatter returning a bare string rather than ``(sql, params)``, so the
  bind parameters were dropped without a word.

None of the three was visible to a test, because nothing looked at the result.
These tests are the missing look.
"""

from typing import List, Protocol, Tuple, runtime_checkable

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import (
    ProtocolNotImplementedError,
    UnsupportedFeatureError,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@runtime_checkable
class DeclaresTableObjectFormat(Protocol):
    """A probe-only protocol that happens to declare a formatter's name."""

    def format_table_object(self, expr) -> Tuple[str, tuple]: ...


class ProtocolWinsTheLookup(DeclaresTableObjectFormat, DummyDialect):
    """A dialect whose base list puts the protocol ahead of the mixin.

    Order matters and this is the case that was broken: ``DummyDialect`` already
    provides ``format_table_object`` through ``TableNameMixin``, so listing the
    protocol *after* it changes nothing. Listing it first is what a backend does
    when a probe-only protocol is added to a base list, and then the protocol is
    what ``getattr`` finds.
    """


class FormatterReturnsNothing(DummyDialect):
    """A formatter whose body is the protocol stub's body."""

    def format_table_object(self, expr):
        return None


class FormatterReturnsBareString(DummyDialect):
    """A formatter that drops its bind parameters on the floor."""

    def format_table_object(self, expr):
        return '"users"'


class FormatterReturnsOneTuple(DummyDialect):
    """A formatter returning a one-element tuple."""

    def format_table_object(self, expr):
        return ('"users"',)


class TestDispatchContract:
    """The lookup is only a formatter lookup if what answers is a formatter."""

    def test_unaffected_rendering_still_works(self):
        """The guard must not change the ordinary path."""
        sql, params = Table(DummyDialect(), "users").to_sql()
        assert sql == '"users"'
        assert params == ()

    def test_protocol_answering_is_reported_as_not_implemented(self):
        """The bug: a protocol in the base list answered and returned None.

        Pinned because the fix is invisible from the outside -- before it,
        this call returned ``None`` and the caller used it as SQL.
        """
        dialect = ProtocolWinsTheLookup()

        # The precondition is the whole point: the protocol satisfies isinstance
        # structurally, so nothing upstream can tell it from a real formatter.
        assert isinstance(dialect, DeclaresTableObjectFormat)

        with pytest.raises(ProtocolNotImplementedError) as exc_info:
            Table(dialect, "users").to_sql()

        message = str(exc_info.value)
        assert "format_table_object" in message
        assert "Table" in message

    def test_formatter_returning_none_is_reported_as_not_implemented(self):
        with pytest.raises(ProtocolNotImplementedError):
            Table(FormatterReturnsNothing(), "users").to_sql()

    @pytest.mark.parametrize(
        "dialect_class",
        [FormatterReturnsBareString, FormatterReturnsOneTuple],
    )
    def test_wrong_return_shape_is_refused(self, dialect_class):
        """A bare string looks like success and silently drops the parameters."""
        with pytest.raises(TypeError) as exc_info:
            Table(dialect_class(), "users").to_sql()

        message = str(exc_info.value)
        assert "must return (sql, params)" in message
        # The message has to name both causes, because they need different fixes.
        assert "protocol" in message
        assert "bind parameters" in message

    def test_missing_formatter_reports_a_capability_gap(self):
        """A dialect with no such formatter is reporting a capability gap.

        The tree reports every other capability gap through a probe raising
        ``UnsupportedFeatureError``, so the dispatch does too; the runners
        already catch both of these.
        """

        class NoTableObjectFormat(DummyDialect):
            format_table_object = None

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            Table(NoTableObjectFormat(), "users").to_sql()

        message = str(exc_info.value)
        assert "format_table_object" in message
        # The suggestion has to name what the caller can do about it.
        assert "mix in the mixin" in message

    def test_both_dispatch_failures_are_caught_where_rendering_happens(self):
        """The migration runners already handle these two; assert they stay handled.

        Otherwise the fix would convert a silent ``None`` into an unhandled
        exception at the boundary that renders.
        """
        for module_name in (
            "rhosocial.activerecord.backend.migration.runner",
            "rhosocial.activerecord.backend.migration.async_runner",
        ):
            module = __import__(module_name, fromlist=["*"])
            caught = " ".join(handler_names(module))
            assert "ProtocolNotImplementedError" in caught, module_name
            assert "UnsupportedFeatureError" in caught, module_name


def handler_names(module) -> List[str]:
    """Exception names the module catches, read from its source.

    Read rather than executed because triggering either condition needs a live
    database, and the claim is about the except clauses existing at all.
    """
    import inspect

    try:
        text = inspect.getsource(module)
    except OSError:  # pragma: no cover
        return []
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("except") and "Error" in line
    ]