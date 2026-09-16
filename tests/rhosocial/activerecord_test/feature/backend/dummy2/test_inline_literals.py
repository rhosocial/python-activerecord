# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_inline_literals.py
"""Tests for Literal inline-literal rendering (per-node inline_literals switch).

Covers:
- Default off: bind-parameter placeholder + params
- Explicit on: inline escaped text via format_literal + empty params
- Per-node isolation inside a comparison predicate
- Setter toggling on an existing node
"""

from rhosocial.activerecord.backend.expression import Literal, ComparisonPredicate


def _dummy_dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    return DummyDialect()


class TestInlineLiterals:
    """Literal rendering honours the per-node inline_literals switch."""

    def test_default_off_uses_placeholder(self):
        lit = Literal(_dummy_dialect(), "abc")
        assert lit.inline_literals is False
        assert lit.to_sql() == ("?", ("abc",))

    def test_explicit_on_inlines_text(self):
        lit = Literal(_dummy_dialect(), "abc", inline_literals=True)
        sql, params = lit.to_sql()
        assert sql == "'abc'"
        assert params == ()

    def test_inline_escapes_quotes(self):
        lit = Literal(_dummy_dialect(), "it's", inline_literals=True)
        sql, params = lit.to_sql()
        assert sql == "'it''s'"
        assert params == ()

    def test_inline_numeric(self):
        lit = Literal(_dummy_dialect(), 42, inline_literals=True)
        assert lit.to_sql() == ("42", ())

    def test_per_node_isolation_in_predicate(self):
        dialect = _dummy_dialect()
        pred = ComparisonPredicate(
            dialect, "=",
            Literal(dialect, "a", inline_literals=True),
            Literal(dialect, "b"),
        )
        sql, params = pred.to_sql()
        assert sql == "'a' = ?"
        assert params == ("b",)

    def test_setter_toggling(self):
        lit = Literal(_dummy_dialect(), "abc")
        assert lit.to_sql() == ("?", ("abc",))
        lit.inline_literals = True
        assert lit.to_sql() == ("'abc'", ())
        lit.inline_literals = False
        assert lit.to_sql() == ("?", ("abc",))
