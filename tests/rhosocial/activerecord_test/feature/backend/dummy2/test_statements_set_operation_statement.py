# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_set_operation_statement.py
"""The compound-SELECT statement node: N query parts, one operator word.

The binary :class:`~rhosocial.activerecord.backend.expression.query_sources.SetOperation`
is the *source* half of the pair -- exactly two sides, each of which may itself
be a set operation, for use in a FROM clause. This is the *statement* half, and
the difference is the point: a caller that must ask one arm per column at run
time cannot express that as a fixed pair of sides without inventing a nesting
nobody wrote, so the node takes a list of query statements instead.

What is under test here is that the node carries no SQL. ``op`` is a word form
and the keyword is the dialect's, which is what makes a dialect that refuses the
operation refuse the node rather than render something broken.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    Literal,
    QueryStatement,
    SetOperationStatement,
)
from rhosocial.activerecord.backend.expression.query_sources import SetOperationKind
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.schema import StatementType


def _part(dialect, name, *columns):
    return QueryStatement(
        dialect,
        select=[Column(dialect, column) for column in columns or (name,)],
        from_=name,
    )


class TestSetOperationStatementShape:
    def test_the_parts_are_joined_by_the_operator_word(self, dummy_dialect: DummyDialect):
        node = SetOperationStatement(
            dummy_dialect,
            op=SetOperationKind.UNION_ALL,
            parts=[_part(dummy_dialect, "a"), _part(dummy_dialect, "b"), _part(dummy_dialect, "c")],
        )

        sql, params = node.to_sql()

        assert sql == (
            'SELECT "a" FROM "a" UNION ALL ' 'SELECT "b" FROM "b" UNION ALL ' 'SELECT "c" FROM "c"'
        )
        assert params == ()

    def test_every_word_form_maps_to_its_own_keyword(self, dummy_dialect: DummyDialect):
        for word, keyword in (
            ("union", "UNION"),
            ("union_all", "UNION ALL"),
            ("intersect", "INTERSECT"),
            ("except", "EXCEPT"),
        ):
            node = SetOperationStatement(
                dummy_dialect, op=word, parts=[_part(dummy_dialect, "a"), _part(dummy_dialect, "b")]
            )
            sql, _ = node.to_sql()
            assert f" {keyword} " in sql, (word, sql)
            assert node.op is SetOperationKind(word)

    def test_a_single_part_renders_that_query_alone(self, dummy_dialect: DummyDialect):
        """One part is legal: the node is not inventing an operator to join."""
        node = SetOperationStatement(
            dummy_dialect, op=SetOperationKind.UNION_ALL, parts=[_part(dummy_dialect, "a")]
        )

        sql, params = node.to_sql()

        assert "UNION" not in sql
        assert sql == 'SELECT "a" FROM "a"'
        assert params == ()
        assert node.op is SetOperationKind.UNION_ALL

    def test_the_word_form_is_stored_not_the_keyword(self, dummy_dialect: DummyDialect):
        """The tree says what is meant; the dialect says how it is spelled."""
        node = SetOperationStatement(
            dummy_dialect,
            op=SetOperationKind.UNION_ALL,
            parts=[_part(dummy_dialect, "a"), _part(dummy_dialect, "b")],
        )

        assert node.op.value == "union_all"
        assert "UNION ALL" not in str(node.op)

    def test_a_symbol_spelling_is_refused(self, dummy_dialect: DummyDialect):
        """``op`` takes the word forms and nothing else, as its sibling does."""
        with pytest.raises(ValueError, match="word forms"):
            SetOperationStatement(dummy_dialect, op="UNION ALL", parts=[_part(dummy_dialect, "a")])

    def test_the_params_are_concatenated_in_part_order(self, dummy_dialect: DummyDialect):
        """One statement's parameters stay in the order its parts were given."""
        left = QueryStatement(
            dummy_dialect,
            select=[Column(dummy_dialect, "a")],
            from_="t",
            where=ComparisonPredicate(
                dummy_dialect, "gt", Column(dummy_dialect, "a"), Literal(dummy_dialect, 1)
            ),
        )
        right = QueryStatement(
            dummy_dialect,
            select=[Column(dummy_dialect, "b")],
            from_="t",
            where=ComparisonPredicate(
                dummy_dialect, "lt", Column(dummy_dialect, "b"), Literal(dummy_dialect, 9)
            ),
        )
        node = SetOperationStatement(
            dummy_dialect, op=SetOperationKind.UNION_ALL, parts=[left, right]
        )

        sql, params = node.to_sql()

        assert sql.count("UNION ALL") == 1
        assert params == (1, 9)

    def test_a_part_that_is_not_a_query_is_refused(self, dummy_dialect: DummyDialect):
        """The formatter names the defect rather than rendering a half-query."""
        node = SetOperationStatement(
            dummy_dialect, op=SetOperationKind.UNION_ALL, parts=["SELECT 1"]
        )

        with pytest.raises(TypeError, match="QueryStatement"):
            node.to_sql()

    def test_get_params_carries_the_wire_shape(self, dummy_dialect: DummyDialect):
        parts = [_part(dummy_dialect, "a"), _part(dummy_dialect, "b")]
        node = SetOperationStatement(dummy_dialect, op=SetOperationKind.UNION_ALL, parts=parts)

        params = node.get_params()

        assert set(params) == {"op", "parts"}
        assert params["op"] == "union_all"
        assert params["parts"] == parts

    def test_the_statement_type_is_a_query(self, dummy_dialect: DummyDialect):
        node = SetOperationStatement(
            dummy_dialect, op=SetOperationKind.UNION_ALL, parts=[_part(dummy_dialect, "a")]
        )

        assert node.statement_type is StatementType.DQL

    def test_the_kind_is_derived_from_the_class_name(self, dummy_dialect: DummyDialect):
        node = SetOperationStatement(
            dummy_dialect, op=SetOperationKind.UNION_ALL, parts=[_part(dummy_dialect, "a")]
        )

        assert node.kind() == "set_operation_statement"


class TestTheDialectGatesIt:
    def test_an_operation_the_dialect_refuses_is_refused(
        self, dummy_dialect: DummyDialect, monkeypatch
    ):
        """The node reuses the per-operation probes rather than inventing one."""
        # DummyDialect answers True to all four, which is the neutral stance a
        # dialect takes when it declines to specialise; lying here proves the
        # gate is wired to the probe rather than assumed.
        monkeypatch.setattr(dummy_dialect, "supports_union_all", lambda: False)
        node = SetOperationStatement(
            dummy_dialect,
            op=SetOperationKind.UNION_ALL,
            parts=[_part(dummy_dialect, "a"), _part(dummy_dialect, "b")],
        )

        with pytest.raises(UnsupportedFeatureError):
            node.to_sql()

    def test_the_dummy_dialect_admits_the_two_unions(self, dummy_dialect: DummyDialect):
        assert dummy_dialect.supports_union() is True
        assert dummy_dialect.supports_union_all() is True
