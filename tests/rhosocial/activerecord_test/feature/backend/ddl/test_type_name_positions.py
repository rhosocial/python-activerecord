# tests/rhosocial/activerecord_test/feature/backend/ddl/test_type_name_positions.py
"""A type position holds a type, and a name is a name.

Three positions take a type: XMLSERIALIZE's target type, an XMLTABLE
column's type, and ALTER COLUMN ... SET DATA TYPE's type.  Each used to carry
a raw string, guarded only by a character class that neither matched what the
engines accept nor kept the value inside its syntactic position --
``TEXT AS (SELECT 1`` passed it.

The rule these cases pin:

* a position holds a type node, and the dialect renders it in its own
  spelling;
* a name the framework does not model becomes the framework's name node, whose
  name the grammar validates -- a type position cannot take a bound
  parameter, so what lands there is code, not data;
* a value that is not a type name is **refused**, not rendered.

Whether the type *exists* is the server's answer, and the server gives it:
``mytype`` is rendered as it was written, and whether PostgreSQL has that
type is PostgreSQL's business.
"""

import pytest

from rhosocial.activerecord.backend.expression import Literal
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AlterColumnAction,
)
from rhosocial.activerecord.backend.expression.type_name import (
    InvalidTypeNameError,
)
from rhosocial.activerecord.backend.expression.types import (
    CustomType,
    IntegerType,
    TextType,
    VarCharType,
)
from rhosocial.activerecord.backend.expression.xml import (
    XMLSerializeExpression,
    XMLTableColumn,
    XMLTableExpression,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

#: Values that are not a type name. Each of these passed the old character
#: class, and each is a way of ending the type and starting something else.
NOT_A_TYPE_NAME = (
    "TEXT AS (SELECT 1",
    "TEXT) , (SELECT password FROM users",
    "TEXT, (SELECT 1)",
    "TEXT UNION SELECT 1",
    "(SELECT 1)",
    "TEXT; DROP TABLE t",
    "TEXT'",
    'TEXT"',
    "TEXT/*comment*/",
)


@pytest.fixture
def dialect():
    return DummyDialect()


def _serialize(dialect, target_type):
    return dialect.format_xmlserialize_expression(
        XMLSerializeExpression(dialect, Literal(dialect, "x"), target_type)
    )[0]


def _xmltable(dialect, data_type):
    return dialect.format_xmltable_expression(
        XMLTableExpression(
            dialect,
            row_pattern=Literal(dialect, "x"),
            columns=[XMLTableColumn(name="c", data_type=data_type)],
        )
    )[0]


def _set_data_type(dialect, new_value):
    return dialect.format_alter_column_action(
        AlterColumnAction(dialect, "c", "SET DATA TYPE", new_value=new_value)
    )[0]


class TestThePositionsTakeAType:
    """A name or a node, and a type comes out."""

    @pytest.mark.parametrize("name", ["TEXT", "VARCHAR(100)", "INTEGER"])
    def test_a_name_renders_as_a_type(self, dialect, name):
        assert name in _serialize(dialect, name)

    def test_a_node_renders_as_a_type(self, dialect):
        assert "TEXT" in _serialize(dialect, TextType(dialect))
        assert "INTEGER" in _serialize(dialect, IntegerType(dialect))
        assert "VARCHAR(100)" in _serialize(dialect, VarCharType(dialect, 100))

    def test_a_name_the_framework_does_not_model_is_kept_verbatim(self, dialect):
        """An extension type is the server's to accept, not the framework's."""
        assert "mytype" in _serialize(dialect, "mytype")
        assert "probe.mytype" in _serialize(dialect, "probe.mytype")

    def test_a_custom_type_node_renders_its_name(self, dialect):
        assert "mytype" in _serialize(dialect, CustomType(dialect, raw="mytype"))

    def test_the_other_two_positions_take_a_type_too(self, dialect):
        assert "INTEGER" in _xmltable(dialect, "INTEGER")
        assert "INTEGER" in _set_data_type(dialect, "INTEGER")
        assert "INTEGER" in _xmltable(dialect, IntegerType(dialect))
        assert "INTEGER" in _set_data_type(dialect, IntegerType(dialect))


class TestThePositionsRefuseAValueThatIsNotAType:
    """The old character class let these through."""

    @pytest.mark.parametrize("value", NOT_A_TYPE_NAME)
    def test_xmlserialize_refuses_it(self, dialect, value):
        with pytest.raises(InvalidTypeNameError):
            _serialize(dialect, value)

    @pytest.mark.parametrize("value", NOT_A_TYPE_NAME)
    def test_xmltable_refuses_it(self, dialect, value):
        with pytest.raises(InvalidTypeNameError):
            _xmltable(dialect, value)

    @pytest.mark.parametrize("value", NOT_A_TYPE_NAME)
    def test_alter_column_refuses_it(self, dialect, value):
        with pytest.raises(InvalidTypeNameError):
            _set_data_type(dialect, value)

    def test_a_value_that_is_neither_a_name_nor_a_node_is_refused(self, dialect):
        with pytest.raises(TypeError):
            _serialize(dialect, 42)
        with pytest.raises(TypeError):
            _set_data_type(dialect, object())
