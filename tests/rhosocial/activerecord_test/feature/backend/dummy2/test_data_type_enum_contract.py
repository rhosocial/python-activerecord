# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_data_type_enum_contract.py
"""The generic ``enum`` type, and what a backend says when it cannot render it.

``EnumType`` exists in the core and no real backend implemented a formatter for
it, so a model declaring an enumerated field failed everywhere with a message
that named neither the feature nor a way forward. The suggestion is the only
place a backend writes down what it stores instead, so the message has to
carry it.

A backend that *can* render the type renders the values through its own literal
formatter, because that is where each dialect's escaping lives: a value holding
a quote is the case where a hand-rolled f-string of quotes goes wrong.
"""

# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_data_type_enum_contract.py
import pytest

from rhosocial.activerecord.backend.dialect.mixins.data_type import DataTypeMixin
from rhosocial.activerecord.backend.expression.types import EnumType


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

    d = DummyDialect()
    d._version = (1, 0, 0)
    return d


# ---------------------------------------------------------------------------
# The type carries its values
# ---------------------------------------------------------------------------


def test_values_are_required(dialect):
    """An enum with no values is a text field, and saying so is better than
    emitting ``ENUM()``."""
    with pytest.raises(ValueError, match="requires values"):
        EnumType(dialect)


def test_an_empty_value_list_is_rejected(dialect):
    with pytest.raises(ValueError, match="at least one value"):
        EnumType(dialect, [])


def test_values_survive_as_a_tuple(dialect):
    assert EnumType(dialect, ["a", "b"]).values == ("a", "b")


# ---------------------------------------------------------------------------
# A backend that renders it
# ---------------------------------------------------------------------------


def test_values_are_rendered_in_order(dialect):
    assert dialect.format_data_type(EnumType(dialect, ["draft", "live"]))[0] == (
        "ENUM('draft','live')"
    )


def test_a_value_containing_a_quote_is_escaped(dialect):
    """The reason to go through format_literal rather than wrapping in quotes.

    ``ENUM('o'brien')`` is not valid SQL; doubling the quote is.
    """
    sql, _ = dialect.format_data_type(EnumType(dialect, ["o'brien"]))
    assert sql == "ENUM('o''brien')"


def test_a_rendered_enum_is_an_advertised_type(dialect):
    """A formatter the dialect does not advertise would be a capability
    claimed in one place and absent in the other."""
    assert "enum" in dialect.supports_data_types()


# ---------------------------------------------------------------------------
# A backend that cannot render it
# ---------------------------------------------------------------------------


class Narrow(DataTypeMixin):
    """A dialect that advertises no enum formatter and suggests nothing.

    Renders one type, so a test can tell "refused because unsupported" from
    "refused because the advice path is broken".
    """

    def format_data_type_varchar(self, data_type):
        return f"VARCHAR({data_type.length})", ()

    def suggested_data_types(self):
        return {}


class Suggester(Narrow):
    """A dialect that cannot render it but knows what it stores instead."""

    def suggested_data_types(self):
        from rhosocial.activerecord.backend.expression.types import VarCharType

        return {"enum": VarCharType}


def test_an_unrenderable_type_is_a_type_error(dialect):
    with pytest.raises(TypeError, match="does not support the generic type 'enum'"):
        Narrow().format_data_type(EnumType(dialect, ["a"]))


def test_the_refusal_names_the_substitute(dialect):
    """Otherwise the caller is told it is unsupported and nothing else, which
    is the same as not knowing."""
    with pytest.raises(TypeError) as excinfo:
        Suggester().format_data_type(EnumType(dialect, ["a"]))
    message = str(excinfo.value)
    assert "VarCharType" in message, message
    assert "how this backend stores the same meaning" in message, message


def test_no_substitute_means_no_advice(dialect):
    with pytest.raises(TypeError) as excinfo:
        Narrow().format_data_type(EnumType(dialect, ["a"]))
    message = str(excinfo.value)
    assert "It suggests" not in message, message
    assert "Use a type this backend supports" in message, message


def test_a_type_the_dialect_renders_is_not_rejected(dialect):
    """The advice path must not swallow types the dialect does handle."""
    from rhosocial.activerecord.backend.expression.types import VarCharType

    assert Suggester().format_data_type(VarCharType(dialect, 10))[0]
