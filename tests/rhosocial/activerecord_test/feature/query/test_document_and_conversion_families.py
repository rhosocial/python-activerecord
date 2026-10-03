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
from rhosocial.activerecord.backend.expression.value_types import (
    ARRAY,
    BOOLEAN,
    DATETIME,
    FAMILIES,
    INTEGER,
    JSON,
    NUMERIC,
    STRING,
    XML,
    family_for_sql_type,
    value_type_of,
)
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
    assert value_type_of(F.json_extract(dialect, columns["json"], Literal(dialect, "$.a"))) == JSON


def test_double_arrow_extraction_gives_text(dialect, columns):
    """`->>` is a narrowing: a document becomes a string and cannot widen back."""
    assert value_type_of(F.json_extract_text(dialect, columns["json"], "$.a")) == STRING


def test_a_built_document_is_a_document(dialect, columns):
    assert value_type_of(F.json_build_object(dialect, "k", 1)) == JSON
    assert value_type_of(F.json_array_elements(dialect, columns["json"])) == JSON


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
    assert value_type_of(text) == STRING
    assert text.to_sql()[0].endswith("->>'$.a'")


# ---------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------


def test_a_sequence_is_a_sequence(dialect, columns):
    assert value_type_of(F.unnest(dialect, columns["array"])) == ARRAY
    assert isinstance(F.unnest(dialect, columns["array"]), ArrayValueExpression)


def test_measuring_a_sequence_gives_a_whole_number(dialect, columns):
    assert value_type_of(F.array_length(dialect, columns["array"], 1)) == INTEGER


# ---------------------------------------------------------------------------
# Operations over several values
# ---------------------------------------------------------------------------


def test_greatest_answers_with_what_its_arguments_answer_with(dialect, columns):
    assert value_type_of(F.greatest(dialect, columns["int"], columns["int"])) == INTEGER


def test_greatest_of_mixed_kinds_is_unknown(dialect, columns):
    """The comparison is legal SQL and the answer is neither kind, so neither
    surface may be offered. Guessing the first or the widest would be wrong."""
    assert value_type_of(F.greatest(dialect, columns["int"], columns["str"])) is None


def test_least_agrees_with_greatest(dialect, columns):
    assert value_type_of(F.least(dialect, columns["float"], columns["float"])) == NUMERIC


def test_nullif_keeps_the_value_it_tests(dialect, columns):
    assert value_type_of(F.nullif(dialect, columns["str"], None)) == STRING


# ---------------------------------------------------------------------------
# what an operation over several values keeps
# ---------------------------------------------------------------------------


def test_a_consensus_needs_exactly_one(dialect, columns):
    """A CASE over disagreeing branches is legal SQL that answers with neither
    kind, so neither surface may be offered."""
    mixed = CaseExpression(dialect, cases=[(columns["int"], columns["int"])],
                           else_result=columns["float"])
    assert value_type_of(mixed) is None


def test_an_argument_without_a_family_does_not_break_a_consensus(dialect, columns):
    """A literal says nothing, so it neither agrees nor disagrees."""
    with_literal = CaseExpression(dialect, cases=[(columns["int"], Literal(dialect, 1))],
                                 else_result=columns["int"])
    assert value_type_of(with_literal) == INTEGER


# ---------------------------------------------------------------------------
# A cast states its result in the target type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sql_type, expected",
    [
        ("VARCHAR(255)", STRING),
        ("TEXT", STRING),
        ("NVARCHAR2(10)", STRING),
        ("INTEGER", INTEGER),
        ("BIGINT", INTEGER),
        ("DECIMAL(10,2)", NUMERIC),
        ("DOUBLE PRECISION", NUMERIC),
        ("BOOLEAN", BOOLEAN),
        ("TIMESTAMP", DATETIME),
        ("JSONB", JSON),
        ("BLOB", "binary"),
        ("UUID", "uuid"),
        ("XML", XML),
    ],
)
def test_sql_type_names_map_to_families(sql_type, expected):
    assert family_for_sql_type(sql_type) == expected


def test_an_unknown_sql_type_is_not_guessed():
    """Offering JSON navigation on a type nobody has heard of is worse than
    saying nothing."""
    assert family_for_sql_type("GEOMETRY") is None
    assert family_for_sql_type("POINT") is None
    assert family_for_sql_type(None) is None


def test_cast_takes_its_family_from_the_target_type(dialect, columns):
    assert value_type_of(F.cast(dialect, columns["int"], VarCharType(dialect, length=10))) == STRING
    assert value_type_of(F.cast(dialect, columns["int"], JsonType(dialect))) == JSON
    assert value_type_of(F.cast(dialect, columns["int"], CustomType(dialect, raw="GEOMETRY"))) is None


# ---------------------------------------------------------------------------
# Formatting and parsing
# ---------------------------------------------------------------------------


def test_to_char_gives_text(dialect, columns):
    assert value_type_of(F.to_char(dialect, columns["int"])) == STRING


def test_to_number_gives_a_number(dialect, columns):
    assert value_type_of(F.to_number(dialect, columns["int"])) == NUMERIC


def test_to_date_gives_a_timestamp(dialect, columns):
    assert value_type_of(F.to_date(dialect, columns["int"])) == DATETIME


# ---------------------------------------------------------------------------
# Session identity is a name
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", ["current_user", "session_user", "system_user"])
def test_the_session_identity_is_a_name(dialect, factory):
    result = getattr(F, factory)(dialect)
    assert value_type_of(result) == STRING
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
    assert value_type_of(ExtensionValue.__new__(ExtensionValue)) is None


def test_every_typed_expression_declares_a_family_from_the_lattice():
    """Each result class states its own family, and it has to be one the
    lattice knows -- otherwise it offers operations nothing downstream expects.

    This replaced a test that every family but XML had a wrapper in a registry.
    There is no registry now: a factory constructs the class it means, so there
    is no table left to be complete."""
    import inspect

    from rhosocial.activerecord.backend.expression import core

    declared = {
        name: getattr(cls, "VALUE_FAMILY", None)
        for name, cls in inspect.getmembers(core, inspect.isclass)
        if name.endswith("ValueExpression") and name != "SQLValueExpression"
    }
    assert declared, "the typed expressions moved"
    assert {f for f in declared.values() if f not in FAMILIES} == set()
    # The base declares none on purpose: it is what an unmodelled result is.
    assert getattr(core.SQLValueExpression, "VALUE_FAMILY", None) is None
