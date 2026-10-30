# tests/rhosocial/activerecord_test/feature/expression/test_registry_contract.py
"""Selective registration: what a registry does and does not decide.

The default instance holds every kind the framework ships, so on its own it
shows nothing about *why* a registry exists. These tests use the difference:
the same artifacts read through tables that differ by a few kinds.

The property under test is not "a narrow registry is narrow". It is that a
registry filters **what an artifact actually contains**, and nothing else:

* a kind the artifact never mentions costs nothing to leave out, even when the
  declaring class has a parameter of that type;
* a kind the artifact does mention is refused, by name, when it is left out.

That combination is what makes a table usable as a boundary. A caller who
allows ``WhereClause`` but not ``GroupByClause`` can read every query that has
no grouping, and no query that has one -- without knowing, or enumerating, the
kinds any of those trees happen to be built from.

Write-side asymmetry is deliberate and tested here too. ``serialize`` consults
no registry (§7.2), so a narrow table does not stop a tree being *written* --
it decides what a reader will accept. See
:func:`test_serializing_ignores_the_registry_entirely` for what that does and
does not buy.
"""

from datetime import timedelta

import pytest

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.operators import RawSQL
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts import (
    GroupByHavingClause,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.query_sources import ValuesExpression
from rhosocial.activerecord.backend.expression.values import LiteralKind
from rhosocial.activerecord.backend.expression.registry import ExpressionRegistry
from rhosocial.activerecord.backend.expression.serialization import (
    default_registry,
    deserialize,
    serialize,
)
from rhosocial.activerecord.backend.expression.statements.dml import InsertStatement
from rhosocial.activerecord.backend.expression.statements.dql import QueryStatement
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect():
    return DummyDialect()


#: The kinds a literal contributes, by wire name.
_VALUE_KINDS = frozenset(member.wire for member in LiteralKind)


def _table(*kinds):
    """A registry holding exactly these kinds and nothing else."""
    registry = ExpressionRegistry()
    full = default_registry()
    value_only = tuple(k for k in kinds if k in _VALUE_KINDS)
    for kind in kinds:
        if kind in _VALUE_KINDS:
            # The twelve value kinds all resolve to Literal, and they are
            # registered by kind rather than by class name.
            continue
        registry.register_node(full.resolve_node(kind))
    registry.register_value_kinds(*value_only)
    return registry


#: Everything the two queries below are built from, minus the grouping clause.
#: ``QueryStatement`` declares a ``group_by_having`` parameter whether or not a
#: query uses one, and that declaration deliberately does not put
#: ``group_by_having_clause`` into the artifact.
#: ``literal`` does not appear here because a literal's kind is its *value*
#: kind: one class carries all twelve, and the artifact names whichever the
#: value calls for. The query below holds the integer 18, so the kind an
#: allow-list has to admit is ``integer_value``.
READS_QUERIES = (
    "query_statement",
    "where_clause",
    "comparison_predicate",
    "column",
    "integer_value",
    "table",
)


def _query(dialect, grouped=False):
    users = Table(dialect, "users")
    where = WhereClause(
        dialect,
        ComparisonPredicate(dialect, ">", Column(dialect, "age"), Literal(dialect, 18)),
    )
    if not grouped:
        return QueryStatement(
            dialect, select=[Column(dialect, "id")], from_=users, where=where
        )
    return QueryStatement(
        dialect,
        select=[Column(dialect, "city")],
        from_=users,
        where=where,
        group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "city")]),
    )


def _insert(dialect):
    users = Table(dialect, "users")
    return InsertStatement(
        dialect,
        into=users,
        source=ValuesExpression(dialect, [(Literal(dialect, 1),)]),
        columns=["id"],
    )


def _kinds_in(artifact):
    """Every kind the artifact names, walking the payload.

    A node is ``{kind, params}`` at every depth -- nested ones are not wrapped,
    so one walk finds them all.
    """
    found = set()
    stack = [artifact]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if isinstance(node.get("kind"), str):
                found.add(node["kind"])
            for value in node.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(v for v in node if isinstance(v, (dict, list)))
    return found


# ---------------------------------------------------------------------------
# The default table
# ---------------------------------------------------------------------------


def test_the_default_registry_reads_everything_the_tree_produces(dialect):
    """The baseline. Without it, the narrower tables prove nothing."""
    for grouped in (False, True):
        artifact = serialize(_query(dialect, grouped))
        restored = deserialize(artifact, dialect, registry=default_registry())
        assert isinstance(restored, QueryStatement)


# ---------------------------------------------------------------------------
# A kind left out costs nothing until the artifact names it
# ---------------------------------------------------------------------------


def test_a_declared_parameter_does_not_put_its_kind_in_the_artifact(dialect):
    """``group_by_having`` is declared either way; only a grouping carries it."""
    plain = serialize(_query(dialect, grouped=False))
    grouped = serialize(_query(dialect, grouped=True))
    assert plain["params"]["group_by_having"] is None
    assert grouped["params"]["group_by_having"]["kind"] == "group_by_having_clause"


def test_an_artifact_without_the_kind_reads_without_the_kind(dialect):
    """The case that makes a narrow table usable.

    ``QueryStatement`` declares a grouping parameter, so a reader that resolved
    kinds from the *declaration* rather than from the payload would demand
    ``group_by_having_clause`` here and refuse a query that has no grouping.
    """
    artifact = serialize(_query(dialect, grouped=False))
    allowed = _table(*READS_QUERIES)
    restored = deserialize(artifact, dialect, registry=allowed)
    assert isinstance(restored, QueryStatement)
    assert restored.get_params()["group_by_having"] is None


def test_an_artifact_naming_an_unregistered_kind_is_refused(dialect):
    """The other half, and the reason a narrow table is worth anything."""
    artifact = serialize(_query(dialect, grouped=True))
    allowed = _table(*READS_QUERIES)
    with pytest.raises(Exception) as caught:
        deserialize(artifact, dialect, registry=allowed)
    assert "group_by_having_clause" in str(caught.value)


def test_the_same_registry_gives_different_answers_for_different_artifacts(dialect):
    """One table, two artifacts, two outcomes -- and nothing else differs."""
    allowed = _table(*READS_QUERIES)
    plain = serialize(_query(dialect, grouped=False))
    grouped = serialize(_query(dialect, grouped=True))
    assert isinstance(deserialize(plain, dialect, registry=allowed), QueryStatement)
    with pytest.raises(Exception):
        deserialize(grouped, dialect, registry=allowed)


# ---------------------------------------------------------------------------
# A boundary stated as a policy
# ---------------------------------------------------------------------------


def test_a_read_only_table_refuses_to_produce_a_write(dialect):
    """``GROUP BY`` not permitted: the table says so by what it omits."""
    read_only = _table(*READS_QUERIES)
    with pytest.raises(Exception) as caught:
        deserialize(serialize(_insert(dialect)), dialect, registry=read_only)
    assert "insert_statement" in str(caught.value)


def test_a_table_must_cover_exactly_what_the_artifact_carries(dialect):
    """The required set is the payload's own kinds -- computed, not guessed.

    Read off the artifact rather than written by hand, so this states the
    property instead of restating a list that someone has to keep in step.
    A tree carrying an INSERT needs ``insert_statement``, ``values_expression``
    and ``integer_value``; admitting the first alone is refused on the second.
    Nothing the INSERT could conceivably contain but does not -- grouping,
    joining, a WHERE clause -- is asked for.
    """
    artifact = serialize(_insert(dialect))
    needed = _kinds_in(artifact)

    # Sanity: the walk sees the whole payload, not just the root.
    assert {"insert_statement", "values_expression", "integer_value"} <= needed
    assert not (needed & {"group_by_having_clause", "join_clause", "where_clause"})

    missing_one = needed - {"values_expression"}
    with pytest.raises(Exception) as caught:
        deserialize(artifact, dialect, registry=_table(*missing_one))
    assert "values_expression" in str(caught.value)

    assert isinstance(deserialize(artifact, dialect, registry=_table(*needed)), InsertStatement)


def test_a_query_table_covers_only_what_its_payload_carries(dialect):
    """The same statement, read through a table built for queries.

    No closure, no guesswork: the six kinds below are the ones the ungrouped
    query names, and the grouped one names a seventh.
    """
    plain = _kinds_in(serialize(_query(dialect, grouped=False)))
    grouped = _kinds_in(serialize(_query(dialect, grouped=True)))
    assert set(READS_QUERIES) == plain
    assert grouped == plain | {"group_by_having_clause"}


# ---------------------------------------------------------------------------
# The write side, which is deliberately not gated
# ---------------------------------------------------------------------------


def test_serializing_ignores_the_registry_entirely(dialect):
    """§7.2: the node reports its own kind, so writing consults no table.

    Stated explicitly because the consequence matters: a narrow registry is a
    **read** boundary. It decides what a reader will accept from an artifact it
    did not author. It does not stop a tree being written, and it does not
    decide what may be executed -- a caller that constructs its own
    ``GroupByHavingClause`` and runs it never touches a registry at all.

    A boundary that had to hold on the write side would need a different
    mechanism, because the writer is the same process that would enforce it.
    """
    grouped = _query(dialect, grouped=True)
    narrow = _table(*READS_QUERIES)

    artifact = serialize(grouped)  # no registry argument exists to pass
    assert artifact["params"]["group_by_having"]["kind"] == "group_by_having_clause"

    # And the artifact just produced is refused by the very table that was
    # never consulted while writing it.
    with pytest.raises(Exception):
        deserialize(artifact, dialect, registry=narrow)


# ---------------------------------------------------------------------------
# A kind the framework ships, and does not admit by default
# ---------------------------------------------------------------------------


def test_caller_vouched_text_is_left_out_of_the_default_table(dialect):
    """``raw_sql`` defines a kind, names a formatter, and is left out anyway.

    ``REGISTER_BY_DEFAULT = False`` says nothing about the node being
    unfinished. It says what admitting it would mean: ``to_sql()`` emits
    ``expression`` verbatim, so a reader that resolved the kind out of an
    artifact would rebuild a node whose SQL the *artifact* chose. The default
    table is what an untrusted payload is resolved against, so the default
    says no.
    """
    assert RawSQL.kind() == "raw_sql"
    assert RawSQL.REGISTER_BY_DEFAULT is False
    assert "raw_sql" not in default_registry().node_kinds()

    # Writing is unaffected (§7.2): the kind still names itself.
    artifact = serialize(RawSQL(dialect, "SELECT 1"))
    assert artifact["kind"] == "raw_sql"

    with pytest.raises(Exception) as caught:
        deserialize(artifact, dialect)
    assert "raw_sql" in str(caught.value)


def test_a_caller_who_trusts_its_artifacts_can_register_it(dialect):
    """The other half, and the reason this is a default rather than a ban.

    Nothing refuses the class. ``register_node`` is the same call any selective
    table makes, so opting in is not a privileged path -- which is the whole
    difference between a sensible default and a prohibition.
    """
    opted_in = ExpressionRegistry()
    opted_in.register_node(RawSQL)
    assert opted_in.node_kinds() == ("raw_sql",)

    restored = deserialize(
        serialize(RawSQL(dialect, "SELECT 1")), dialect, registry=opted_in
    )
    assert isinstance(restored, RawSQL)
    assert restored.expression == "SELECT 1"
    assert restored.to_sql() == ("SELECT 1", ())


def test_a_raw_sql_bind_value_survives_the_round_trip(dialect):
    """The one place a non-JSON type is allowed, and it needs the value kinds.

    ``params`` are wrapped in ``Literal`` at construction, so each bind value
    carries the kind that says what it is. Without that, ``b"\\x00"`` and a
    string are the same three bytes on the wire and a reader cannot tell them
    apart -- the values sent to the database are precisely the ones that must not
    be guessed at.

    So opting ``raw_sql`` in is two registrations, not one: the node, and the
    value vocabulary its parameters speak.
    """
    opted_in = ExpressionRegistry()
    opted_in.register_node(RawSQL)
    opted_in.register_value_kinds()

    node = RawSQL(
        dialect,
        "SELECT * FROM t WHERE blob = ? AND span = ?",
        (b"\x00\x01", timedelta(seconds=90)),
    )
    restored = deserialize(serialize(node), dialect, registry=opted_in)

    # The driver is handed plain values, not nodes.
    assert node.to_sql()[1] == (b"\x00\x01", timedelta(seconds=90))
    # ...and the values came back as themselves, not as text.
    assert [p.value for p in restored.params] == [b"\x00\x01", timedelta(seconds=90)]
    assert restored.to_sql() == node.to_sql()