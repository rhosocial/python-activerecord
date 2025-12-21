# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_operators.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, Subquery
)
from rhosocial.activerecord.backend.expression.operators import (
    SQLOperation, BinaryExpression, UnaryExpression, RawSQLExpression, BinaryArithmeticExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestSQLOperation:
    """Tests for SQLOperation representing generic SQL operations."""

    def test_sql_operation_with_operands(self, dummy_dialect: DummyDialect):
        """Test SQLOperation with multiple operands."""
        operand1 = Literal(dummy_dialect, "value1")
        operand2 = Column(dummy_dialect, "column_name")
        
        sql_op = SQLOperation(dummy_dialect, "CUSTOM_OP", operand1, operand2)
        
        sql, params = sql_op.to_sql()
        
        assert "CUSTOM_OP(" in sql
        assert params == ("value1",)

    def test_sql_operation_without_operands(self, dummy_dialect: DummyDialect):
        """Test SQLOperation with no operands."""
        sql_op = SQLOperation(dummy_dialect, "NO_PARAM_FUNC")
        
        sql, params = sql_op.to_sql()
        
        assert sql == "NO_PARAM_FUNC()"
        assert params == ()

    def test_sql_operation_single_operand(self, dummy_dialect: DummyDialect):
        """Test SQLOperation with single operand."""
        operand = Literal(dummy_dialect, 42)
        
        sql_op = SQLOperation(dummy_dialect, "SINGLE_ARG", operand)
        
        sql, params = sql_op.to_sql()
        
        assert "SINGLE_ARG(" in sql
        assert params == (42,)


class TestBinaryExpression:
    """Tests for BinaryExpression representing binary SQL operations."""

    def test_binary_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic binary expression."""
        left = Column(dummy_dialect, "age")
        right = Literal(dummy_dialect, 18)
        
        bin_expr = BinaryExpression(dummy_dialect, ">", left, right)
        
        sql, params = bin_expr.to_sql()
        
        # The exact format depends on the dialect's format_binary_operator method
        assert ">" in sql
        assert params == (18,)

    def test_binary_expression_with_complex_operands(self, dummy_dialect: DummyDialect):
        """Test binary expression with complex operands."""
        left = FunctionCall(dummy_dialect, "UPPER", Column(dummy_dialect, "name"))
        right = Literal(dummy_dialect, "JOHN")
        
        bin_expr = BinaryExpression(dummy_dialect, "=", left, right)
        
        sql, params = bin_expr.to_sql()
        
        assert "UPPER" in sql.upper()
        assert params == ("JOHN",)

    def test_binary_expression_different_operators(self, dummy_dialect: DummyDialect):
        """Test binary expression with different operators."""
        left = Column(dummy_dialect, "score")
        right = Literal(dummy_dialect, 100)
        
        operators = ["+", "-", "*", "/", "=", "!=", "<", ">", "<=", ">="]
        
        for op in operators:
            bin_expr = BinaryExpression(dummy_dialect, op, left, right)
            
            sql, params = bin_expr.to_sql()
            
            assert op in sql
            assert params == (100,)


class TestUnaryExpression:
    """Tests for UnaryExpression representing unary SQL operations."""

    def test_unary_expression_before_position(self, dummy_dialect: DummyDialect):
        """Test unary expression with operator before operand."""
        operand = Column(dummy_dialect, "name")
        
        unary_expr = UnaryExpression(dummy_dialect, "NOT", operand, pos='before')
        
        sql, params = unary_expr.to_sql()
        
        # The exact format depends on the dialect's format_unary_operator method
        assert "NOT" in sql.upper()
        assert params == ()

    def test_unary_expression_after_position(self, dummy_dialect: DummyDialect):
        """Test unary expression with operator after operand."""
        operand = Column(dummy_dialect, "value")
        
        unary_expr = UnaryExpression(dummy_dialect, "++", operand, pos='after')
        
        sql, params = unary_expr.to_sql()
        
        # The exact format depends on the dialect's format_unary_operator method
        assert "++" in sql
        assert params == ()

    def test_unary_expression_with_literal(self, dummy_dialect: DummyDialect):
        """Test unary expression with literal operand."""
        operand = Literal(dummy_dialect, -5)
        
        unary_expr = UnaryExpression(dummy_dialect, "ABS", operand, pos='before')
        
        sql, params = unary_expr.to_sql()
        
        assert "ABS" in sql.upper()
        assert params == (-5,)


class TestRawSQLExpression:
    """Tests for RawSQLExpression representing raw SQL strings."""

    def test_raw_sql_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic raw SQL expression."""
        raw_sql = RawSQLExpression(dummy_dialect, "NOW()")
        
        sql, params = raw_sql.to_sql()
        
        assert sql == "NOW()"
        assert params == ()

    def test_raw_sql_expression_with_complex_sql(self, dummy_dialect: DummyDialect):
        """Test raw SQL expression with complex SQL string."""
        complex_sql = "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL 30 DAY"
        raw_sql = RawSQLExpression(dummy_dialect, complex_sql)
        
        sql, params = raw_sql.to_sql()
        
        assert sql == complex_sql
        assert params == ()

    def test_raw_sql_expression_with_placeholders(self, dummy_dialect: DummyDialect):
        """Test raw SQL expression with parameter placeholders."""
        sql_with_placeholders = "SELECT * FROM table WHERE col = ? AND other_col = ?"
        raw_sql = RawSQLExpression(dummy_dialect, sql_with_placeholders)
        
        sql, params = raw_sql.to_sql()
        
        assert sql == sql_with_placeholders
        assert params == ()


class TestBinaryArithmeticExpression:
    """Tests for BinaryArithmeticExpression representing binary arithmetic operations."""

    def test_binary_arithmetic_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic binary arithmetic expression."""
        left = Column(dummy_dialect, "price")
        right = Literal(dummy_dialect, 1.1)
        
        arith_expr = BinaryArithmeticExpression(dummy_dialect, "*", left, right)
        
        sql, params = arith_expr.to_sql()
        
        assert "*" in sql
        assert params == (1.1,)

    def test_binary_arithmetic_expression_with_functions(self, dummy_dialect: DummyDialect):
        """Test binary arithmetic with function calls."""
        left = FunctionCall(dummy_dialect, "SUM", Column(dummy_dialect, "amount"))
        right = Literal(dummy_dialect, 2)
        
        arith_expr = BinaryArithmeticExpression(dummy_dialect, "/", left, right)
        
        sql, params = arith_expr.to_sql()
        
        assert "/" in sql
        assert "SUM" in sql.upper()
        assert params == (2,)

    def test_binary_arithmetic_different_operators(self, dummy_dialect: DummyDialect):
        """Test binary arithmetic with different operators."""
        left = Column(dummy_dialect, "quantity")
        right = Column(dummy_dialect, "unit_price")
        
        operators = ["+", "-", "*", "/", "%"]
        
        for op in operators:
            arith_expr = BinaryArithmeticExpression(dummy_dialect, op, left, right)
            
            sql, params = arith_expr.to_sql()
            
            assert op in sql
            assert params == ()