# tests/rhosocial/activerecord_test/feature/backend/views/test_view_execution_async.py
"""Async twin of test_view_execution.py using AsyncSQLiteBackend."""
import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    FunctionCall,
    TableExpression,
    QueryExpression,
    CreateViewExpression,
    DropViewExpression,
    CreateMaterializedViewExpression,
    DropMaterializedViewExpression,
    RefreshMaterializedViewExpression,
    CreateTableExpression,
    InsertExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraintType,
    ForeignKeyConstraint,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.operators import RawSQLPredicate, RawSQLExpression
from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause, WhereClause
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteIntegerType, SQLiteRealType, SQLiteTextType


@pytest_asyncio.fixture
async def sqlite_backend():
    """Provides an AsyncSQLiteBackend connected to an in-memory database with test tables and data."""
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    dialect = backend.dialect

    # Create users table using expression system
    users_columns = [
        ColumnDefinition(
            name="id",
            data_type=SQLiteIntegerType(),
            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)],
        ),
        ColumnDefinition(
            name="name", data_type=SQLiteTextType(), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        ),
        ColumnDefinition(name="email", data_type=SQLiteTextType()),
        ColumnDefinition(
            name="status",
            data_type=SQLiteTextType(),
            constraints=[
                ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=RawSQLExpression(dialect, "'active'"))
            ],
        ),
    ]

    create_users = CreateTableExpression(dialect, table="users", columns=users_columns)

    sql, params = create_users.to_sql()
    await backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create orders table using expression system
    orders_columns = [
        ColumnDefinition(
            name="id",
            data_type=SQLiteIntegerType(),
            constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)],
        ),
        ColumnDefinition(name="user_id", data_type=SQLiteIntegerType()),
        ColumnDefinition(name="amount", data_type=SQLiteRealType()),
        ColumnDefinition(name="order_date", data_type=SQLiteTextType()),
    ]

    orders_fk_constraint = ForeignKeyConstraint(
        constraint_type=TableConstraintType.FOREIGN_KEY,
        columns=["user_id"],
        foreign_key_table="users",
        foreign_key_columns=["id"],
    )

    create_orders = CreateTableExpression(
        dialect, table="orders", columns=orders_columns, table_constraints=[orders_fk_constraint]
    )

    sql, params = create_orders.to_sql()
    await backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Insert test data using expression system
    insert_users = [
        ("Alice", "alice@example.com", "active"),
        ("Bob", "bob@example.com", "inactive"),
        ("Charlie", "charlie@example.com", "active"),
    ]

    for name, email, status in insert_users:
        insert_expr = InsertExpression(
            dialect,
            into="users",
            source=ValuesSource(dialect, [[Literal(dialect, name), Literal(dialect, email), Literal(dialect, status)]]),
            columns=["name", "email", "status"],
        )
        sql, params = insert_expr.to_sql()
        await backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))

    insert_orders = [
        (1, 100.0, "2024-01-01"),
        (1, 200.0, "2024-01-15"),
        (2, 50.0, "2024-01-10"),
    ]

    for user_id, amount, order_date in insert_orders:
        insert_expr = InsertExpression(
            dialect,
            into="orders",
            source=ValuesSource(
                dialect, [[Literal(dialect, user_id), Literal(dialect, amount), Literal(dialect, order_date)]]
            ),
            columns=["user_id", "amount", "order_date"],
        )
        sql, params = insert_expr.to_sql()
        await backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))

    yield backend

    await backend.disconnect()


class TestAsyncSQLiteViewExecution:
    """Tests for CREATE VIEW and DROP VIEW with actual execution (async)."""

    @pytest.mark.asyncio
    async def test_create_view_basic(self, sqlite_backend):
        """Test basic CREATE VIEW executes successfully."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")],
            from_=TableExpression(dialect, "users"),
        )

        create_view = CreateViewExpression(dialect, view_name="user_view", query=query)

        sql, params = create_view.to_sql()

        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        result = await sqlite_backend.execute(
            'SELECT * FROM "user_view"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
        )

        assert result.data is not None
        assert len(result.data) == 3
        assert result.data[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_create_view_with_where(self, sqlite_backend):
        """Test CREATE VIEW with WHERE clause executes successfully."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(
            dialect,
            select=[Column(dialect, "id"), Column(dialect, "name")],
            from_=TableExpression(dialect, "users"),
            where=WhereClause(dialect, condition=RawSQLPredicate(dialect, "\"status\" = 'active'")),
        )

        create_view = CreateViewExpression(dialect, view_name="active_users", query=query)

        sql, params = create_view.to_sql()

        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        result = await sqlite_backend.execute(
            'SELECT * FROM "active_users"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
        )

        assert result.data is not None
        assert len(result.data) == 2

    @pytest.mark.asyncio
    async def test_create_view_with_aggregates(self, sqlite_backend):
        """Test CREATE VIEW with aggregate functions."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(
            dialect,
            select=[
                Column(dialect, "user_id"),
                FunctionCall(dialect, "SUM", Column(dialect, "amount"), alias="total_amount"),
                FunctionCall(dialect, "COUNT", Column(dialect, "id"), alias="order_count"),
            ],
            from_=TableExpression(dialect, "orders"),
            group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "user_id")]),
        )

        create_view = CreateViewExpression(dialect, view_name="user_order_summary", query=query)

        sql, params = create_view.to_sql()

        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        result = await sqlite_backend.execute(
            'SELECT * FROM "user_order_summary" ORDER BY user_id',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
        )

        assert result.data is not None
        assert len(result.data) == 2

    @pytest.mark.asyncio
    async def test_create_temporary_view(self, sqlite_backend):
        """Test CREATE TEMPORARY VIEW executes successfully."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(
            dialect, select=[Column(dialect, "id"), Column(dialect, "name")], from_=TableExpression(dialect, "users")
        )

        create_view = CreateViewExpression(dialect, view_name="temp_user_view", query=query, temporary=True)

        sql, params = create_view.to_sql()

        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        result = await sqlite_backend.execute(
            'SELECT * FROM "temp_user_view"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
        )

        assert result.data is not None
        assert len(result.data) == 3

    @pytest.mark.asyncio
    async def test_create_view_if_not_exists(self, sqlite_backend):
        """Test CREATE VIEW IF NOT EXISTS (SQLite's OR REPLACE equivalent)."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(dialect, select=[Column(dialect, "id")], from_=TableExpression(dialect, "users"))

        create_view = CreateViewExpression(dialect, view_name="test_view", query=query)

        sql, params = create_view.to_sql()
        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        create_view2 = CreateViewExpression(
            dialect,
            view_name="test_view",
            query=query,
            replace=True,  # This generates IF NOT EXISTS in SQLite
        )

        sql, params = create_view2.to_sql()

        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

    @pytest.mark.asyncio
    async def test_drop_view(self, sqlite_backend):
        """Test DROP VIEW executes successfully."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(dialect, select=[Column(dialect, "id")], from_=TableExpression(dialect, "users"))

        create_view = CreateViewExpression(dialect, view_name="view_to_drop", query=query)

        sql, params = create_view.to_sql()
        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        drop_view = DropViewExpression(dialect, view_name="view_to_drop")

        sql, params = drop_view.to_sql()
        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        with pytest.raises(Exception):  # Should raise OperationalError  # noqa: B017
            await sqlite_backend.execute(
                "SELECT * FROM view_to_drop", (), options=ExecutionOptions(stmt_type=StatementType.SELECT)
            )

    @pytest.mark.asyncio
    async def test_drop_view_if_exists(self, sqlite_backend):
        """Test DROP VIEW IF EXISTS executes without error for non-existent view."""
        dialect = sqlite_backend.dialect

        drop_view = DropViewExpression(dialect, view_name="nonexistent_view", if_exists=True)

        sql, params = drop_view.to_sql()

        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

    @pytest.mark.asyncio
    async def test_drop_view_if_exists_for_existing_view(self, sqlite_backend):
        """Test DROP VIEW IF EXISTS works for existing view."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(dialect, select=[Column(dialect, "id")], from_=TableExpression(dialect, "users"))

        create_view = CreateViewExpression(dialect, view_name="view_to_drop_if_exists", query=query)

        sql, params = create_view.to_sql()
        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        drop_view = DropViewExpression(dialect, view_name="view_to_drop_if_exists", if_exists=True)

        sql, params = drop_view.to_sql()
        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        with pytest.raises(Exception):  # noqa: B017
            await sqlite_backend.execute(
                "SELECT * FROM view_to_drop_if_exists", (), options=ExecutionOptions(stmt_type=StatementType.SELECT)
            )

    @pytest.mark.asyncio
    async def test_create_view_with_column_aliases(self, sqlite_backend):
        """Test CREATE VIEW with explicit column aliases."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(
            dialect, select=[Column(dialect, "id"), Column(dialect, "name")], from_=TableExpression(dialect, "users")
        )

        create_view = CreateViewExpression(
            dialect, view_name="aliased_view", query=query, column_aliases=["user_id", "user_name"]
        )

        sql, params = create_view.to_sql()
        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        result = await sqlite_backend.execute(
            'SELECT user_id, user_name FROM "aliased_view"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
        )

        assert result.data is not None


class TestAsyncSQLiteMaterializedViewExecution:
    """Tests for materialized view operations (should all fail)."""

    @pytest.mark.asyncio
    async def test_create_materialized_view_raises_error(self, sqlite_backend):
        """Test that CREATE MATERIALIZED VIEW raises UnsupportedFeatureError."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(dialect, select=[Column(dialect, "id")], from_=TableExpression(dialect, "users"))

        create_mv = CreateMaterializedViewExpression(dialect, view_name="test_mv", query=query)

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            create_mv.to_sql()

        assert "CREATE MATERIALIZED VIEW" in str(exc_info.value)
        assert "SQLite" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_drop_materialized_view_raises_error(self, sqlite_backend):
        """Test that DROP MATERIALIZED VIEW raises UnsupportedFeatureError."""
        dialect = sqlite_backend.dialect

        drop_mv = DropMaterializedViewExpression(dialect, view_name="test_mv")

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            drop_mv.to_sql()

        assert "DROP MATERIALIZED VIEW" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_refresh_materialized_view_raises_error(self, sqlite_backend):
        """Test that REFRESH MATERIALIZED VIEW raises UnsupportedFeatureError."""
        dialect = sqlite_backend.dialect

        refresh_mv = RefreshMaterializedViewExpression(dialect, view_name="test_mv")

        with pytest.raises(UnsupportedFeatureError) as exc_info:
            refresh_mv.to_sql()

        assert "REFRESH MATERIALIZED VIEW" in str(exc_info.value)


class TestAsyncSQLiteViewJoins:
    """Tests for VIEW with JOIN operations."""

    @pytest.mark.asyncio
    async def test_create_view_with_join(self, sqlite_backend):
        """Test CREATE VIEW with JOIN executes successfully."""
        from rhosocial.activerecord.backend.expression.query_parts import JoinExpression

        dialect = sqlite_backend.dialect

        users_table = TableExpression(dialect, "users", alias="u")
        orders_table = TableExpression(dialect, "orders", alias="o")

        join_condition = Column(dialect, "id", "u") == Column(dialect, "user_id", "o")
        join_expr = JoinExpression(
            dialect, left_table=users_table, right_table=orders_table, condition=join_condition, join_type="INNER JOIN"
        )

        query = QueryExpression(
            dialect, select=[Column(dialect, "name", "u"), Column(dialect, "amount", "o")], from_=join_expr
        )

        create_view = CreateViewExpression(dialect, view_name="user_orders_view", query=query)

        sql, params = create_view.to_sql()
        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        result = await sqlite_backend.execute(
            'SELECT * FROM "user_orders_view" ORDER BY name',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
        )

        assert result.data is not None
        assert len(result.data) == 3


class TestAsyncSQLiteViewSubquery:
    """Tests for VIEW with subquery operations."""

    @pytest.mark.asyncio
    async def test_create_view_with_subquery(self, sqlite_backend):
        """Test CREATE VIEW containing subquery logic."""
        dialect = sqlite_backend.dialect

        query = QueryExpression(
            dialect,
            select=[
                Column(dialect, "user_id"),
                FunctionCall(dialect, "COUNT", Column(dialect, "id"), alias="order_count"),
            ],
            from_=TableExpression(dialect, "orders"),
            group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "user_id")]),
        )

        create_view = CreateViewExpression(dialect, view_name="order_counts_view", query=query)

        sql, params = create_view.to_sql()
        await sqlite_backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DDL))

        result = await sqlite_backend.execute(
            'SELECT user_id, order_count FROM "order_counts_view"',
            (),
            options=ExecutionOptions(stmt_type=StatementType.SELECT, process_result_set=True),
        )

        assert result.data is not None
