# tests/rhosocial/activerecord_test/feature/backend/test_numeric_value_operations.py
"""A numeric column offers the operations SQL already has for numbers.

The functions existed as free functions in ``functions.math`` and were
unreachable from a column, so ``col.sqrt()`` raised AttributeError while
``sqrt(dialect, col)`` worked. The mixin now forwards to the same factories, so
what these tests pin down is that the wiring is right: the right function name,
the arguments bound rather than inlined, and a result family the next call in
the chain can use.

Family is checked where SQL makes it depend on the operand rather than on the
operation. ``CEIL(numeric)`` is ``numeric`` and ``CEIL(integer)`` is ``integer``
in every backend, so ``ceil`` keeps the operand's family instead of asserting
one -- asserting integer here would have been wrong for every ``float`` column.
"""

import pytest

from rhosocial.activerecord.backend.expression import NumericColumn
from rhosocial.activerecord.backend.expression.value_types import INTEGER, NUMERIC


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

    return DummyDialect()


@pytest.fixture
def price(dialect):
    return NumericColumn(dialect, "price", table="t")


NO_ARGUMENT_OPERATIONS = [
    ("abs", "ABS"),
    ("sign", "SIGN"),
    ("ceil", "CEIL"),
    ("floor", "FLOOR"),
    ("truncate", "TRUNCATE"),
    ("sqrt", "SQRT"),
    ("exp", "EXP"),
    ("log", "LOG"),
    ("sin", "SIN"),
    ("cos", "COS"),
    ("tan", "TAN"),
]

ARGUMENT_OPERATIONS = [
    ("round", (2,), "ROUND"),
    ("power", (2,), "POWER"),
    ("mod", (3,), "MOD"),
    ("log", (2,), "LOG"),
]


class TestOperationsReachTheColumn:
    @pytest.mark.parametrize("method,sql_name", NO_ARGUMENT_OPERATIONS)
    def test_no_argument(self, price, method, sql_name):
        sql, _ = getattr(price, method)().to_sql()
        assert sql.startswith(f"{sql_name}(")

    @pytest.mark.parametrize("method,args,sql_name", ARGUMENT_OPERATIONS)
    def test_with_argument(self, price, method, args, sql_name):
        sql, _ = getattr(price, method)(*args).to_sql()
        assert sql.startswith(f"{sql_name}(")

    @pytest.mark.parametrize("method,sql_name", NO_ARGUMENT_OPERATIONS)
    def test_the_column_is_the_operand(self, price, method, sql_name):
        """Not the dialect or a fresh literal -- the column being asked about."""
        sql, _ = getattr(price, method)().to_sql()
        assert '"t"."price"' in sql


class TestArgumentsAreBound:
    """A number that came from the caller is data, and data gets bound."""

    @pytest.mark.parametrize(
        "method,args", [("round", (2,)), ("power", (3,)), ("mod", (7,))]
    )
    def test_the_argument_is_a_parameter(self, price, method, args):
        sql, params = getattr(price, method)(*args).to_sql()
        assert "?" in sql
        assert args[0] in params


class TestResultFamilies:
    def test_abs_keeps_the_operand_family(self, price):
        """ABS of a double is a double; asserting one family would be wrong."""
        assert price.abs().VALUE_FAMILY == NUMERIC

    def test_sign_is_always_an_integer(self, price):
        assert price.sign().VALUE_FAMILY == INTEGER

    def test_sqrt_is_a_number(self, price):
        assert price.sqrt().VALUE_FAMILY == NUMERIC

    @pytest.mark.parametrize("method", ["ceil", "floor"])
    def test_rounding_keeps_the_operand_family(self, price, method):
        """CEIL(numeric) is numeric in every backend; CEIL(integer) is not."""
        assert getattr(price, method)().VALUE_FAMILY == NUMERIC


class TestChaining:
    def test_a_result_can_be_used_as_an_operand_again(self, price):
        """The reason the family matters: the next call has to be available."""
        sql, _ = price.abs().sqrt().to_sql()
        assert sql.count("SQRT(") == 1
        assert "ABS(" in sql

    def test_an_arithmetic_result_can_be_rounded(self, price):
        sql, _ = (price + 1).round(2).to_sql()
        assert "ROUND(" in sql

    def test_order_of_operations_is_visible_in_the_sql(self, price):
        sql, _ = price.abs().ceil().to_sql()
        assert sql == 'CEIL(ABS("t"."price"))'