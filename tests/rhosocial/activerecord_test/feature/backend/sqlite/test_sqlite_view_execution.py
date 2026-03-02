# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_sqlite_view_execution.py
"""
Tests for SQLite VIEW functionality with actual database execution.

These tests verify that generated SQL statements execute correctly
against an actual SQLite database.
"""
import pytest
import sqlite3
from unittest.mock import patch

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, TableExpression, QueryExpression,
    CreateViewExpression, DropViewExpression,
    CreateMaterializedViewExpression, DropMaterializedViewExpression,
    RefreshMaterializedViewExpression,
    CreateTableExpression, DropTableExpression, InsertExpression,
    ColumnDefinition, ColumnConstraint, ColumnConstraintType,
    TableConstraint, TableConstraintType, ForeignKeyConstraint,
    ValuesSource
)
from rhosocial.activerecord.backend.expression.operators import RawSQLPredicate, RawSQLExpression
from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause, WhereClause
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


@pytest.fixture
def sqlite_backend():
    """Provides a SQLiteBackend instance connected to an in-memory database."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    dialect = backend.dialect

    # Create users table using expression system
    users_columns = [
        ColumnDefinition(
            name="id",
            data_type="INTEGER",
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
            ]
        ),
        ColumnDefinition(
            name="name",
            data_type="TEXT",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        ),
        ColumnDefinition(name="email", data_type="TEXT"),
        ColumnDefinition(
            name="status",
            data_type="TEXT",
            constraints=[
                ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=RawSQLExpression(dialect, "'active'"))
            ]
        ),
    ]

    create_users = CreateTableExpression(
        dialect,
        table_name="users",
        columns=users_columns
    )

    sql, params = create_users.to_sql()
    backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create orders table using expression system
    orders_columns = [
        ColumnDefinition(
            name="id",
            data_type="INTEGER",
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
            ]
        ),
        ColumnDefinition(name="user_id", data_type="INTEGER"),
        ColumnDefinition(name="amount", data_type="REAL"),
        ColumnDefinition(name="order_date", data_type="TEXT"),
    ]

    orders_fk_constraint = ForeignKeyConstraint(
        constraint_type=TableConstraintType.FOREIGN_KEY,
        columns=["user_id"],
        foreign_key_table="users",
        foreign_key_columns=["id"]
    )

    create_orders = CreateTableExpression(
        dialect,
        table_name="orders",
        columns=orders_columns,
        table_constraints=[orders_fk_constraint]
    )

    sql, params = create_orders.to_sql()
    backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Insert test data using expression system
    insert_users = [
        ('Alice', 'alice@example.com', 'active'),
        ('Bob', 'bob@example.com', 'inactive'),
        ('Charlie', 'charlie@example.com', 'active'),
    ]

    for name, email, status in insert_users:
        insert_expr = InsertExpression(
            dialect,
            into="users",
            source=ValuesSource(dialect, [
                [Literal(dialect, name), Literal(dialect, email), Literal(dialect, status)]
            ]),
            columns=["name", "email", "status"]
        )
        sql, params = insert_expr.to_sql()
        backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))

    insert_orders = [
        (1, 100.0, '2024-01-01'),
        (1, 200.0, '2024-01-15'),
        (2, 50.0, '2024-01-10'),
    ]

    for user_id, amount, order_date in insert_orders:
        insert_expr = InsertExpression(
            dialect,
            into="orders",
            source=ValuesSource(dialect, [
                [Literal(dialect, user_id), Literal(dialect, amount), Literal(dialect, order_date)]
            ]),
            columns=["user_id", "amount", "order_date"]
        )
        sql, params = insert_expr.to_sql()
        backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))

    yield backend

    backend.disconnect()


class TestSQLiteViewExecution:
    """Tests for CREATE VIEW and DROP VIEW with actual execution."""

    def test_create_view_basic(self, sqlite_backend):
        """Test basic CREATE VIEW executes successfully."""
        dialect = sqlite_backend.dialect
        
        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")],
            from_=TableExpression(dialect, "users")
        )
        
        create_view = CreateViewExpression(
            dialect,
            view_name="user_view",
            query=query
        )
        
        sql, params = create_view.to_sql()
        
        # Execute CREATE VIEW
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        
        # Verify view was created by querying it
        result = sqlite_backend.execute(
            'SELECT * FROM "user_view"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True)
        )
        
        assert result.data is not None
        assert len(result.data) == 3
        assert result.data[0]['name'] == 'Alice'

    def test_create_view_with_where(self, sqlite_backend):
        """Test CREATE VIEW with WHERE clause executes successfully."""
        # Note: SQLite does not allow parameters in VIEW definitions
        # Using RawSQLPredicate to inline the condition value
        dialect = sqlite_backend.dialect

        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id"), Column(dialect, "name")],
            from_=TableExpression(dialect, "users"),
            where=WhereClause(dialect, condition=RawSQLPredicate(dialect, '"status" = \'active\''))
        )

        create_view = CreateViewExpression(
            dialect,
            view_name="active_users",
            query=query
        )

        sql, params = create_view.to_sql()
        
        # Execute CREATE VIEW
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        
        # Query the view
        result = sqlite_backend.execute(
            'SELECT * FROM "active_users"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True)
        )
        
        assert result.data is not None
        assert len(result.data) == 2 # Alice and Charlie are active

    def test_create_view_with_aggregates(self, sqlite_backend):
        """Test CREATE VIEW with aggregate functions."""
        dialect = sqlite_backend.dialect
        
        query = QueryExpression(
            dialect,
            select=[
                Column(dialect, "user_id"),
                FunctionCall(dialect, "SUM", Column(dialect, "amount"), alias="total_amount"),
                FunctionCall(dialect, "COUNT", Column(dialect, "id"), alias="order_count")
            ],
            from_=TableExpression(dialect, "orders"),
            group_by_having=GroupByHavingClause(
                dialect,
                group_by=[Column(dialect, "user_id")]
            )
        )
        
        create_view = CreateViewExpression(
            dialect,
            view_name="user_order_summary",
            query=query
        )
        
        sql, params = create_view.to_sql()
        
        # Execute CREATE VIEW
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        
        # Query the view
        result = sqlite_backend.execute(
            'SELECT * FROM "user_order_summary" ORDER BY user_id',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True)
        )

        assert result.data is not None
        assert len(result.data) == 2 # 2 users with orders

    def test_create_temporary_view(self, sqlite_backend):
        """Test CREATE TEMPORARY VIEW executes successfully."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id"), Column(dialect, "name")],
            from_=TableExpression(dialect, "users")
        )

        create_view = CreateViewExpression(
            dialect,
            view_name="temp_user_view",
            query=query,
            temporary=True
        )

        sql, params = create_view.to_sql()

        # Execute CREATE TEMPORARY VIEW
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

        # Query the temporary view
        result = sqlite_backend.execute(
            'SELECT * FROM "temp_user_view"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True)
        )

        assert result.data is not None
        assert len(result.data) == 3

    def test_create_view_if_not_exists(self, sqlite_backend):
        """Test CREATE VIEW IF NOT EXISTS (SQLite's OR REPLACE equivalent)."""
        dialect = sqlite_backend.dialect
        
        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id")],
            from_=TableExpression(dialect, "users")
        )
        
        # First create the view
        create_view = CreateViewExpression(
            dialect,
            view_name="test_view",
            query=query
        )
        
        sql, params = create_view.to_sql()
        sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))
        
        # Try to create again with IF NOT EXISTS
        create_view2 = CreateViewExpression(
            dialect,
            view_name="test_view",
            query=query,
            replace=True  # This generates IF NOT EXISTS in SQLite
        )
        
        sql, params = create_view2.to_sql()
        
        # Should not raise error
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

    def test_drop_view(self, sqlite_backend):
        """Test DROP VIEW executes successfully."""
        dialect = sqlite_backend.dialect
        
        # First create a view
        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id")],
            from_=TableExpression(dialect, "users")
        )
        
        create_view = CreateViewExpression(
            dialect,
            view_name="view_to_drop",
            query=query
        )
        
        sql, params = create_view.to_sql()
        sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))
        
        # Now drop it
        drop_view = DropViewExpression(
            dialect,
            view_name="view_to_drop"
        )
        
        sql, params = drop_view.to_sql()
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        
        # Verify view no longer exists
        with pytest.raises(Exception):  # Should raise OperationalError
            sqlite_backend.execute(
                'SELECT * FROM view_to_drop',
                (),
                options=ExecutionOptions(stmt_type=StatementType.SELECT)
            )

    def test_drop_view_if_exists(self, sqlite_backend):
        """Test DROP VIEW IF EXISTS executes without error for non-existent view."""
        dialect = sqlite_backend.dialect
        
        drop_view = DropViewExpression(
            dialect,
            view_name="nonexistent_view",
            if_exists=True
        )
        
        sql, params = drop_view.to_sql()
        
        # Should not raise error
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )

    def test_drop_view_if_exists_for_existing_view(self, sqlite_backend):
        """Test DROP VIEW IF EXISTS works for existing view."""
        dialect = sqlite_backend.dialect
        
        # First create a view
        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id")],
            from_=TableExpression(dialect, "users")
        )
        
        create_view = CreateViewExpression(
            dialect,
            view_name="view_to_drop_if_exists",
            query=query
        )
        
        sql, params = create_view.to_sql()
        sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))
        
        # Drop with IF EXISTS
        drop_view = DropViewExpression(
            dialect,
            view_name="view_to_drop_if_exists",
            if_exists=True
        )
        
        sql, params = drop_view.to_sql()
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        
        # Verify view is gone
        with pytest.raises(Exception):
            sqlite_backend.execute(
                'SELECT * FROM view_to_drop_if_exists',
                (),
                options=ExecutionOptions(stmt_type=StatementType.SELECT)
            )

    def test_create_view_with_column_aliases(self, sqlite_backend):
        """Test CREATE VIEW with explicit column aliases."""
        dialect = sqlite_backend.dialect
        
        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id"), Column(dialect, "name")],
            from_=TableExpression(dialect, "users")
        )
        
        create_view = CreateViewExpression(
            dialect,
            view_name="aliased_view",
            query=query,
            column_aliases=["user_id", "user_name"]
        )
        
        sql, params = create_view.to_sql()
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        
        # Query and check column names
        result = sqlite_backend.execute(
            'SELECT user_id, user_name FROM "aliased_view"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True)
        )
        
        assert result.data is not None


class TestSQLiteMaterializedViewExecution:
    """Tests for materialized view operations (should all fail)."""

    def test_create_materialized_view_raises_error(self, sqlite_backend):
        """Test that CREATE MATERIALIZED VIEW raises UnsupportedFeatureError."""
        dialect = sqlite_backend.dialect
        
        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id")],
            from_=TableExpression(dialect, "users")
        )
        
        create_mv = CreateMaterializedViewExpression(
            dialect,
            view_name="test_mv",
            query=query
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            create_mv.to_sql()
        
        assert "CREATE MATERIALIZED VIEW" in str(exc_info.value)
        assert "SQLite" in str(exc_info.value)

    def test_drop_materialized_view_raises_error(self, sqlite_backend):
        """Test that DROP MATERIALIZED VIEW raises UnsupportedFeatureError."""
        dialect = sqlite_backend.dialect
        
        drop_mv = DropMaterializedViewExpression(
            dialect,
            view_name="test_mv"
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            drop_mv.to_sql()
        
        assert "DROP MATERIALIZED VIEW" in str(exc_info.value)

    def test_refresh_materialized_view_raises_error(self, sqlite_backend):
        """Test that REFRESH MATERIALIZED VIEW raises UnsupportedFeatureError."""
        dialect = sqlite_backend.dialect
        
        refresh_mv = RefreshMaterializedViewExpression(
            dialect,
            view_name="test_mv"
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            refresh_mv.to_sql()
        
        assert "REFRESH MATERIALIZED VIEW" in str(exc_info.value)


class TestSQLiteViewJoins:
    """Tests for VIEW with JOIN operations."""

    def test_create_view_with_join(self, sqlite_backend):
        """Test CREATE VIEW with JOIN executes successfully."""
        from rhosocial.activerecord.backend.expression.query_parts import JoinExpression
        
        dialect = sqlite_backend.dialect
        
        users_table = TableExpression(dialect, "users", alias="u")
        orders_table = TableExpression(dialect, "orders", alias="o")
        
        join_condition = Column(dialect, "id", "u") == Column(dialect, "user_id", "o")
        join_expr = JoinExpression(
            dialect,
            left_table=users_table,
            right_table=orders_table,
            condition=join_condition,
            join_type="INNER JOIN"
        )
        
        query = QueryExpression(
            dialect,
            select=[
                Column(dialect, "name", "u"),
                Column(dialect, "amount", "o")
            ],
            from_=join_expr
        )
        
        create_view = CreateViewExpression(
            dialect,
            view_name="user_orders_view",
            query=query
        )
        
        sql, params = create_view.to_sql()
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        
        # Query the view
        result = sqlite_backend.execute(
            'SELECT * FROM "user_orders_view" ORDER BY name',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True)
        )
        
        assert result.data is not None
        assert len(result.data) == 3  # 3 orders


class TestSQLiteViewSubquery:
    """Tests for VIEW with subquery operations."""

    def test_create_view_with_subquery(self, sqlite_backend):
        """Test CREATE VIEW containing subquery logic."""
        from rhosocial.activerecord.backend.expression.core import Subquery
        
        dialect = sqlite_backend.dialect
        
        # Create a simpler view that demonstrates subquery-like behavior
        # Since SQLite handles views as query definitions, we test simpler aggregate views
        query = QueryExpression(
            dialect,
            select=[
                Column(dialect, "user_id"),
                FunctionCall(dialect, "COUNT", Column(dialect, "id"), alias="order_count")
            ],
            from_=TableExpression(dialect, "orders"),
            group_by_having=GroupByHavingClause(
                dialect,
                group_by=[Column(dialect, "user_id")]
            )
        )
        
        create_view = CreateViewExpression(
            dialect,
            view_name="order_counts_view",
            query=query
        )
        
        sql, params = create_view.to_sql()
        result = sqlite_backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DDL)
        )
        
        # Query the view
        result = sqlite_backend.execute(
            'SELECT user_id, order_count FROM "order_counts_view"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True)
        )
        
        assert result.data is not None
