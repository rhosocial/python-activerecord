# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_operators.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, Subquery
)
from rhosocial.activerecord.backend.expression.operators import (
    SQLOperation, BinaryExpression, UnaryExpression, RawSQLExpression, BinaryArithmeticExpression
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLOperation:
    """Tests for SQLOperation representing generic SQL operations."""

    def test_sql_operation_with_operands(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test SQLOperation with multiple operands."""
        operand1 = Literal(sqlite_dialect_3_8_0, "value1")
        operand2 = Column(sqlite_dialect_3_8_0, "column_name")

        sql_op = SQLOperation(sqlite_dialect_3_8_0, "CUSTOM_OP", operand1, operand2)

        sql, params = sql_op.to_sql()

        assert "CUSTOM_OP(" in sql
        assert params == ("value1",)

    def test_sql_operation_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic SQLOperation functionality."""
        operand1 = Literal(sqlite_dialect_3_8_0, "value")
        sql_op = SQLOperation(sqlite_dialect_3_8_0, "UPPER", operand1)
        sql, params = sql_op.to_sql()
        assert sql == "UPPER(?)"
        assert params == ("value",)


class TestBinaryExpression:
    """Tests for BinaryExpression representing binary operations."""

    def test_binary_expression_concatenation(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test binary expression with concatenation operator."""
        left = Column(sqlite_dialect_3_8_0, "first_name")
        right = Column(sqlite_dialect_3_8_0, "last_name")
        binary_expr = BinaryExpression(sqlite_dialect_3_8_0, "||", left, right)

        sql, params = binary_expr.to_sql()
        assert sql == '"first_name" || "last_name"'
        assert params == ()

    def test_binary_expression_with_literal(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test binary expression with a literal operand."""
        left = Column(sqlite_dialect_3_8_0, "price")
        right = Literal(sqlite_dialect_3_8_0, 100)
        binary_expr = BinaryExpression(sqlite_dialect_3_8_0, ">", left, right)

        sql, params = binary_expr.to_sql()
        assert sql == '"price" > ?'
        assert params == (100,)


class TestUnaryExpression:
    """Tests for UnaryExpression representing unary operations."""

    def test_unary_not_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test unary NOT expression."""
        operand = Column(sqlite_dialect_3_8_0, "active")
        unary_expr = UnaryExpression(sqlite_dialect_3_8_0, "NOT", operand)

        sql, params = unary_expr.to_sql()
        assert sql == "NOT \"active\""
        assert params == ()

    def test_unary_negation_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test unary negation expression."""
        operand = Column(sqlite_dialect_3_8_0, "balance")
        unary_expr = UnaryExpression(sqlite_dialect_3_8_0, "-", operand, pos='before')

        sql, params = unary_expr.to_sql()
        assert sql == "- \"balance\""
        assert params == ()


class TestBinaryArithmeticExpression:
    """Tests for BinaryArithmeticExpression representing arithmetic operations."""

    def test_addition_arithmetic_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test addition arithmetic expression."""
        left = Column(sqlite_dialect_3_8_0, "price")
        right = Literal(sqlite_dialect_3_8_0, 10)
        arithmetic_expr = BinaryArithmeticExpression(sqlite_dialect_3_8_0, "+", left, right)

        sql, params = arithmetic_expr.to_sql()
        assert sql == '"price" + ?'
        assert params == (10,)

    def test_subtraction_arithmetic_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test subtraction arithmetic expression."""
        left = Column(sqlite_dialect_3_8_0, "balance")
        right = Literal(sqlite_dialect_3_8_0, 50)
        arithmetic_expr = BinaryArithmeticExpression(sqlite_dialect_3_8_0, "-", left, right)

        sql, params = arithmetic_expr.to_sql()
        assert sql == '"balance" - ?'
        assert params == (50,)

    def test_multiplication_arithmetic_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test multiplication arithmetic expression."""
        left = Column(sqlite_dialect_3_8_0, "quantity")
        right = Column(sqlite_dialect_3_8_0, "unit_price")
        arithmetic_expr = BinaryArithmeticExpression(sqlite_dialect_3_8_0, "*", left, right)

        sql, params = arithmetic_expr.to_sql()
        assert sql == '"quantity" * "unit_price"'
        assert params == ()

    def test_division_arithmetic_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test division arithmetic expression."""
        left = Column(sqlite_dialect_3_8_0, "total")
        right = Literal(sqlite_dialect_3_8_0, 12)
        arithmetic_expr = BinaryArithmeticExpression(sqlite_dialect_3_8_0, "/", left, right)

        sql, params = arithmetic_expr.to_sql()
        assert sql == '"total" / ?'
        assert params == (12,)

    def test_modulo_arithmetic_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test modulo arithmetic expression."""
        left = Column(sqlite_dialect_3_8_0, "value")
        right = Literal(sqlite_dialect_3_8_0, 10)
        arithmetic_expr = BinaryArithmeticExpression(sqlite_dialect_3_8_0, "%", left, right)

        sql, params = arithmetic_expr.to_sql()
        assert sql == '"value" % ?'
        assert params == (10,)


class TestRawSQLExpression:
    """Tests for RawSQLExpression representing raw SQL strings."""

    def test_raw_sql_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic RawSQLExpression."""
        raw_expr = RawSQLExpression(sqlite_dialect_3_8_0, "CURRENT_TIMESTAMP")
        sql, params = raw_expr.to_sql()
        assert sql == "CURRENT_TIMESTAMP"
        assert params == ()

    def test_raw_sql_with_params(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test RawSQLExpression with parameters."""
        raw_expr = RawSQLExpression(sqlite_dialect_3_8_0, "datetime('now', 'localtime')", ())
        sql, params = raw_expr.to_sql()
        assert sql == "datetime('now', 'localtime')"
        assert params == ()