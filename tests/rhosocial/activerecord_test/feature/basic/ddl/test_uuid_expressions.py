# tests/rhosocial/activerecord_test/feature/basic/ddl/test_uuid_expressions.py
"""UUID value expressions and the ``UUIDSupport`` contract.

Generating a UUID in SQL is a portable *request* with a wildly
non-portable *spelling* — eight backends, eight function names, and SQLite
has none. The expression layer states the request; each dialect fills in a
``UUID_SQL`` table. A dialect that cannot serve a request must say so, and
rendering must then raise with a usable suggestion rather than emit another
backend's function.

Storage is deliberately not involved: that is ``DataType``'s business, and
nothing here reads it.
"""

# tests/rhosocial/activerecord_test/feature/basic/ddl/test_uuid_expressions.py
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.protocols import UUIDSupport
from rhosocial.activerecord.backend.expression import (
    UUIDCastExpression,
    UUIDConstantExpression,
    UUIDGenerationExpression,
    Literal,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

_NIL = "00000000-0000-0000-0000-000000000000"
_MAX = "ffffffff-ffff-ffff-ffff-ffffffffffff"


def _dialect(uuid_sql=None):
    dialect = SQLiteDialect()
    dialect._version = (3, 46, 1)
    if uuid_sql is not None:
        dialect.UUID_SQL = uuid_sql
    return dialect


_FULL = {
    "generation": "GEN_UUID()",
    "constant": {"nil": "X'00'", "max": "X'FF'"},
    "cast": "CAST({inner} AS UUID)",
}


# ---------------------------------------------------------------------------
# Honest absence
# ---------------------------------------------------------------------------


def test_sqlite_satisfies_the_protocol():
    """Being in the protocol is about shape, not about capability."""
    assert isinstance(_dialect(), UUIDSupport)


@pytest.mark.parametrize(
    "probe", ["supports_uuid_generation", "supports_uuid_constant", "supports_uuid_cast"]
)
def test_sqlite_reports_no_uuid_operations(probe):
    """SQLite has no UUID function, so all three must report False."""
    assert getattr(_dialect(), probe)() is False


@pytest.mark.parametrize(
    "factory",
    [
        lambda d: UUIDGenerationExpression(d),
        lambda d: UUIDConstantExpression(d, "nil"),
        lambda d: UUIDCastExpression(d, Literal(d, "x")),
    ],
    ids=["generation", "constant", "cast"],
)
def test_rendering_raises_when_unsupported(factory):
    with pytest.raises(UnsupportedFeatureError):
        factory(_dialect()).to_sql()


def test_generation_suggests_the_python_route():
    """The suggestion must point at something that actually works today."""
    with pytest.raises(UnsupportedFeatureError) as excinfo:
        UUIDGenerationExpression(_dialect()).to_sql()
    assert "uuid.uuid4" in str(excinfo.value)


# ---------------------------------------------------------------------------
# A dialect that implements the operations
# ---------------------------------------------------------------------------


def test_capability_probes_reflect_the_table():
    dialect = _dialect(_FULL)
    assert dialect.supports_uuid_generation() is True
    assert dialect.supports_uuid_constant() is True
    assert dialect.supports_uuid_cast() is True


def test_generation_renders_the_backends_own_function():
    assert UUIDGenerationExpression(_dialect(_FULL)).to_sql() == ("GEN_UUID()", ())


def test_generation_carries_its_alias():
    assert UUIDGenerationExpression(_dialect(_FULL), alias="u").to_sql() == (
        'GEN_UUID() AS "u"',
        (),
    )


@pytest.mark.parametrize("which, expected", [("nil", "X'00'"), ("max", "X'FF'")])
def test_constants_render_per_kind(which, expected):
    assert UUIDConstantExpression(_dialect(_FULL), which).to_sql() == (expected, ())


def test_constant_kind_is_case_insensitive():
    assert UUIDConstantExpression(_dialect(_FULL), "MAX").to_sql() == ("X'FF'", ())


def test_constant_rejects_an_unknown_kind():
    """A typo must not silently render a literal."""
    with pytest.raises(ValueError, match="which must be one of"):
        UUIDConstantExpression(_dialect(_FULL), "middle")


def test_cast_substitutes_the_operand_and_keeps_its_parameters():
    dialect = _dialect(_FULL)
    expr = UUIDCastExpression(dialect, Literal(dialect, "not-a-uuid"))
    assert expr.to_sql() == ("CAST(? AS UUID)", ("not-a-uuid",))


def test_constant_and_cast_stay_unsupported_when_only_generation_is_declared():
    partial = {"generation": "GEN_UUID()"}
    dialect = _dialect(partial)
    assert dialect.supports_uuid_generation() is True
    with pytest.raises(UnsupportedFeatureError, match="UUID constants"):
        UUIDConstantExpression(dialect, "nil").to_sql()
    with pytest.raises(UnsupportedFeatureError, match="UUID cast"):
        UUIDCastExpression(dialect, Literal(dialect, "x")).to_sql()


# ---------------------------------------------------------------------------
# The expressions are ordinary value expressions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [
        lambda d: UUIDGenerationExpression(d),
        lambda d: UUIDConstantExpression(d, "nil"),
        lambda d: UUIDCastExpression(d, Literal(d, "x")),
    ],
    ids=["generation", "constant", "cast"],
)
def test_uuid_expressions_support_comparison_and_aliasing(factory):
    from rhosocial.activerecord.backend.expression import SQLPredicate

    dialect = _dialect(_FULL)
    expr = factory(dialect)
    assert isinstance(expr == factory(dialect), SQLPredicate)
    assert expr.as_("u").alias == "u"


def test_format_methods_are_declared_for_dispatch():
    assert UUIDGenerationExpression(_dialect()).format_method == "format_uuid_generation"
    assert UUIDConstantExpression(_dialect(), "nil").format_method == "format_uuid_constant"
    assert (
        UUIDCastExpression(_dialect(), Literal(_dialect(), "x")).format_method
        == "format_uuid_cast"
    )
