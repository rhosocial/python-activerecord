"""The wildcard quotes through its relation, not its own flags.

The old node carried per-role quoting fields; those are gone. Quoting now
belongs to the relation object the wildcard qualifies. The schema-qualified
forms need a dialect whose namespace probes answer yes -- neither core
dialect models a schema layer, and the render must refuse there rather than
emit a name the engine cannot resolve.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import AllColumnsWildcard
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def schema_dialect():
    """A dummy whose namespace probes admit schema-qualified names."""
    return type(
        "SchemaQualifyingDialect",
        (DummyDialect,),
        {"supports_schema_qualification": lambda self: True},
    )()


class TestWildcardIdentifierQuoting:
    """Quoting decisions ride on the qualified relation's own identity."""

    def test_bare_wildcard_has_no_qualifier(self):
        d = DummyDialect()
        w = AllColumnsWildcard(d)
        assert w.relation is None
        sql, params = d.format_all_columns_wildcard(w)
        assert sql == "*"
        assert params == ()

    def test_relation_quoted_by_default(self):
        d = DummyDialect()
        w = AllColumnsWildcard(d, relation=NamedRelationRef(d, Table(d, "users")))
        sql, params = d.format_all_columns_wildcard(w)
        assert sql == '"users".*'
        assert params == ()

    def test_name_quoting_independent(self):
        d = schema_dialect()
        w = AllColumnsWildcard(
            d,
            relation=NamedRelationRef(
                d,
                Table(d, "users", schema_name="public", name_need_quote=False, schema_need_quote=True),
            ),
        )
        sql, params = d.format_all_columns_wildcard(w)
        assert sql == '"public".users.*'
        assert params == ()

    def test_schema_quoting_independent(self):
        d = schema_dialect()
        w = AllColumnsWildcard(
            d,
            relation=NamedRelationRef(
                d,
                Table(d, "users", schema_name="public", name_need_quote=True, schema_need_quote=False),
            ),
        )
        sql, params = d.format_all_columns_wildcard(w)
        assert sql == 'public."users".*'
        assert params == ()

    def test_schema_refused_where_unmodeled(self):
        """A schema qualifier on a dialect without one is an explicit failure."""
        d = DummyDialect()
        w = AllColumnsWildcard(
            d, relation=NamedRelationRef(d, Table(d, "users", schema_name="public"))
        )
        with pytest.raises(UnsupportedFeatureError, match="schema-qualified"):
            d.format_all_columns_wildcard(w)
