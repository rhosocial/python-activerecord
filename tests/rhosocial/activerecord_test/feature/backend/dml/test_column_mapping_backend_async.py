# tests/rhosocial/activerecord_test/feature/backend/dml/test_column_mapping_backend_async.py
"""Async twin of test_column_mapping_backend.py using AsyncSQLiteBackend."""
import pytest
import pytest_asyncio
import sqlite3
import uuid
from datetime import datetime

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.schema import StatementType


@pytest_asyncio.fixture
async def mapped_table_backend():
    """Set up an in-memory AsyncSQLiteBackend with a 'mapped_users' table for column mapping tests."""
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    await backend.introspect_and_adapt()

    create_table_sql = """
    CREATE TABLE mapped_users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP NOT NULL,
        user_uuid TEXT,
        is_active INTEGER
    );
    """
    await backend.executescript(create_table_sql)

    yield backend

    await backend.disconnect()


@pytest.mark.asyncio
async def test_insert_and_returning_with_mapping(mapped_table_backend):
    """Tests execute() with INSERT and RETURNING using column_mapping (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    column_to_field_mapping = {
        "user_id": "user_pk",
        "name": "full_name",
        "email": "user_email",
        "created_at": "created_timestamp",
    }

    sql = "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)"
    params = ("John Doe", "john.doe@example.com", now_str)

    result = await backend.execute(
        sql, params, options=ExecutionOptions(stmt_type=StatementType.INSERT, column_mapping=column_to_field_mapping)
    )
    assert result is not None


@pytest.mark.asyncio
async def test_update_with_backend(mapped_table_backend):
    """Tests that an update operation via execute() works correctly (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("Jane Doe", "jane.doe@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    sql = "UPDATE mapped_users SET name = ? WHERE user_id = ?"
    params = ("Jane Smith", 1)
    result = await backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.UPDATE))
    assert result.affected_rows == 1

    fetched_row = await backend.fetch_one("SELECT name FROM mapped_users WHERE user_id = 1")
    assert fetched_row is not None
    assert fetched_row["name"] == "Jane Smith"


@pytest.mark.asyncio
async def test_execute_fetch_with_mapping(mapped_table_backend):
    """Tests that fetch_one uses column_mapping to return field names as keys (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    column_to_field_mapping = {"user_id": "user_pk", "name": "full_name", "email": "user_email"}

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("Fetch Test", "fetch@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    fetched_row = await backend.fetch_one(
        "SELECT * FROM mapped_users WHERE user_id = 1", (), column_mapping=column_to_field_mapping
    )

    assert fetched_row is not None
    assert "full_name" in fetched_row
    assert "user_email" in fetched_row
    assert "created_at" in fetched_row
    assert fetched_row["full_name"] == "Fetch Test"
    assert fetched_row["user_pk"] == 1


@pytest.mark.asyncio
async def test_execute_fetch_without_mapping(mapped_table_backend):
    """Tests that fetch without column_mapping returns raw column names (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("No Map", "nomap@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    fetched_row = await backend.fetch_one("SELECT * FROM mapped_users WHERE user_id = 1")

    assert fetched_row is not None
    assert "user_id" in fetched_row
    assert "name" in fetched_row
    assert "full_name" not in fetched_row
    assert "user_pk" not in fetched_row
    assert fetched_row["name"] == "No Map"


@pytest.mark.asyncio
async def test_fetch_with_combined_mapping_and_adapters(mapped_table_backend):
    """Tests that fetch_one applies both column_mapping and column_adapters (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    test_uuid = uuid.uuid4()

    column_to_field_mapping = {"user_id": "pk", "name": "full_name", "user_uuid": "uuid", "is_active": "active"}

    uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
    bool_adapter = backend.adapter_registry.get_adapter(bool, int)

    column_adapters = {"user_uuid": (uuid_adapter, uuid.UUID), "is_active": (bool_adapter, bool)}

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at, user_uuid, is_active) VALUES (?, ?, ?, ?, ?)",
        ("Combined Test", "combined@example.com", now_str, str(test_uuid), 1),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    fetched_row = await backend.fetch_one(
        "SELECT * FROM mapped_users WHERE user_id = 1",
        (),
        column_mapping=column_to_field_mapping,
        column_adapters=column_adapters,
    )
    assert fetched_row is not None

    assert "full_name" in fetched_row
    assert "uuid" in fetched_row
    assert "active" in fetched_row
    assert "name" not in fetched_row
    assert "user_uuid" not in fetched_row

    assert fetched_row["full_name"] == "Combined Test"
    assert isinstance(fetched_row["uuid"], uuid.UUID)
    assert fetched_row["uuid"] == test_uuid
    assert isinstance(fetched_row["active"], bool)
    assert fetched_row["active"] is True


@pytest.mark.asyncio
async def test_insert_with_returning_columns_sql_construction(mapped_table_backend):
    """Tests SQL construction with RETURNING clause for insert (dialect calls are sync)."""
    from rhosocial.activerecord.backend.options import InsertOptions
    from rhosocial.activerecord.backend.expression.statements import ValuesSource
    from rhosocial.activerecord.backend.expression import Column as ExprColumn, Literal
    from rhosocial.activerecord.backend.base.operations import ReturningClause as BaseReturningClause

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    insert_options = InsertOptions(
        table="mapped_users",
        data={"name": "Returning Test", "email": "returning@example.com", "created_at": now_str},
        returning_columns=["user_id", "name", "email"],
    )

    columns = list(insert_options.data.keys())
    values = [Literal(backend.dialect, v) for v in insert_options.data.values()]
    values_source = ValuesSource(backend.dialect, [values])

    returning_clause = None
    if insert_options.returning_columns:
        returning_expressions = [ExprColumn(backend.dialect, col) for col in insert_options.returning_columns]
        returning_clause = BaseReturningClause(backend.dialect, returning_expressions)

    from rhosocial.activerecord.backend.expression import InsertExpression

    insert_expr = InsertExpression(
        dialect=backend.dialect,
        into=insert_options.table,
        source=values_source,
        columns=columns,
        returning=returning_clause,
    )

    sql, params = insert_expr.to_sql()

    assert "RETURNING" in sql.upper()
    assert "user_id" in sql
    assert "name" in sql
    assert "email" in sql


@pytest.mark.skipif(sqlite3.sqlite_version_info < (3, 35), reason="RETURNING clause requires SQLite 3.35+")
@pytest.mark.asyncio
async def test_insert_with_returning_columns_execution(mapped_table_backend):
    """Tests insert with RETURNING clause execution (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    sql = "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?) RETURNING user_id, name, email"
    params = ("Returning Test", "returning@example.com", now_str)

    result = await backend.execute(
        sql,
        params,
        options=ExecutionOptions(
            stmt_type=StatementType.DQL,  # Use DQL to ensure result set is processed
        ),
    )

    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert returned_row["name"] == "Returning Test"
    assert returned_row["email"] == "returning@example.com"
    assert isinstance(returned_row["user_id"], int)
    assert returned_row["user_id"] > 0


@pytest.mark.asyncio
async def test_update_with_returning_columns_sql_construction(mapped_table_backend):
    """Tests SQL construction with RETURNING clause for update (dialect calls are sync)."""
    from rhosocial.activerecord.backend.options import UpdateOptions, ExecutionOptions
    from rhosocial.activerecord.backend.expression import ComparisonPredicate, Column, Literal
    from rhosocial.activerecord.backend.base.operations import ReturningClause as BaseReturningClause

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("Update Test", "update@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    where_predicate = ComparisonPredicate(
        backend.dialect, "=", Column(backend.dialect, "name"), Literal(backend.dialect, "Update Test")
    )
    update_options = UpdateOptions(
        table="mapped_users",
        data={"name": "Updated Name", "email": "updated@example.com"},
        where=where_predicate,
        returning_columns=["user_id", "name", "email"],
    )

    assignments = {k: Literal(backend.dialect, v) for k, v in update_options.data.items()}

    returning_clause = None
    if update_options.returning_columns:
        from rhosocial.activerecord.backend.expression import Column as ExprColumn

        returning_expressions = [ExprColumn(backend.dialect, col) for col in update_options.returning_columns]
        returning_clause = BaseReturningClause(backend.dialect, returning_expressions)

    from rhosocial.activerecord.backend.expression import UpdateExpression

    update_expr = UpdateExpression(
        dialect=backend.dialect,
        table=update_options.table,
        assignments=assignments,
        where=update_options.where,
        returning=returning_clause,
    )

    sql, params = update_expr.to_sql()

    assert "RETURNING" in sql.upper()
    assert "user_id" in sql
    assert "name" in sql
    assert "email" in sql


@pytest.mark.skipif(sqlite3.sqlite_version_info < (3, 35), reason="RETURNING clause requires SQLite 3.35+")
@pytest.mark.asyncio
async def test_update_with_returning_columns_execution(mapped_table_backend):
    """Tests update with RETURNING clause execution (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("Update Test", "update@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    sql = "UPDATE mapped_users SET name = ?, email = ? WHERE name = ? RETURNING user_id, name, email"
    params = ("Updated Name", "updated@example.com", "Update Test")

    result = await backend.execute(
        sql,
        params,
        options=ExecutionOptions(
            stmt_type=StatementType.DQL,  # Use DQL to ensure result set is processed
        ),
    )

    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert returned_row["name"] == "Updated Name"
    assert returned_row["email"] == "updated@example.com"


@pytest.mark.asyncio
async def test_delete_with_returning_columns_sql_construction(mapped_table_backend):
    """Tests SQL construction with RETURNING clause for delete (dialect calls are sync)."""
    from rhosocial.activerecord.backend.options import DeleteOptions, ExecutionOptions
    from rhosocial.activerecord.backend.expression import ComparisonPredicate, Column, Literal
    from rhosocial.activerecord.backend.base.operations import ReturningClause as BaseReturningClause

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("Delete Test", "delete@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    where_predicate = ComparisonPredicate(
        backend.dialect, "=", Column(backend.dialect, "name"), Literal(backend.dialect, "Delete Test")
    )
    delete_options = DeleteOptions(
        table="mapped_users", where=where_predicate, returning_columns=["user_id", "name", "email"]
    )

    returning_clause = None
    if delete_options.returning_columns:
        from rhosocial.activerecord.backend.expression import Column as ExprColumn

        returning_expressions = [ExprColumn(backend.dialect, col) for col in delete_options.returning_columns]
        returning_clause = BaseReturningClause(backend.dialect, returning_expressions)

    from rhosocial.activerecord.backend.expression import DeleteExpression

    delete_expr = DeleteExpression(
        dialect=backend.dialect, tables=delete_options.table, where=delete_options.where, returning=returning_clause
    )

    sql, params = delete_expr.to_sql()

    assert "RETURNING" in sql.upper()
    assert "user_id" in sql
    assert "name" in sql
    assert "email" in sql


@pytest.mark.skipif(sqlite3.sqlite_version_info < (3, 35), reason="RETURNING clause requires SQLite 3.35+")
@pytest.mark.asyncio
async def test_delete_with_returning_columns_execution(mapped_table_backend):
    """Tests delete with RETURNING clause execution (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("Delete Test", "delete@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    sql = "DELETE FROM mapped_users WHERE name = ? RETURNING user_id, name, email"
    params = ("Delete Test",)

    result = await backend.execute(
        sql,
        params,
        options=ExecutionOptions(
            stmt_type=StatementType.DQL,  # Use DQL to ensure result set is processed
        ),
    )

    assert result is not None
    assert result.data is not None
    assert len(result.data) == 1

    returned_row = result.data[0]
    assert "user_id" in returned_row
    assert "name" in returned_row
    assert "email" in returned_row
    assert returned_row["name"] == "Delete Test"
    assert returned_row["email"] == "delete@example.com"


@pytest.mark.asyncio
async def test_returning_fetchall_impact_comparison(mapped_table_backend):
    """Tests the impact of result set processing on RETURNING operations (async)."""
    from rhosocial.activerecord.backend.options import ExecutionOptions

    backend = mapped_table_backend
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("Fetchall Test", "fetchall@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    sql = "UPDATE mapped_users SET name = ? WHERE name = ? RETURNING user_id, name, email"
    params = ("Fetchall Updated", "Fetchall Test")

    result_with_fetchall = await backend.execute(
        sql,
        params,
        options=ExecutionOptions(
            stmt_type=StatementType.DQL  # This will process result set and call fetchall
        ),
    )

    assert result_with_fetchall.data is not None
    assert len(result_with_fetchall.data) == 1
    assert result_with_fetchall.data[0]["name"] == "Fetchall Updated"

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("No Fetchall Test", "nofetchall@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    sql2 = "UPDATE mapped_users SET name = ? WHERE name = ? RETURNING user_id, name, email"
    params2 = ("No Fetchall Updated", "No Fetchall Test")

    result_without_processing = await backend.execute(
        sql2,
        params2,
        options=ExecutionOptions(
            stmt_type=StatementType.DML,  # DML type
            process_result_set=False,  # Explicitly set to False to not process result set
        ),
    )

    assert result_without_processing.data is None

    await backend.execute(
        "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
        ("Process Test", "processtest@example.com", now_str),
        options=ExecutionOptions(stmt_type=StatementType.INSERT),
    )

    sql3 = "UPDATE mapped_users SET name = ? WHERE name = ? RETURNING user_id, name, email"
    params3 = ("Processed Updated", "Process Test")

    result_with_processing = await backend.execute(
        sql3,
        params3,
        options=ExecutionOptions(
            stmt_type=StatementType.DML,  # DML type
            process_result_set=True,  # Explicitly set to True to process result set
        ),
    )

    assert result_with_processing.data is not None
    assert len(result_with_processing.data) == 1
    assert result_with_processing.data[0]["name"] == "Processed Updated"
    assert result_with_processing.data[0]["email"] == "processtest@example.com"
