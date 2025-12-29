# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_advanced_functions.py
"""
Tests for the advanced SQL function expression components in advanced_functions.py
"""
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal
)
from rhosocial.activerecord.backend.expression.advanced_functions import (
    CaseExpression, CastExpression, ExistsExpression,
    AnyExpression, AllExpression, JSONExpression, ArrayExpression,
    OrderedSetAggregation
)
from rhosocial.activerecord.backend.expression.core import Subquery
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestCaseExpression:
    """Tests for CaseExpression class."""

    def test_case_expression_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic CASE expression functionality."""
        # Create a basic CASE expression with one condition-result pair
        condition = Column(sqlite_dialect_3_8_0, "age") > Literal(sqlite_dialect_3_8_0, 18)
        result = Literal(sqlite_dialect_3_8_0, "adult")
        case_expr = CaseExpression(sqlite_dialect_3_8_0, cases=[(condition, result)])

        sql, params = case_expr.to_sql()
        assert "CASE" in sql
        assert params == (18, "adult")

    def test_case_expression_multiple_conditions(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test CASE expression with multiple conditions."""
        condition1 = Column(sqlite_dialect_3_8_0, "age") > Literal(sqlite_dialect_3_8_0, 65)
        result1 = Literal(sqlite_dialect_3_8_0, "senior")
        condition2 = Column(sqlite_dialect_3_8_0, "age") > Literal(sqlite_dialect_3_8_0, 18)
        result2 = Literal(sqlite_dialect_3_8_0, "adult")

        case_expr = CaseExpression(
            sqlite_dialect_3_8_0,
            cases=[(condition1, result1), (condition2, result2)],
            else_result=Literal(sqlite_dialect_3_8_0, "minor")
        )

        sql, params = case_expr.to_sql()
        assert "CASE" in sql
        assert len(params) == 5  # 65, "senior", 18, "adult", "minor"

    def test_case_expression_simple_case(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test simple CASE expression with value."""
        value = Column(sqlite_dialect_3_8_0, "status_code")
        case_expr = CaseExpression(
            sqlite_dialect_3_8_0,
            value=value,
            cases=[
                (Literal(sqlite_dialect_3_8_0, 1), Literal(sqlite_dialect_3_8_0, "Active")),
                (Literal(sqlite_dialect_3_8_0, 0), Literal(sqlite_dialect_3_8_0, "Inactive"))
            ],
            else_result=Literal(sqlite_dialect_3_8_0, "Unknown")
        )

        sql, params = case_expr.to_sql()
        assert "CASE" in sql
        assert len(params) == 5  # 1, "Active", 0, "Inactive", "Unknown"


class TestCastExpression:
    """Tests for CastExpression class."""

    def test_cast_expression_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic CAST expression functionality."""
        cast_expr = CastExpression(sqlite_dialect_3_8_0, Column(sqlite_dialect_3_8_0, "price"), "INTEGER")
        sql, params = cast_expr.to_sql()
        # SQLite uses CAST(expr AS type)
        assert "CAST(" in sql
        assert "AS INTEGER" in sql
        assert params == ()


class TestExistsExpression:
    """Tests for ExistsExpression class."""

    def test_exists_expression_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic EXISTS expression functionality."""
        subquery = Subquery(sqlite_dialect_3_8_0, "SELECT 1 FROM orders WHERE user_id = users.id", ())
        exists_expr = ExistsExpression(sqlite_dialect_3_8_0, subquery)
        sql, params = exists_expr.to_sql()
        assert "EXISTS" in sql.upper()
        assert params == ()

    def test_not_exists_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test NOT EXISTS expression functionality."""
        subquery = Subquery(sqlite_dialect_3_8_0, "SELECT 1 FROM orders WHERE user_id = users.id", ())
        exists_expr = ExistsExpression(sqlite_dialect_3_8_0, subquery, is_not=True)
        sql, params = exists_expr.to_sql()
        assert "NOT EXISTS" in sql.upper()
        assert params == ()


class TestAnyAllExpression:
    """Tests for AnyExpression and AllExpression classes."""

    def test_any_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test ANY expression functionality."""
        # ANY with a list might generate different SQL in SQLite
        any_expr = AnyExpression(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "price"),
            ">",
            Literal(sqlite_dialect_3_8_0, [100, 200, 300])
        )
        sql, params = any_expr.to_sql()
        # SQLite might convert ANY to other forms
        assert sql  # Should generate some valid SQL
        assert len(params) == 1  # The list should be a single parameter

    def test_all_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test ALL expression functionality."""
        all_expr = AllExpression(
            sqlite_dialect_3_8_0,
            Column(sqlite_dialect_3_8_0, "price"),
            ">",
            Literal(sqlite_dialect_3_8_0, [50, 75])
        )
        sql, params = all_expr.to_sql()
        # This might be converted to a different form in SQLite
        assert sql  # Should generate some valid SQL
        assert params == ((50, 75),)  # The list should be a single parameter tuple


class TestJSONExpression:
    """Tests for JSONExpression class."""

    def test_json_extract_path(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test JSON path extraction."""
        json_expr = JSONExpression(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.name"
        )
        sql, params = json_expr.to_sql()
        # In SQLite, this uses the -> operator
        assert "->" in sql
        assert params == ("$.name",)

    def test_json_extract_as_text(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test JSON path extraction as text."""
        json_expr = JSONExpression(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "metadata"),
            "$.settings.theme",
            operation="->>"
        )
        sql, params = json_expr.to_sql()
        # In SQLite, this uses the ->> operator
        assert "->>" in sql
        assert params == ("$.settings.theme",)


class TestArrayExpression:
    """Tests for ArrayExpression class."""

    def test_array_constructor_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that array constructor is not supported in SQLite."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        array_expr = ArrayExpression(
            sqlite_dialect_3_8_0,
            "CONSTRUCTOR",
            elements=[Literal(sqlite_dialect_3_8_0, 1), Literal(sqlite_dialect_3_8_0, 2), Literal(sqlite_dialect_3_8_0, 3)]
        )
        # Try to generate SQL - this should raise UnsupportedFeatureError in SQLite
        with pytest.raises(UnsupportedFeatureError):
            array_expr.to_sql()

    def test_array_access_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that array access is not supported in SQLite."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        array_access = ArrayExpression(
            sqlite_dialect_3_8_0,
            "ACCESS",
            base_expr=Column(sqlite_dialect_3_8_0, "tags"),
            index_expr=Literal(sqlite_dialect_3_8_0, 1)
        )
        # Try to generate SQL - this should raise UnsupportedFeatureError in SQLite
        with pytest.raises(UnsupportedFeatureError):
            array_access.to_sql()


class TestOrderedSetAggregation:
    """Tests for OrderedSetAggregation class."""

    def test_ordered_set_aggregation_not_supported(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that ordered set aggregation is not supported in SQLite."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        
        try:
            # PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary)
            expr = OrderedSetAggregation(
                sqlite_dialect_3_8_0,
                "PERCENTILE_CONT",
                args=[Literal(sqlite_dialect_3_8_0, 0.5)],
                order_by=[Column(sqlite_dialect_3_8_0, "salary")],
                alias="median_salary"
            )
            expr.to_sql()
            # If we reach here, the exception was not raised
            assert False, "Expected UnsupportedFeatureError for ordered set aggregation"
        except UnsupportedFeatureError:
            # This is expected
            pass