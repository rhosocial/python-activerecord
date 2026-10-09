# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_type_spelling_parse.py
"""``parse_type`` must cover every spelling and be canonical (D8).

Two rules, and they are the reason this file exists.

**Coverage.** Every entry of every core ``SPELLINGS`` tuple is a name the
framework itself claims to understand. A ``parse_type`` that answers
``CustomType`` for one of them is saying "I have no type called ``int1``" — and
then writing the raw text back, which is what a ``CustomType`` does. That is
worse than useless on a column the framework declared itself: introspection
reports a name the framework owns as a vendor-specific type.

**Canonicality.** One concept in, exactly one class out, carrying the spelling it
was written with. Not two spellings of one type coming back as two classes (a
second class per synonym is exactly what ``SPELLINGS`` exists to prevent), and
not ``character varying`` — variable length — coming back as the fixed-length
type, which would make the differ report a change that is not there.

Both rules are checked here over **every** core spelling on **every** core
dialect, by walking the classes rather than a hand-written list, so a new
concept with a new spelling cannot be added without this test noticing.
"""

import inspect

import pytest

from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BooleanType,
    CharType,
    CustomType,
    DataType,
    DecimalType,
    DoubleType,
    IntegerType,
    SmallIntType,
    TextType,
    TinyIntType,
    VarCharType,
)

_CORE_TYPES_PREFIX = "rhosocial.activerecord.backend.expression.types"

#: The core dialects, by id. Both ship in this package and neither needs a
#: connection, so a coverage rule stated here is stated about core rather than
#: about one backend's opinion.
_DIALECTS = {
    "dummy": "rhosocial.activerecord.backend.impl.dummy.dialect:DummyDialect",
    "sqlite": "rhosocial.activerecord.backend.impl.sqlite.dialect:SQLiteDialect",
}

#: SQLite stores by *affinity*, not by type name, so several concepts collapse
#: into one stored class — and they must, because the database does not tell them
#: apart. This is the one place a core dialect's answer to a spelling is not the
#: concept class, and it is stated rather than inferred so that a new collapse
#: has to be declared here:
#:
#:   ``INTEGER`` affinity — INT, TINYINT, SMALLINT, BIGINT, INT1: one cell.
#:   ``TEXT``    affinity — TEXT, CHAR, VARCHAR, CHARACTER VARYING, CLOB: one
#:                            cell, so a fixed-length and a variable-length
#:                            declaration are the same column to SQLite.
#:   ``REAL``    affinity — REAL, FLOAT, DOUBLE, DOUBLE PRECISION: one cell.
#:   ``NUMERIC`` affinity — DECIMAL, NUMERIC, DEC, BOOLEAN, BOOL and the
#:                            temporal types: one cell.
#:
#: ``SQLiteNumericType`` derives from no core concept, because that affinity
#: spans three families at once; what it *is* here is the storage each of those
#: concepts has on this backend, which is the only thing a parse of a spelling
#: can honestly be.
_AFFINITY_STORAGE = {
    "sqlite": (),
}


def _dialects():
    """``{id: dialect instance}`` for every core dialect that imports."""
    import importlib

    found = {}
    for dialect_id, target in _DIALECTS.items():
        module_path, class_name = target.split(":")
        module = importlib.import_module(module_path)
        dialect_class = getattr(module, class_name)
        found[dialect_id] = (
            dialect_class() if dialect_id == "dummy"
            else dialect_class(version=(3, 45, 0))
        )
    return found


def _sqlite_affinity_classes():
    """``{core name: the SQLite class that stands in for it}``, declared here
    rather than discovered, because the affinity model is a fact about SQLite
    and not something a lookup should be able to change silently."""
    from rhosocial.activerecord.backend.impl.sqlite.expression import types as sq

    return {
        IntegerType.name: sq.SQLiteIntegerType,
        TinyIntType.name: sq.SQLiteIntegerType,
        SmallIntType.name: sq.SQLiteIntegerType,
        BigIntType.name: sq.SQLiteIntegerType,
        CharType.name: sq.SQLiteTextType,
        VarCharType.name: sq.SQLiteTextType,
        TextType.name: sq.SQLiteTextType,
        DoubleType.name: sq.SQLiteRealType,
        DecimalType.name: sq.SQLiteNumericType,
        BooleanType.name: sq.SQLiteNumericType,
    }


#: Per dialect, the extra classes a concept may legitimately parse to because
#: that backend's storage collapses them. Empty for a dialect that keeps the
#: concepts apart.
_COLLAPSED_STORAGE = {"sqlite": _sqlite_affinity_classes(), "dummy": {}}


def _concrete_core_types():
    """Every concrete core ``DataType`` — the concepts the framework models."""
    seen = set()
    stack = [DataType]
    while stack:
        klass = stack.pop()
        if klass in seen:
            continue
        seen.add(klass)
        stack.extend(klass.__subclasses__())
    return sorted(
        (
            klass for klass in seen
            if not inspect.isabstract(klass)
            and klass.__module__.startswith(_CORE_TYPES_PREFIX)
        ),
        key=lambda klass: klass.name or "",
    )


def _spellings():
    """``(concept, spelling)`` for every entry of every core ``SPELLINGS``."""
    return [
        (klass, spelling)
        for klass in _concrete_core_types()
        for spelling in klass.SPELLINGS
    ]


def _cases():
    return [
        (klass.__name__, spelling)
        for klass, spelling in _spellings()
    ]


_DIALECT_IDS = sorted(_DIALECTS)
_CASES = _cases()
_COLLAPSED_IDS = sorted(_COLLAPSED_STORAGE)


def test_the_walk_finds_every_spellinged_core_type():
    """The enumeration this file rests on must not be vacuous.

    If a new core type declared a spelling and this walk stopped finding it, the
    tests below would pass while checking nothing.
    """
    concepts = {klass for klass, _ in _spellings()}
    assert len(concepts) >= 11, (
        f"expected the eleven synonym-bearing core types, found "
        f"{sorted(k.__name__ for k in concepts)}"
    )
    assert len(_CASES) > len(concepts), "a concept must contribute its other spellings too"
    for concept in concepts:
        assert concept.SPELLINGS[0] == concept.name or concept.SPELLINGS, (
            f"{concept.__name__}: SPELLINGS should list the canonical spelling "
            f"first, got {concept.SPELLINGS!r}"
        )


@pytest.mark.parametrize("dialect_id", _DIALECT_IDS)
@pytest.mark.parametrize("concept_name,spelling", _CASES,
                         ids=[f"{c}-{s}" for c, s in _CASES])
def test_every_spelling_is_recognised(dialect_id, concept_name, spelling):
    """A name in a core ``SPELLINGS`` tuple is never an unrecognised type.

    ``CustomType`` means "the framework has no class for this name", and it
    renders the raw text back. For ``INT1`` — which ``TinyIntType`` declares — that
    turns a type the framework owns into a vendor-specific one on every
    introspection round trip.
    """
    dialect = _dialects()[dialect_id]
    parsed = dialect.parse_type(spelling.upper())
    assert not isinstance(parsed, CustomType), (
        f"{dialect_id}: {concept_name} spells itself {spelling!r} and this "
        f"dialect parsed it as an unrecognised type ({parsed.raw!r}). Every "
        f"entry of every core SPELLINGS must parse to a type."
    )


@pytest.mark.parametrize("dialect_id", _DIALECT_IDS)
@pytest.mark.parametrize("concept_name,spelling", _CASES,
                         ids=[f"{c}-{s}" for c, s in _CASES])
def test_every_spelling_reaches_its_own_concept(dialect_id, concept_name, spelling):
    """The parse lands on this concept, or on the storage this dialect uses for it.

    Not "some type in the same family": the concept itself, except where a
    dialect's storage genuinely cannot tell two concepts apart — and then only
    for the collapses declared in ``_COLLAPSED_STORAGE``.
    """
    concept = next(k for k, _ in _spellings() if k.__name__ == concept_name)
    dialect = _dialects()[dialect_id]
    parsed = dialect.parse_type(spelling.upper())
    collapsed = _COLLAPSED_STORAGE[dialect_id]
    allowed = tuple(
        klass for name, klass in collapsed.items() if name == concept.name
    )
    assert isinstance(parsed, concept) or type(parsed) in allowed, (
        f"{dialect_id}: {concept_name} spelled {spelling!r} parsed as "
        f"{type(parsed).__name__}, which is neither the concept nor a storage "
        f"class this dialect declares for it"
    )


@pytest.mark.parametrize("dialect_id", _DIALECT_IDS)
@pytest.mark.parametrize("concept_name", sorted({c for c, _ in _CASES}))
def test_spellings_of_one_concept_parse_to_one_class(dialect_id, concept_name):
    """Two spellings of one type must not come back as two classes.

    That is the whole reason ``SPELLINGS`` is a tuple on the class: a second
    class per synonym would make ``parse_type`` disagree with itself about what a
    column is, and the differ would report a change on a column nobody touched.
    """
    dialect = _dialects()[dialect_id]
    parsed = [
        type(dialect.parse_type(spelling.upper()))
        for concept, spelling in _spellings()
        if concept.__name__ == concept_name
    ]
    assert len(set(parsed)) == 1, (
        f"{dialect_id}: {concept_name} parses to {sorted(k.__name__ for k in set(parsed))}"
    )


@pytest.mark.parametrize("dialect_id", _COLLAPSED_IDS)
def test_character_varying_is_never_the_fixed_length_type(dialect_id):
    """``CHARACTER VARYING`` is the variable-length concept, not ``CHAR``.

    Both spellings start with ``CHARACTER``, so a parser that matches the prefix
    and stops gets this wrong for one of the two — and the two are different
    storage, so the error is a false schema change rather than a cosmetic one.
    """
    dialect = _dialects()[dialect_id]
    varying = dialect.parse_type("CHARACTER VARYING")
    fixed = dialect.parse_type("CHARACTER")
    assert not isinstance(varying, CharType), (
        f"{dialect_id}: 'character varying' parsed as the fixed-length "
        f"{type(varying).__name__}"
    )
    assert not isinstance(fixed, VarCharType), (
        f"{dialect_id}: 'character' parsed as the variable-length "
        f"{type(fixed).__name__}"
    )


def test_dummy_carries_the_spelling_it_was_parsed_from():
    """A dialect that keeps the concepts apart reports the spelling it read.

    ``spelling`` is deliberately not part of a type's identity, but it is how the
    type was written, and the formatters read it: a parser that dropped it would
    silently turn a caller's ``bool`` into a ``boolean`` request.
    """
    dialect = _dialects()["dummy"]
    for concept, spelling in _spellings():
        parsed = dialect.parse_type(spelling.upper())
        assert getattr(parsed, "spelling", None) == spelling, (
            f"{concept.__name__}: parsed from {spelling!r} as "
            f"{type(parsed).__name__}(spelling={getattr(parsed, 'spelling', None)!r})"
        )


def test_a_number_the_type_cannot_carry_is_not_silently_dropped():
    """``INT(11)`` is a display width no core type models, so it is not ``INT``.

    Reporting it as ``IntegerType`` would claim the width is gone; reporting it as
    the raw text says what it is and lets the caller decide.
    """
    dialect = _dialects()["dummy"]
    parsed = dialect.parse_type("INT(11)")
    assert isinstance(parsed, CustomType)
    assert parsed.raw == "INT(11)"


def test_sqlite_keeps_affinity_parsing_and_now_covers_the_core_spellings():
    """SQLite parses by affinity, and every core spelling finds its affinity.

    The affinity classes are the honest answer for a backend that stores by
    affinity — but the four spellings that used to miss every group and fall
    through to ``CustomType`` (``INT1``, ``CHARACTER``, ``DEC``, ``BOOL``) now
    reach the affinity SQLite has always given them.
    """
    dialect = _dialects()["sqlite"]
    from rhosocial.activerecord.backend.impl.sqlite.expression import types as sq

    for raw, expected in (
        ("INT1", sq.SQLiteIntegerType),
        ("CHARACTER", sq.SQLiteTextType),
        ("DEC", sq.SQLiteNumericType),
        ("BOOL", sq.SQLiteNumericType),
        ("DOUBLE PRECISION", sq.SQLiteRealType),
        ("BYTEA", sq.SQLiteBlobType),
    ):
        assert type(dialect.parse_type(raw)) is expected, (
            f"sqlite: {raw!r} should parse to {expected.__name__}"
        )