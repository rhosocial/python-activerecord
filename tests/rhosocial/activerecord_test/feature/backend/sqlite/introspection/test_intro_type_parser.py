# tests/rhosocial/activerecord_test/feature/backend/sqlite/introspection/test_intro_type_parser.py
"""SQLiteTypeParser: read-direction type spelling parsing (introspection-only).

The parser is a backend-local, temporary helper under the SQLite introspection
namespace -- not a dialect protocol member. These tests pin the affinity rules
and canonicality that the introspector relies on.
"""
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression import types as sq
from rhosocial.activerecord.backend.impl.sqlite.introspection.type_parser import SQLiteTypeParser


def _parser():
    return SQLiteTypeParser(SQLiteDialect(version=(3, 53, 0)))


def test_affinity_parsing_covers_core_spellings():
    p = _parser()
    for raw, expected in (
        ("INT1", sq.SQLiteIntegerType),
        ("CHARACTER", sq.SQLiteTextType),
        ("DEC", sq.SQLiteNumericType),
        ("BOOL", sq.SQLiteNumericType),
        ("DOUBLE PRECISION", sq.SQLiteRealType),
        ("BYTEA", sq.SQLiteBlobType),
        ("BIGINT", sq.SQLiteIntegerType),
        ("CHAR", sq.SQLiteTextType),
    ):
        assert type(p.parse(raw)) is expected, f"{raw!r} should parse to {expected.__name__}"


def test_length_and_precision_are_carried():
    p = _parser()
    assert p.parse("VARCHAR(255)").length == 255
    assert p.parse("DECIMAL(10, 2)").precision == 10


def test_unknown_type_is_custom():
    from rhosocial.activerecord.backend.expression.types import CustomType
    assert isinstance(_parser().parse("SOME_UNKNOWN_TYPE"), CustomType)
