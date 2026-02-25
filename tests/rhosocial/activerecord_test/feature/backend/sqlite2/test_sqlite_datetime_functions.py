# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_datetime_functions.py
"""
Tests for SQLite-specific datetime functions and special constants in DML and DQL operations.
This file tests various SQLite datetime functions and special constants in INSERT, UPDATE, 
DELETE, and SELECT operations.
"""
import pytest
from datetime import datetime, timedelta
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, RawSQLExpression,
    QueryExpression, UpdateExpression, DeleteExpression,
    ComparisonPredicate, LogicalPredicate
)
from rhosocial.activerecord.backend.expression.statements import (
    InsertExpression, ReturningClause, ValuesSource
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLiteDateTimeFunctions:
    """Tests for SQLite datetime functions and special constants in various operations."""

    def test_current_timestamp_in_insert(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test CURRENT_TIMESTAMP in INSERT operations."""
        # Using RawSQLExpression for CURRENT_TIMESTAMP
        raw_timestamp = RawSQLExpression(sqlite_dialect_3_8_0, 'CURRENT_TIMESTAMP')
        
        insert_expr = InsertExpression(
            sqlite_dialect_3_8_0,
            into="users",
            source=ValuesSource(
                sqlite_dialect_3_8_0,
                values_list=[[Literal(sqlite_dialect_3_8_0, "john"), raw_timestamp]]
            ),
            columns=["username", "created_at"]
        )
        
        sql, params = insert_expr.to_sql()
        assert 'CURRENT_TIMESTAMP' in sql
        assert params == ("john",)
        # Verify that CURRENT_TIMESTAMP is not parameterized
        assert sql.count('?') == 1  # Only the "john" parameter

    def test_current_timestamp_in_update(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test CURRENT_TIMESTAMP in UPDATE operations."""
        raw_timestamp = RawSQLExpression(sqlite_dialect_3_8_0, 'CURRENT_TIMESTAMP')
        
        update_expr = UpdateExpression(
            sqlite_dialect_3_8_0,
            table="users",
            assignments={
                "updated_at": raw_timestamp,
                "username": Literal(sqlite_dialect_3_8_0, "updated_john")
            },
            where=Column(sqlite_dialect_3_8_0, "id") == Literal(sqlite_dialect_3_8_0, 1)
        )
        
        sql, params = update_expr.to_sql()
        assert 'CURRENT_TIMESTAMP' in sql
        assert params == ("updated_john", 1)
        # Verify that CURRENT_TIMESTAMP is not parameterized
        assert sql.count('?') == 2  # "updated_john" and the WHERE value

    def test_datetime_function_in_select(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test datetime functions in SELECT operations."""
        # Using FunctionCall for datetime functions
        now_func = FunctionCall(sqlite_dialect_3_8_0, "DATETIME", Literal(sqlite_dialect_3_8_0, "now"))
        date_func = FunctionCall(sqlite_dialect_3_8_0, "DATE", Literal(sqlite_dialect_3_8_0, "now"))
        
        query_expr = QueryExpression(
            sqlite_dialect_3_8_0,
            select=[
                Column(sqlite_dialect_3_8_0, "id"),
                now_func,
                date_func
            ],
            from_="users"  # Use string instead of Column
        )
        
        sql, params = query_expr.to_sql()
        assert 'DATETIME(' in sql  # Check that function is in SQL
        assert 'DATE(' in sql  # Check that function is in SQL
        assert len(params) == 2  # Two parameters for the two literals
        assert params == ("now", "now")  # The actual parameter values

    def test_date_arithmetic_in_where_clause(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test date arithmetic in WHERE clauses."""
        # Using FunctionCall for date arithmetic
        date_func = FunctionCall(
            sqlite_dialect_3_8_0, 
            "DATE", 
            Literal(sqlite_dialect_3_8_0, "now"), 
            Literal(sqlite_dialect_3_8_0, "-1 day")
        )
        
        query_expr = QueryExpression(
            sqlite_dialect_3_8_0,
            select=[Column(sqlite_dialect_3_8_0, "id")],
            from_="users",
            where=Column(sqlite_dialect_3_8_0, "created_at") > date_func
        )
        
        sql, params = query_expr.to_sql()
        assert 'DATE(' in sql  # Check that function is in SQL
        assert len(params) == 2  # Two parameters for the two literals
        assert params == ("now", "-1 day")  # The actual parameter values

    def test_current_timestamp_in_delete(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test CURRENT_TIMESTAMP concept in DELETE operations (for audit trails)."""
        # Create a table with a timestamp column for audit purposes
        delete_expr = DeleteExpression(
            sqlite_dialect_3_8_0,
            table="temp_users",
            where=Column(sqlite_dialect_3_8_0, "status") == Literal(sqlite_dialect_3_8_0, "inactive")
        )
        
        sql, params = delete_expr.to_sql()
        assert 'temp_users' in sql
        assert params == ("inactive",)

    def test_multiple_datetime_functions_in_single_query(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test multiple datetime functions in a single query."""
        # Various datetime functions
        current_timestamp = RawSQLExpression(sqlite_dialect_3_8_0, 'CURRENT_TIMESTAMP')
        now_func = FunctionCall(sqlite_dialect_3_8_0, "DATETIME", Literal(sqlite_dialect_3_8_0, "now"))
        today_func = FunctionCall(sqlite_dialect_3_8_0, "DATE", Literal(sqlite_dialect_3_8_0, "now"))
        time_func = FunctionCall(sqlite_dialect_3_8_0, "TIME", Literal(sqlite_dialect_3_8_0, "now"))
        
        query_expr = QueryExpression(
            sqlite_dialect_3_8_0,
            select=[
                current_timestamp,
                now_func,
                today_func,
                time_func
            ],
            from_="dual"  # Using dual as dummy table
        )
        
        sql, params = query_expr.to_sql()
        assert 'CURRENT_TIMESTAMP' in sql  # RawSQLExpression should appear directly
        assert 'DATETIME(' in sql  # FunctionCall should appear with parameter placeholder
        assert 'DATE(' in sql  # FunctionCall should appear with parameter placeholder
        assert 'TIME(' in sql  # FunctionCall should appear with parameter placeholder
        assert len(params) == 3  # Three parameters for the three literals in FunctionCalls
        assert params == ("now", "now", "now")  # The actual parameter values

    def test_datetime_with_returning_clause(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test datetime functions with RETURNING clause."""
        if sqlite_dialect_3_8_0.supports_returning_clause():
            raw_timestamp = RawSQLExpression(sqlite_dialect_3_8_0, 'CURRENT_TIMESTAMP')
            
            update_expr = UpdateExpression(
                sqlite_dialect_3_8_0,
                table="users",
                assignments={
                    "updated_at": raw_timestamp,
                    "status": Literal(sqlite_dialect_3_8_0, "active")
                },
                where=Column(sqlite_dialect_3_8_0, "id") == Literal(sqlite_dialect_3_8_0, 1),
                returning=ReturningClause(
                    sqlite_dialect_3_8_0,
                    expressions=[
                        Column(sqlite_dialect_3_8_0, "id"),
                        Column(sqlite_dialect_3_8_0, "updated_at")
                    ]
                )
            )
            
            sql, params = update_expr.to_sql()
            assert 'CURRENT_TIMESTAMP' in sql
            assert 'RETURNING' in sql.upper()
            assert params == ("active", 1)

    def test_strftime_function_in_operations(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test STRFTIME function in various operations."""
        # STRFTIME function to format dates
        strftime_func = FunctionCall(
            sqlite_dialect_3_8_0,
            "STRFTIME",
            Literal(sqlite_dialect_3_8_0, "%Y-%m-%d %H:%M:%S"),
            Literal(sqlite_dialect_3_8_0, "now")
        )
        
        query_expr = QueryExpression(
            sqlite_dialect_3_8_0,
            select=[strftime_func, Column(sqlite_dialect_3_8_0, "id")],
            from_="events"
        )
        
        sql, params = query_expr.to_sql()
        assert 'STRFTIME(' in sql  # Check that function is in SQL
        assert len(params) == 2  # Two parameters for the two literals in STRFTIME
        assert params == ("%Y-%m-%d %H:%M:%S", "now")  # The actual parameter values

    def test_datetime_comparison_with_literals(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test datetime comparisons with literal values."""
        # Compare datetime with literal
        query_expr = QueryExpression(
            sqlite_dialect_3_8_0,
            select=[Column(sqlite_dialect_3_8_0, "id")],
            from_="logs",
            where=Column(sqlite_dialect_3_8_0, "timestamp") > Literal(sqlite_dialect_3_8_0, "2023-01-01 00:00:00")
        )
        
        sql, params = query_expr.to_sql()
        assert 'timestamp' in sql
        assert params == ("2023-01-01 00:00:00",)

    def test_julianday_function(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test JULIANDAY function in operations."""
        julianday_func = FunctionCall(
            sqlite_dialect_3_8_0,
            "JULIANDAY",
            Literal(sqlite_dialect_3_8_0, "now")
        )
        
        query_expr = QueryExpression(
            sqlite_dialect_3_8_0,
            select=[
                Column(sqlite_dialect_3_8_0, "id"),
                julianday_func
            ],
            from_="calendar_events"
        )
        
        sql, params = query_expr.to_sql()
        assert 'JULIANDAY(' in sql  # Check that function is in SQL
        assert len(params) == 1  # One parameter for the literal in JULIANDAY
        assert params == ("now",)  # The actual parameter value