# tests/rhosocial/activerecord_test/feature/expression/test_order_by_wire.py
"""The ORDER BY element has exactly one spelling per meaning on the wire.

Two things are pinned here, and both came from a cross-language round trip
rather than from a thought about the design.

The first is that an element with no direction must survive. ``direction: null``
is what this library itself writes, and it is also what Go writes for a sort
with no direction -- a reader that crashed on it would reject its own output.

The second is that ``OrderByItem`` and the ``(operand, direction)`` pair are not
two spellings to be chosen freely. They mean the same thing unless null
ordering is involved, and preserving whichever the caller passed would put a
choice on the wire that every other language would then have to guess at.
"""

import pytest

from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression import serialization as ser
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.query_parts import (
    OrderByClause,
    OrderByItem,
    SortDirection,
)


@pytest.fixture
def dialect():
    return DummyDialect()


def encoded_expressions(clause):
    return ser.encode_artifact(clause)["params"]["expressions"]


def test_a_sort_with_no_direction_round_trips(dialect):
    """The pair with a null direction is the shape Go writes for the same sort."""
    clause = OrderByClause(dialect, expressions=[(Column(dialect, "id"), None)])
    assert clause.to_sql()[0] == 'ORDER BY "id"'
    encoded = encoded_expressions(clause)
    assert encoded[0][1] is None, "the absent direction must travel as null"


def test_the_pair_and_the_item_produce_the_same_bytes(dialect):
    """Building it either way must not change the artifact.

    An artifact has to be byte-identical across four languages. That it does
    not depend on how the caller happened to spell the same sort is what makes
    such an artifact possible at all.
    """
    as_item = OrderByClause(dialect, expressions=[OrderByItem(dialect, Column(dialect, "id"))])
    as_pair = OrderByClause(dialect, expressions=[(Column(dialect, "id"), None)])
    assert ser.encode_artifact(as_item) == ser.encode_artifact(as_pair)


def test_null_ordering_keeps_the_node_form(dialect):
    """The pair cannot express NULLS FIRST/LAST, so that case stays a node.

    This is the one meaning the node form exists for; collapsing it into a
    pair would have to drop the request.
    """
    clause = OrderByClause(
        dialect, expressions=[OrderByItem(dialect, Column(dialect, "id"), nulls="last")]
    )
    entry = encoded_expressions(clause)[0]
    assert entry["kind"] == "order_by_item"
    assert entry["params"]["nulls"] == "last"


def test_a_direction_written_as_sql_still_normalizes(dialect):
    """``DESC`` from habit and ``desc`` from the wire word are one thing.

    A caller writing the keyword must not ship the keyword: that is the same
    two-spellings problem, one level up.
    """
    clause = OrderByClause(dialect, expressions=[(Column(dialect, "id"), "DESC")])
    assert encoded_expressions(clause)[0][1] == "desc"


class TestSortDirectionParse:
    """Absent is a value; wrong is an error. Neither is a crash."""

    def test_absent_direction_is_none(self):
        assert SortDirection.parse(None) is None

    @pytest.mark.parametrize("word", ["asc", "ASC", "desc", "DESC", " Desc "])
    def test_accepts_either_case_and_surrounding_space(self, word):
        assert SortDirection.parse(word) is not None

    @pytest.mark.parametrize("word", ["sideways", 123, 4.5, [], {}])
    def test_rejects_anything_else_explicitly(self, word):
        with pytest.raises(ValueError):
            SortDirection.parse(word)


def test_the_directive_renders_no_keyword_without_a_direction(dialect):
    """The formatter must not reach for a keyword that is not there.

    The constructor accepts an absent direction, so a formatter that assumed one
    would turn a valid artifact into an AttributeError at render time -- which
    is how this was found.
    """
    clause = OrderByClause(dialect, expressions=[(Column(dialect, "id"), None)])
    sql, _ = clause.to_sql()
    assert sql == 'ORDER BY "id"'
    assert "ASC" not in sql and "DESC" not in sql