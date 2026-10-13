# tests/rhosocial/activerecord_test/feature/backend/dialect/test_wildcard_protocol.py
"""
Test for the WildcardSupport protocol in its two grammar positions.

The asterisk is one lexical token serving two contracts (spec 4.10): the
select-list/RETURNING expansion and the aggregate row count. A dialect that
only supports wildcards implements both formatter entries; each names its
own formatter, so overriding one spelling never disturbs the other.
"""

from rhosocial.activerecord.backend.dialect import SQLDialectBase, WildcardSupport
from rhosocial.activerecord.backend.dialect.mixins import ExpressionMixin
from rhosocial.activerecord.backend.expression.core import (
    AllColumnsWildcard,
    RowCountWildcard,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef


class WildcardOnlyDialect(SQLDialectBase, ExpressionMixin, WildcardSupport):
    """Dialect that only supports wildcard expressions."""

    pass


def test_wildcard_only_dialect_supports_features():
    """Test that wildcard-only dialect properly supports wildcard features."""
    dialect = WildcardOnlyDialect()

    # Verify protocol implementation
    assert isinstance(dialect, WildcardSupport)


class TestAllColumnsWildcardFormatting:
    """The select-list entry: bare ``*`` and the relation-qualified ``rel.*``."""

    def test_bare_wildcard(self):
        dialect = WildcardOnlyDialect()
        result = dialect.format_all_columns_wildcard(AllColumnsWildcard(dialect))
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] == "*"
        assert result[1] == ()

    def test_qualified_wildcard(self):
        """The qualified form needs a dialect that renders relation objects."""
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        dialect = DummyDialect()
        node = AllColumnsWildcard(
            dialect, relation=NamedRelationRef(dialect, Table(dialect, "users"))
        )
        result = dialect.format_all_columns_wildcard(node)
        assert result[0] == '"users".*'
        assert result[1] == ()

    def test_alias_is_the_qualifier(self):
        """A aliased reference is known by its alias in the query scope."""
        from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

        dialect = DummyDialect()
        node = AllColumnsWildcard(
            dialect, relation=NamedRelationRef(dialect, Table(dialect, "users"), alias="u")
        )
        result = dialect.format_all_columns_wildcard(node)
        assert result[0] == '"u".*'

    def test_format_method_declares_the_entry(self):
        dialect = WildcardOnlyDialect()
        assert AllColumnsWildcard(dialect).format_method == "format_all_columns_wildcard"


class TestRowCountWildcardFormatting:
    """The aggregate-parameter entry: the bare asterisk and nothing else."""

    def test_bare_star(self):
        dialect = WildcardOnlyDialect()
        result = dialect.format_row_count_wildcard(RowCountWildcard(dialect))
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] == "*"
        assert result[1] == ()

    def test_format_method_declares_the_entry(self):
        dialect = WildcardOnlyDialect()
        assert RowCountWildcard(dialect).format_method == "format_row_count_wildcard"

    def test_no_relation_slot(self):
        """The row-count wildcard carries no relation by contract (4.10.2)."""
        import pytest

        dialect = WildcardOnlyDialect()
        with pytest.raises(TypeError):
            RowCountWildcard(dialect, relation=None)
