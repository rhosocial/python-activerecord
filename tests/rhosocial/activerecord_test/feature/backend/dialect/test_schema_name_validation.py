# tests/rhosocial/activerecord_test/feature/backend/dialect/test_schema_name_validation.py

"""``SchemaSupport.validate_schema_name`` -- the one place a namespace is judged.

An expression only collects parameters. At construction its parameters may still
be incomplete and its dialect may not be settled, so the value is stored as
given; strict checking belongs to the dialect and runs while rendering, which is
the first moment the schema is actually used.

So this module tests the dialect method once, rather than repeating the same four
cases for each of the forty-odd expressions that carry a ``schema_name``. What
varies between expressions is which formatter reaches the check, and that is
covered by asserting each rendering path rejects a bad value -- one case per
path, not per expression.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins.ddl_schema import SchemaMixin
from rhosocial.activerecord.backend.dialect.protocols import SchemaSupport
from rhosocial.activerecord.backend.expression.core import (
    Column,
    QualifiedIdentifierExpression,
    TableExpression,
    WildcardExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    DropViewExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class Namespaced(SQLiteDialect):
    """SQLite that claims a namespace, so the accepts path can be exercised.

    Everything else about the dialect is unchanged; only ``supports_schema``
    differs, which is the single switch the validation consults.
    """

    def supports_schema(self) -> bool:
        return True


@pytest.fixture
def plain():
    return SQLiteDialect()


@pytest.fixture
def namespaced():
    return Namespaced()


class TestProtocolAndImplementationPair:
    def test_mixin_implements_the_protocol(self, plain):
        assert isinstance(plain, SchemaSupport)

    def test_the_method_is_part_of_the_protocol(self):
        assert "validate_schema_name" in SchemaSupport.__protocol_attrs__
        assert hasattr(SchemaMixin, "validate_schema_name")

    def test_returns_true_rather_than_false(self, namespaced):
        expr = TableExpression(namespaced, "users", schema_name="app")
        assert namespaced.validate_schema_name(expr) is True

    def test_none_is_unqualified_and_accepted(self, namespaced, plain):
        assert namespaced.validate_schema_name(
            TableExpression(namespaced, "users")
        ) is True
        assert plain.validate_schema_name(TableExpression(plain, "users")) is True


class TestRejectedValues:
    @pytest.mark.parametrize("value", ["", "   ", "\t\n"])
    def test_blank_is_a_mistake_not_a_spelling_of_unqualified(
        self, namespaced, value
    ):
        expr = TableExpression(namespaced, "users", schema_name=value)
        with pytest.raises(ValueError) as exc:
            expr.to_sql()
        assert "non-empty" in str(exc.value)
        assert "use None" in str(exc.value), (
            "the message has to say what to write instead, or the caller "
            f"reaches for the empty string again: {exc.value}"
        )

    @pytest.mark.parametrize("value", [123, 1.5, [], object()])
    def test_non_string_is_rejected_before_quoting(self, namespaced, value):
        expr = TableExpression(namespaced, "users", schema_name=value)
        with pytest.raises(ValueError) as exc:
            expr.to_sql()
        assert "must be a string or None" in str(exc.value)

    def test_a_dialect_without_namespaces_refuses_the_value(self, plain):
        expr = TableExpression(plain, "users", schema_name="app")
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "no namespace" in str(exc.value)


class TestEveryRenderingPathJudges:
    """One case per path, not one per expression.

    ``format_table`` and ``format_column`` are the chokepoints most statements
    reach, but a few render a qualified name on their own -- a wildcard and a
    bare qualified identifier both do. Each of those needs its own call to
    ``validate_schema_name``, and a path that forgot would silently accept an
    empty schema again.
    """

    @pytest.mark.parametrize(
        "build",
        [
            pytest.param(lambda d: TableExpression(d, "users", schema_name=""), id="table"),
            pytest.param(
                lambda d: Column(d, "id", table="users", schema_name=""), id="column"
            ),
            pytest.param(
                lambda d: WildcardExpression(d, table="users", schema_name=""),
                id="wildcard",
            ),
            pytest.param(
                lambda d: QualifiedIdentifierExpression(
                    d, schema_name="", name="users"
                ),
                id="qualified-identifier",
            ),
            pytest.param(
                lambda d: DropViewExpression(d, "v_users", schema_name=""),
                id="drop-view",
            ),
        ],
    )
    def test_path_rejects_an_empty_schema(self, namespaced, build):
        with pytest.raises(ValueError) as exc:
            build(namespaced).to_sql()
        assert "non-empty" in str(exc.value), exc.value


class TestConstructionDoesNotJudge:
    """The half of the contract that is easy to forget.

    If construction validated, an expression built before its parameters were
    settled would fail for a reason that has nothing to do with the statement
    the caller wanted.
    """

    @pytest.mark.parametrize("value", ["", "   ", 123])
    def test_value_is_stored_verbatim(self, plain, value):
        expr = DropViewExpression(plain, "v_users", schema_name=value)
        assert expr.schema_name == value

    def test_a_dialect_without_namespaces_still_accepts_construction(self, plain):
        expr = TableExpression(plain, "users", schema_name="app")
        assert expr.schema_name == "app"
