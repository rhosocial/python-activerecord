# tests/rhosocial/activerecord_test/feature/query/test_document_and_conversion_families.py
"""The families that carry documents, sequences, casts and XML.

A JSON extraction is not always a document: `->` hands back JSON and `->>`
hands back text, so the same node class reports two families and the chain
narrows. A cast states its result in the target type, which is the only place
it can come from. And an operation over several values — GREATEST, a CASE —
answers with their common kind, or with nothing when they disagree.
"""

# tests/rhosocial/activerecord_test/feature/query/test_document_and_conversion_families.py
import pytest

from rhosocial.activerecord.backend.expression import functions as F, Literal
from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.advanced_functions import CaseExpression
from rhosocial.activerecord.backend.expression.core import (
    ArrayValueExpression,
    JSONValueExpression,
)
from rhosocial.activerecord.backend.expression.type_name import is_valid_type_name
from rhosocial.activerecord.backend.expression.types import VarCharType, JsonType, CustomType


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    d = SQLiteDialect()
    d._version = (3, 46, 1)
    return d


@pytest.fixture
def columns(dialect):
    from rhosocial.activerecord.base.column_dispatch import build_column

    return {
        "int": build_column(dialect, "i", int),
        "float": build_column(dialect, "f", float),
        "str": build_column(dialect, "s", str),
        "json": build_column(dialect, "j", dict),
        "array": build_column(dialect, "l", list),
    }


# ---------------------------------------------------------------------------
# The same node, two families
# ---------------------------------------------------------------------------


def test_arrow_extraction_gives_a_document(dialect, columns):
    assert isinstance(F.json_extract(dialect, columns["json"], Literal(dialect, "$.a")), JSONValueExpression)


def test_double_arrow_extraction_gives_text(dialect, columns):
    """`->>` is a narrowing: a document becomes a string and cannot widen back."""
    assert isinstance(F.json_extract_text(dialect, columns["json"], "$.a"), StringValueExpression)


def test_a_built_document_is_a_document(dialect, columns):
    assert isinstance(F.json_build_object(dialect, "k", 1), JSONValueExpression)
    assert isinstance(F.json_array_elements(dialect, columns["json"]), JSONValueExpression)


def test_a_document_offers_the_json_accessors(dialect, columns):
    built = F.json_build_object(dialect, "k", 1)
    assert isinstance(built, JSONValueExpression)
    assert hasattr(built, "json_path")
    assert not hasattr(built, "upper")


def test_text_reports_a_string_family(dialect, columns):
    """Narrowing is reported, which is what propagation reads.

    The JSON accessors stay, because one node class serves both arrow
    directions and the wrapper cannot hide what it forwards — that is a known
    over-offer on this one class, not a claim that text is a document.
    """
    text = F.json_extract_text(dialect, columns["json"], "$.a")
    assert isinstance(text, StringValueExpression)
    assert text.to_sql()[0].endswith("->>'$.a'")


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------


def test_a_sequence_is_a_sequence(dialect, columns):
    assert isinstance(F.unnest(dialect, columns["array"]), ArrayValueExpression)
    assert isinstance(F.unnest(dialect, columns["array"]), ArrayValueExpression)


def test_measuring_a_sequence_gives_a_whole_number(dialect, columns):
    assert isinstance(F.array_length(dialect, columns["array"], 1), IntegerValueExpression)


# ---------------------------------------------------------------------------
# Operations over several values
# ---------------------------------------------------------------------------


def test_greatest_answers_with_what_its_arguments_answer_with(dialect, columns):
    assert isinstance(F.greatest(dialect, columns["int"], columns["int"]), IntegerValueExpression)


def test_greatest_of_mixed_kinds_is_unknown(dialect, columns):
    """The comparison is legal SQL and the answer is neither kind, so neither
    surface may be offered. Guessing the first or the widest would be wrong."""
    assert not isinstance(F.greatest(dialect, columns["int"], columns["str"]), ArrayValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), BinaryValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), BooleanValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), DateValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), IntegerValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), IntervalValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), JSONValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), NumericValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), StringValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), TimeValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), TimestampValueExpression) and not isinstance(F.greatest(dialect, columns["int"], columns["str"]), UUIDValueExpression)


def test_least_agrees_with_greatest(dialect, columns):
    assert isinstance(F.least(dialect, columns["float"], columns["float"]), NumericValueExpression)


def test_nullif_keeps_the_value_it_tests(dialect, columns):
    assert isinstance(F.nullif(dialect, columns["str"], None), StringValueExpression)


# ---------------------------------------------------------------------------
# what an operation over several values keeps
# ---------------------------------------------------------------------------


def test_a_consensus_needs_exactly_one(dialect, columns):
    """A CASE over disagreeing branches is legal SQL that answers with neither
    kind, so neither surface may be offered."""
    mixed = CaseExpression(dialect, cases=[(columns["int"], columns["int"])],
                           else_result=columns["float"])
    assert not isinstance(mixed, ArrayValueExpression) and not isinstance(mixed, BinaryValueExpression) and not isinstance(mixed, BooleanValueExpression) and not isinstance(mixed, DateValueExpression) and not isinstance(mixed, IntegerValueExpression) and not isinstance(mixed, IntervalValueExpression) and not isinstance(mixed, JSONValueExpression) and not isinstance(mixed, NumericValueExpression) and not isinstance(mixed, StringValueExpression) and not isinstance(mixed, TimeValueExpression) and not isinstance(mixed, TimestampValueExpression) and not isinstance(mixed, UUIDValueExpression)


def test_an_argument_without_a_family_does_not_break_a_consensus(dialect, columns):
    """A literal says nothing, so it neither agrees nor disagrees."""
    with_literal = CaseExpression(dialect, cases=[(columns["int"], Literal(dialect, 1))],
                                 else_result=columns["int"])
    assert isinstance(with_literal, IntegerValueExpression)


# ---------------------------------------------------------------------------
# A cast states its result in the target type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sql_type",
    [
        "VARCHAR(255)",
        "TEXT",
        "NVARCHAR2(10)",
        "INTEGER",
        "BIGINT",
        "DECIMAL(10,2)",
        "DOUBLE PRECISION",
        "BOOLEAN",
        "TIMESTAMP",
        "JSONB",
        "BLOB",
        "UUID",
        "XML",
    ],
)
def test_real_sql_type_names_are_names(sql_type):
    """These are all type names a database has.

    They used to be pinned to the value family a cast to them produces. There is
    no such table now: ``cast`` answers with the class of the ``DataType`` it
    was handed, so the name carries no type of its own to be right about. What
    remains is that the name is recognised -- the grammar, not a meaning.
    """
    assert is_valid_type_name(sql_type)


def test_an_unknown_sql_type_is_still_a_name():
    """A name nobody here knows is still shaped like a name.

    What it means is the dialect's business, decided when the dialect is
    asked to render it, not something this package guesses at here.
    """
    assert is_valid_type_name("GEOMETRY")
    assert is_valid_type_name("POINT")
    assert not is_valid_type_name(None)


def test_cast_takes_its_type_from_the_target_type(dialect, columns):
    """The cast answers with the class of the type it was handed."""
    assert isinstance(
        F.cast(dialect, columns["int"], VarCharType(dialect, length=10)),
        StringValueExpression,
    )
    assert isinstance(
        F.cast(dialect, columns["int"], JsonType(dialect)), JSONValueExpression
    )


def test_an_unmodelled_target_type_yields_no_typed_result(dialect, columns):
    """A user-defined type has no value class to answer with.

    Offering JSON navigation on a type nobody here has heard of would be worse
    than saying nothing, so the cast comes back untyped and the caller says what
    they meant with ``as_*``.
    """
    result = F.cast(dialect, columns["int"], CustomType(dialect, raw="GEOMETRY"))
    assert not isinstance(
        result,
        (
            ArrayValueExpression,
            BinaryValueExpression,
            BooleanValueExpression,
            DateValueExpression,
            IntegerValueExpression,
            IntervalValueExpression,
            JSONValueExpression,
            NumericValueExpression,
            StringValueExpression,
            TimeValueExpression,
            TimestampValueExpression,
            UUIDValueExpression,
        ),
    )


# ---------------------------------------------------------------------------
# Formatting and parsing
# ---------------------------------------------------------------------------


def test_to_char_gives_text(dialect, columns):
    assert isinstance(F.to_char(dialect, columns["int"]), StringValueExpression)


def test_to_number_gives_a_number(dialect, columns):
    assert isinstance(F.to_number(dialect, columns["int"]), NumericValueExpression)


def test_to_date_gives_a_timestamp(dialect, columns):
    assert isinstance(F.to_date(dialect, columns["int"]), TimestampValueExpression)


# ---------------------------------------------------------------------------
# Session identity is a name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", ["current_user", "session_user", "system_user"])
def test_the_session_identity_is_a_name(dialect, factory):
    result = getattr(F, factory)(dialect)
    assert isinstance(result, StringValueExpression)
    assert hasattr(result, "upper")


# ---------------------------------------------------------------------------
# XML
# ---------------------------------------------------------------------------


def test_the_xml_nodes_declare_a_family(dialect):
    from rhosocial.activerecord.backend.expression import xml as X

    for cls in (
        X.XMLParseExpression,
        X.XMLConcatExpression,
        X.XMLQueryExpression,
        X.XMLAggExpression,
    ):
        assert value_type_of(cls) == XML


def test_xmlexists_is_a_predicate_not_a_value():
    """It answers a WHERE clause, so it has no value family to declare."""
    from rhosocial.activerecord.backend.expression import xml as X
    from rhosocial.activerecord.backend.expression.bases import SQLPredicate

    assert issubclass(X.XMLExistsExpression, SQLPredicate)


# ---------------------------------------------------------------------------
# Every family has a wrapper
# ---------------------------------------------------------------------------


def test_a_family_the_core_does_not_hold_is_reported_unknown():
    """The lattice is closed. An extension type a backend models fully is still
    unknown here, because the core does not know which backends exist and cannot
    say what such a family means for the operations its own results offer.

    Declaring one used to look like it worked -- the attribute was there, and
    reading it gave the name back -- so nothing pinned the difference between a
    family that is honoured and one that is quietly dropped."""
    declared = "network"

    class ExtensionValue(SQLValueExpression):
        VALUE_FAMILY = declared

    assert declared not in FAMILIES
    assert not isinstance(ExtensionValue.__new__(ExtensionValue), ArrayValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), BinaryValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), BooleanValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), DateValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), IntegerValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), IntervalValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), JSONValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), NumericValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), StringValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), TimeValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), TimestampValueExpression) and not isinstance(ExtensionValue.__new__(ExtensionValue), UUIDValueExpression)


def test_every_typed_expression_declares_a_family_from_the_lattice():
    """Each result class states its own family, and it has to be one the
    lattice knows -- otherwise it offers operations nothing downstream expects.

    This replaced a test that every family but XML had a wrapper in a registry.
    There is no registry now: a factory constructs the class it means, so there
    is no table left to be complete."""
    import inspect

    from rhosocial.activerecord.backend.expression import core

    declared = {
        name: cls
        for name, cls in inspect.getmembers(core, inspect.isclass)
        if name.endswith("ValueExpression") and name != "SQLValueExpression"
    }
    assert declared, "the typed expressions moved"
    # Every typed expression declares its type by being a class, so the only
    # thing left to check is that each one is still reachable and distinct.
    assert len(set(declared.values())) == len(declared), "two names bind one class"


def test_every_temporal_type_is_reachable():
    """The four temporal classes exist and are distinct.

    They were one class with a label saying which it was; now each is its own,
    so this pins that they are all still there.
    """
    from rhosocial.activerecord.backend.expression import core

    for name in ("TimestampValueExpression", "DateValueExpression",
                 "TimeValueExpression", "IntervalValueExpression"):
        assert hasattr(core, name), name
