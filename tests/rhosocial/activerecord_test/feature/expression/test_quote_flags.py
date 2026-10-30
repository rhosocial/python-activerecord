# tests/rhosocial/activerecord_test/feature/expression/test_quote_flags.py
"""A quoting flag is a bool, and the annotation is the only thing saying so.

These flags have no third state. There is no "unspecified" to represent,
because the formatter never meets an absent one: the value is settled at
construction and carried on the artifact (expression-dialect §10.1). So the only
way a flag goes wrong is a caller passing something that is not a bool.

Python does not enforce annotations, so nothing stopped `name_need_quote=None` --
and None takes the branch that writes the identifier out with nothing escaped,
which is the decision the caller never made. The signature already said `bool`;
this is where the type is actually checked.

The Go port made the same mistake from the other direction: there `bool`'s zero
value is false, so leaving the flag unset read as "do not quote". Both ends
arrive at "the identifier is written bare", and both suites pass either way,
because each is self-consistent.
"""

import pytest

from rhosocial.activerecord.backend.expression import core as C
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects.base import SchemaObject
from rhosocial.activerecord.backend.expression.objects.relation import Table
from rhosocial.activerecord.backend.expression.sources.relation import NamedRelationRef
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect():
    return DummyDialect()


class TestTheValidator:
    def test_a_bool_passes_through_untouched(self):
        assert BaseExpression.quote_flag(True, "flag") is True
        assert BaseExpression.quote_flag(False, "flag") is False

    @pytest.mark.parametrize("value", [None, 0, 1, "", "yes", [], {}])
    def test_anything_else_is_refused(self, value):
        with pytest.raises(TypeError):
            BaseExpression.quote_flag(value, "flag")

    def test_the_message_names_the_owner_and_the_flag(self):
        """A type error that does not say where is a type error you read twice."""
        with pytest.raises(TypeError) as caught:
            SchemaObject.quote_flag(None, "name_need_quote")
        message = str(caught.value)
        assert "SchemaObject" in message
        assert "name_need_quote" in message
        assert "NoneType" in message


class TestEveryFlagIsCheckedAtConstruction:
    """Each owner, each flag -- the point is that none was missed."""

    def test_column_flags(self, dialect):
        for flag in ("name_need_quote", "alias_need_quote",
                     "schema_need_quote", "table_need_quote"):
            with pytest.raises(TypeError, match=flag):
                C.Column(dialect, "id", **{flag: None})

    def test_identifier_flags(self, dialect):
        for flag in ("name_need_quote", "schema_need_quote"):
            with pytest.raises(TypeError, match=flag):
                C.QualifiedIdentifier(dialect, "u", **{flag: None})

    def test_schema_object_flags(self, dialect):
        for flag in ("catalog_need_quote", "schema_need_quote", "name_need_quote"):
            with pytest.raises(TypeError, match=flag):
                Table(dialect, "t", **{flag: None})

    def test_table_source_alias_flag(self, dialect):
        with pytest.raises(TypeError, match="alias_need_quote"):
            NamedRelationRef(dialect, Table(dialect, "t"), alias_need_quote=None)


class TestNormalUseIsUntouched:
    """The check is on the way in; nothing about the ordinary path changes."""

    def test_defaults_quote_every_position(self, dialect):
        column = C.Column(dialect, "id", table="users", alias="pk")
        assert column.name_need_quote is True
        assert column.table_need_quote is True
        assert column.alias_need_quote is True
        assert column.to_sql()[0] == '"users"."id" AS "pk"'

    def test_false_still_writes_the_identifier_bare(self, dialect):
        assert C.Column(dialect, "plain", name_need_quote=False).to_sql()[0] == "plain"

    def test_each_position_answers_for_itself(self, dialect):
        column = C.Column(dialect, "id", table="users", table_need_quote=False)
        assert column.to_sql()[0] == 'users."id"'

    def test_an_integer_zero_is_not_a_false(self, dialect):
        """0 == False in Python, which is exactly why isinstance is the test.

        Accepting 0 would mean a caller passing a count silently decided not to
        quote.
        """
        with pytest.raises(TypeError):
            C.Column(dialect, "id", name_need_quote=0)