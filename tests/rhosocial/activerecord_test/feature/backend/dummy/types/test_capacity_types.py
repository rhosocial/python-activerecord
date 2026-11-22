# tests/rhosocial/activerecord_test/feature/backend/dummy/types/test_capacity_types.py
"""The five content types' capacity parameter, and what it means.

SQL text has no "any number of bytes": every backend chooses a tier. A
declaration of capacity is therefore a **minimum** -- "this column must hold N
characters" -- and what a dialect does with it is that dialect's business. What
the types themselves must guarantee is narrower and testable here:

* the parameter exists and survives construction and rendering;
* two different minima are two different types, while the same minimum is the
  same type;
* a dialect with no tier to choose satisfies it rather than refusing it.
"""
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedDataTypeError
from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    JsonBType,
    JsonType,
    TextType,
    VarCharType,
    XmlType,
)

CAPACITY_TYPES = [TextType, BlobType, JsonType, JsonBType, XmlType]


def _sqlite_dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    return SQLiteDialect()


def _dummy_dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

    return DummyDialect()


@pytest.mark.parametrize("factory", CAPACITY_TYPES)
def test_a_capacity_is_carried_and_reported(factory):
    declared = factory(length=16000)

    assert declared.length == 16000
    assert undeclared_length(factory) is None


def undeclared_length(factory):
    return factory().length


@pytest.mark.parametrize("factory", CAPACITY_TYPES)
def test_two_minima_are_two_types(factory):
    """Capacity is part of identity, exactly like a VARCHAR width.

    If it were not, a differ could not see that a document column now needs to
    hold twice as much, and the migration would silently keep the old size.
    """
    assert factory(length=16000) != factory(length=3500)
    assert factory(length=16000) == factory(length=16000)


@pytest.mark.parametrize("factory", [TextType, BlobType, JsonType, JsonBType])
def test_a_dialect_with_no_tier_satisfies_the_minimum(factory):
    """A minimum is satisfied by an unbounded column, not refused by it.

    SQLite has one text spelling and one binary one; declaring a minimum there
    describes a fact it already satisfies, so rendering must not fail.
    """
    sql, params = _sqlite_dialect().format_data_type(factory(length=16000))

    assert params == ()
    assert sql


def test_a_substituted_concept_names_its_substitute():
    """SQLite has no XML type: it stores XML as text, and says so.

    The declaration still fails rather than silently becoming a text column,
    because a substitution is an answer about the *concept*, not an invitation
    to re-declare the field behind the caller's back -- and the minimum stays
    the caller's to write, as a text type, once they have heard the answer.
    """
    dialect = _sqlite_dialect()
    substitute = dialect.suggest_substitute_types().mapping["xml"]

    assert substitute is not None
    with pytest.raises(UnsupportedDataTypeError):
        dialect.format_data_type(XmlType(length=16000))


@pytest.mark.parametrize("factory", CAPACITY_TYPES)
def test_the_dummy_baseline_renders_the_minimum(factory):
    sql, params = _dummy_dialect().format_data_type(factory(length=16000))

    assert params == ()
    assert sql


def test_a_minimum_is_not_a_width_for_a_fixed_width_type():
    """``VarCharType`` keeps its old meaning: a width, not a minimum.

    The difference is not cosmetic. A width the server enforces has to match;
    a document column's capacity is a floor. Both live on ``length`` because
    both answer "how much does this hold", so this is what keeps the difference
    visible when one of them changes.
    """
    assert VarCharType(length=255).length == 255
    assert VarCharType() != VarCharType(length=255)


def test_the_content_types_stay_types_of_their_own():
    """A capacity parameter does not fold them into the text family.

    Metadata and operations differ: JSON is navigable by path, XML by XPath,
    and both differ from the text several backends store them as. The parameter
    is a shared question, not a shared identity.
    """
    assert {factory.name for factory in CAPACITY_TYPES} == {
        "text", "blob", "json", "jsonb", "xml"
    }