# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_inline_literals.py
"""Tests for class-level inline-literal rendering (``inline_params`` strategy).

Covers:
- ``Literal`` (data position): always a bind-parameter placeholder
- ``DdlLiteral`` (DDL position): inline escaped text via format_literal, no params
- Per-class isolation inside a comparison predicate
- The strategy is read off the class, so an instance-level assignment has
  no effect on rendering
- The DDL renderers lift plain literals to the DDL class (CHECK condition
  and partial-index WHERE carry no bind parameters)
"""

from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    DdlLiteral,
    Literal,
)


def _dummy_dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    return DummyDialect()


class TestInlineParamsClassStrategy:
    """Literal rendering honours the class-level inline_params strategy."""

    def test_data_position_literal_uses_placeholder(self):
        lit = Literal(_dummy_dialect(), "abc")
        assert type(lit).inline_params is False
        assert lit.to_sql() == ("?", ("abc",))

    def test_ddl_position_literal_inlines_text(self):
        lit = DdlLiteral(_dummy_dialect(), "abc")
        sql, params = lit.to_sql()
        assert sql == "'abc'"
        assert params == ()

    def test_ddl_literal_escapes_quotes(self):
        lit = DdlLiteral(_dummy_dialect(), "it's")
        sql, params = lit.to_sql()
        assert sql == "'it''s'"
        assert params == ()

    def test_ddl_literal_numeric(self):
        assert DdlLiteral(_dummy_dialect(), 42).to_sql() == ("42", ())

    def test_per_class_isolation_in_predicate(self):
        dialect = _dummy_dialect()
        pred = ComparisonPredicate(
            dialect, "=",
            DdlLiteral(dialect, "a"),
            Literal(dialect, "b"),
        )
        sql, params = pred.to_sql()
        assert sql == "'a' = ?"
        assert params == ("b",)

    def test_instance_assignment_cannot_flip_the_strategy(self):
        """The formatters read the class attribute, not the instance."""
        lit = Literal(_dummy_dialect(), "abc")
        assert lit.to_sql() == ("?", ("abc",))
        lit.inline_params = True  # instance shadowing must stay inert
        assert lit.to_sql() == ("?", ("abc",))
        del lit.inline_params

    def test_ddl_literal_repr(self):
        assert repr(DdlLiteral(_dummy_dialect(), 1)) == "DdlLiteral(1)"

    def test_check_condition_lifts_plain_literals(self):
        """A CHECK built from ordinary data-position nodes renders inline."""
        from rhosocial.activerecord.backend.expression import TableCheckConstraint

        condition = ComparisonPredicate(
            _dummy_dialect(), ">", Column(_dummy_dialect(), "age"), Literal(_dummy_dialect(), 0)
        )
        constraint = TableCheckConstraint(_dummy_dialect(), condition)
        assert constraint.to_sql() == ('CHECK ("age" > 0)', ())

    def test_partial_index_where_lifts_plain_literals(self):
        from rhosocial.activerecord.backend.expression.objects import Index
        from rhosocial.activerecord.backend.expression.objects import Table
        from rhosocial.activerecord.backend.expression.statements.ddl_index import CreateIndexStatement

        dialect = _dummy_dialect()
        where = ComparisonPredicate(
            dialect, "=", Column(dialect, "status"), Literal(dialect, "active")
        )
        stmt = CreateIndexStatement(
            dialect, index=Index(dialect, "idx_active"), table=Table(dialect, "users"),
            columns=["email"], where=where,
        )
        sql, params = stmt.to_sql()
        assert "WHERE \"status\" = 'active'" in sql
        assert params == ()
