# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_operators.py
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall
)
from rhosocial.activerecord.backend.expression.operators import (
    SQLOperation, BinaryExpression, UnaryExpression, RawSQLExpression, RawSQLPredicate
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

        # Use operator overloading instead of direct instantiation
        arith_expr = left * right

        sql, params = arith_expr.to_sql()

        assert sql == '"price" * ?'
        assert params == (1.1,)

    def test_binary_arithmetic_expression_with_functions(self, dummy_dialect: DummyDialect):
        """Test binary arithmetic with function calls."""
        left = FunctionCall(dummy_dialect, "SUM", Column(dummy_dialect, "amount"))
        right = Literal(dummy_dialect, 2)

        # Use operator overloading instead of direct instantiation
        arith_expr = left / right

        sql, params = arith_expr.to_sql()

        assert sql == 'SUM("amount") / ?'
        assert params == (2,)

    def test_binary_arithmetic_different_operators(self, dummy_dialect: DummyDialect):
        """Test binary arithmetic with different operators."""
        left = Column(dummy_dialect, "quantity")
        right = Column(dummy_dialect, "unit_price")

        # Test using operator overloading
        add_expr = left + right
        sql, params = add_expr.to_sql()
        assert sql == '"quantity" + "unit_price"'
        assert params == ()

        sub_expr = left - right
        sql, params = sub_expr.to_sql()
        assert sql == '"quantity" - "unit_price"'
        assert params == ()

        mul_expr = left * right
        sql, params = mul_expr.to_sql()
        assert sql == '"quantity" * "unit_price"'
        assert params == ()

        div_expr = left / right
        sql, params = div_expr.to_sql()
        assert sql == '"quantity" / "unit_price"'
        assert params == ()

        mod_expr = left % right
        sql, params = mod_expr.to_sql()
        assert sql == '"quantity" % "unit_price"'
        assert params == ()


class TestBinaryArithmeticExpressionPrecedence:
    """Tests for BinaryArithmeticExpression operator precedence and parentheses handling."""

    def test_multiplication_precedence_over_addition(self, dummy_dialect: DummyDialect):
        """Test that multiplication has higher precedence than addition."""
        # Expression: (a + b) * c should generate ("a + b") * c
        left_add = Column(dummy_dialect, "a") + Column(dummy_dialect, "b")
        right = Column(dummy_dialect, "c")
        expr = left_add * right

        sql, params = expr.to_sql()

        # Multiplication has higher precedence than addition, so the addition part should be in parentheses
        assert sql == '("a" + "b") * "c"'
        assert params == ()

    def test_addition_precedence_lower_than_multiplication(self, dummy_dialect: DummyDialect):
        """Test that addition has lower precedence than multiplication."""
        # Expression: a + (b * c) should generate "a + b * c" (no parentheses needed for multiplication)
        left = Column(dummy_dialect, "a")
        right_mult = Column(dummy_dialect, "b") * Column(dummy_dialect, "c")
        expr = left + right_mult

        sql, params = expr.to_sql()

        # Addition has lower precedence than multiplication, so no parentheses needed for multiplication part
        assert sql == '"a" + "b" * "c"'
        assert params == ()

    def test_multiplication_precedence_over_subtraction(self, dummy_dialect: DummyDialect):
        """Test that multiplication has higher precedence than subtraction."""
        # Expression: (a - b) * c should generate ("a - b") * c
        left_sub = Column(dummy_dialect, "a") - Column(dummy_dialect, "b")
        right = Column(dummy_dialect, "c")
        expr = left_sub * right

        sql, params = expr.to_sql()

        # Multiplication has higher precedence than subtraction, so the subtraction part should be in parentheses
        assert sql == '("a" - "b") * "c"'
        assert params == ()

    def test_division_precedence_over_addition(self, dummy_dialect: DummyDialect):
        """Test that division has higher precedence than addition."""
        # Expression: (a + b) / c should generate ("a + b") / c
        left_add = Column(dummy_dialect, "a") + Column(dummy_dialect, "b")
        right = Column(dummy_dialect, "c")
        expr = left_add / right

        sql, params = expr.to_sql()

        # Division has higher precedence than addition, so the addition part should be in parentheses
        assert sql == '("a" + "b") / "c"'
        assert params == ()

    def test_same_precedence_left_associative(self, dummy_dialect: DummyDialect):
        """Test that operators with same precedence are left-associative."""
        # Expression: (a * b) / c should generate "a * b / c" (no parentheses needed for left-associative)
        left_mult = Column(dummy_dialect, "a") * Column(dummy_dialect, "b")
        right = Column(dummy_dialect, "c")
        expr = left_mult / right

        sql, params = expr.to_sql()

        # Both multiplication and division have same precedence, so no parentheses needed for left part
        assert sql == '"a" * "b" / "c"'
        assert params == ()

    def test_addition_subtraction_same_precedence(self, dummy_dialect: DummyDialect):
        """Test that addition and subtraction have same precedence."""
        # Expression: (a - b) + c should generate "a - b + c" (no parentheses needed for left-associative)
        left_sub = Column(dummy_dialect, "a") - Column(dummy_dialect, "b")
        right = Column(dummy_dialect, "c")
        expr = left_sub + right

        sql, params = expr.to_sql()

        # Both addition and subtraction have same precedence, so no parentheses needed
        assert sql == '"a" - "b" + "c"'
        assert params == ()

    def test_right_operand_needs_parens_case(self, dummy_dialect: DummyDialect):
        """Test the right operand needs parentheses case."""
        # More specifically test right_needs_parens: when right operand has lower precedence than current operator
        # Example: a * (b + c) where addition has lower precedence than multiplication
        left = Column(dummy_dialect, "a")
        right_add = Column(dummy_dialect, "b") + Column(dummy_dialect, "c")
        expr = left * right_add

        sql, params = expr.to_sql()

        # Multiplication has higher precedence than addition, so the addition part should be in parentheses
        assert sql == '"a" * ("b" + "c")'
        assert params == ()

    def test_right_operand_higher_precedence_than_current(self, dummy_dialect: DummyDialect):
        """Test when right operand has higher precedence than current operator."""
        # Expression: a + (b * c) where multiplication has higher precedence than addition
        # In this case, the right operand (b * c) should NOT need parentheses since it has higher precedence
        left = Column(dummy_dialect, "a")
        right_mult = Column(dummy_dialect, "b") * Column(dummy_dialect, "c")
        expr = left + right_mult

        sql, params = expr.to_sql()

        # Addition has lower precedence than multiplication, so no parentheses needed for multiplication part
        assert sql == '"a" + "b" * "c"'
        assert params == ()


class TestRawSQLPredicate:
    """Tests for RawSQLPredicate representing raw SQL predicate strings."""

    def test_raw_sql_predicate_basic(self, dummy_dialect: DummyDialect):
        """Test basic raw SQL predicate."""
        raw_predicate = RawSQLPredicate(dummy_dialect, "age > 18")

        sql, params = raw_predicate.to_sql()

        assert sql == "age > 18"
        assert params == ()

    def test_raw_sql_predicate_with_complex_sql(self, dummy_dialect: DummyDialect):
        """Test raw SQL predicate with complex SQL string."""
        complex_predicate = "created_at > NOW() - INTERVAL 30 DAY AND status = 'active'"
        raw_predicate = RawSQLPredicate(dummy_dialect, complex_predicate)

        sql, params = raw_predicate.to_sql()

        assert sql == complex_predicate
        assert params == ()

    def test_raw_sql_predicate_with_placeholders(self, dummy_dialect: DummyDialect):
        """Test raw SQL predicate with parameter placeholders."""
        predicate_with_placeholders = "col1 = ? AND col2 = ?"
        raw_predicate = RawSQLPredicate(dummy_dialect, predicate_with_placeholders, (1, "value"))

        sql, params = raw_predicate.to_sql()

        assert sql == predicate_with_placeholders
        assert params == (1, "value")

    def test_raw_sql_predicate_empty_params(self, dummy_dialect: DummyDialect):
        """Test raw SQL predicate with empty params."""
        raw_predicate = RawSQLPredicate(dummy_dialect, "status = 'active'", ())

        sql, params = raw_predicate.to_sql()

        assert sql == "status = 'active'"
        assert params == ()

    def test_raw_sql_predicate_is_predicate_subclass(self, dummy_dialect: DummyDialect):
        """Test that RawSQLPredicate is indeed a subclass of SQLPredicate."""
        from rhosocial.activerecord.backend.expression.bases import SQLPredicate
        raw_predicate = RawSQLPredicate(dummy_dialect, "age > 18")

        assert isinstance(raw_predicate, SQLPredicate)