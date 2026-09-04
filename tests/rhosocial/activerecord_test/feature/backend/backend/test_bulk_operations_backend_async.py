# tests/rhosocial/activerecord_test/feature/backend/backend/test_bulk_operations_backend_async.py
"""Async twin of test_bulk_operations_backend.py: bulk_insert/bulk_update on AsyncSQLiteBackend."""

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import BulkInsertOptions, BulkUpdateOptions
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestAsyncBulkInsert:
    """Test backend.bulk_insert (multi-row single-statement INSERT) on AsyncSQLiteBackend."""

    @pytest_asyncio.fixture
    async def backend(self):
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        await backend.introspect_and_adapt()
        await backend.execute(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_bulk_insert_multiple_rows(self, backend):
        """Multiple rows are inserted in a single statement."""
        options = BulkInsertOptions(
            table="items",
            columns=["id", "name", "qty"],
            rows=[[1, "a", 10], [2, "b", 20], [3, "c", 30]],
        )
        result = await backend.bulk_insert(options)

        assert result.affected_rows == 3
        rows = await backend.fetch_all("SELECT * FROM items ORDER BY id")
        assert [r["name"] for r in rows] == ["a", "b", "c"]
        assert [r["qty"] for r in rows] == [10, 20, 30]

    @pytest.mark.asyncio
    async def test_bulk_insert_column_subset(self, backend):
        """Inserting a column subset leaves other columns NULL."""
        options = BulkInsertOptions(
            table="items",
            columns=["id", "name"],
            rows=[[4, "d"]],
        )
        result = await backend.bulk_insert(options)
        assert result.affected_rows == 1

        row = await backend.fetch_one("SELECT * FROM items WHERE id = 4")
        assert row["name"] == "d"
        assert row["qty"] is None

    @pytest.mark.asyncio
    async def test_bulk_insert_empty_rows_rejected(self, backend):
        """Empty row list is rejected by the VALUES source contract."""
        options = BulkInsertOptions(table="items", columns=["id", "name", "qty"], rows=[])
        with pytest.raises(ValueError, match="non-empty"):
            await backend.bulk_insert(options)

    @pytest.mark.asyncio
    async def test_bulk_insert_returning_columns(self, backend):
        """RETURNING columns are processed when requested (SQLite 3.35+)."""
        options = BulkInsertOptions(
            table="items",
            columns=["id", "name", "qty"],
            rows=[[5, "e", 50]],
            returning_columns=["id", "name"],
        )
        result = await backend.bulk_insert(options)
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["id"] == 5
        assert result.data[0]["name"] == "e"

    @pytest.mark.asyncio
    async def test_bulk_insert_no_autocommit_inside_transaction(self, backend):
        """auto_commit=False inside an open transaction leaves the transaction active."""
        await backend.begin_transaction()
        options = BulkInsertOptions(
            table="items",
            columns=["id", "name", "qty"],
            rows=[[6, "f", 60]],
            auto_commit=False,
        )
        await backend.bulk_insert(options)
        assert backend.in_transaction is True
        await backend.rollback_transaction()


class TestAsyncBulkUpdate:
    """Test backend.bulk_update (single-statement CASE WHEN UPDATE) on AsyncSQLiteBackend."""

    @pytest_asyncio.fixture
    async def backend(self):
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()
        await backend.introspect_and_adapt()
        await backend.execute(
            "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, qty INTEGER)",
            options=ExecutionOptions(stmt_type=StatementType.DDL),
        )
        await backend.execute_many(
            "INSERT INTO items (id, name, qty) VALUES (?, ?, ?)",
            [(1, "old1", 1), (2, "old2", 2), (3, "old3", 3)],
        )
        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_bulk_update_single_field(self, backend):
        """CASE WHEN updates all matched rows in one statement."""
        options = BulkUpdateOptions(
            table="items",
            pk_column="id",
            pk_values=[1, 2, 3],
            field_values={"qty": [100, 200, 300]},
        )
        result = await backend.bulk_update(options)
        assert result.affected_rows == 3

        rows = await backend.fetch_all("SELECT * FROM items ORDER BY id")
        assert [r["qty"] for r in rows] == [100, 200, 300]
        assert [r["name"] for r in rows] == ["old1", "old2", "old3"]

    @pytest.mark.asyncio
    async def test_bulk_update_multiple_fields(self, backend):
        """Multiple fields are updated in the same statement."""
        options = BulkUpdateOptions(
            table="items",
            pk_column="id",
            pk_values=[1, 3],
            field_values={"name": ["new1", "new3"], "qty": [11, 33]},
        )
        result = await backend.bulk_update(options)
        assert result.affected_rows == 2

        rows = await backend.fetch_all("SELECT * FROM items ORDER BY id")
        assert rows[0]["name"] == "new1" and rows[0]["qty"] == 11
        assert rows[1]["name"] == "old2" and rows[1]["qty"] == 2
        assert rows[2]["name"] == "new3" and rows[2]["qty"] == 33

    @pytest.mark.asyncio
    async def test_bulk_update_no_matching_rows(self, backend):
        """PK values with no match update nothing."""
        options = BulkUpdateOptions(
            table="items",
            pk_column="id",
            pk_values=[999],
            field_values={"qty": [1]},
        )
        result = await backend.bulk_update(options)
        assert result.affected_rows == 0

    @pytest.mark.asyncio
    async def test_bulk_update_no_autocommit_inside_transaction(self, backend):
        """auto_commit=False inside an open transaction leaves the transaction active."""
        await backend.begin_transaction()
        options = BulkUpdateOptions(
            table="items",
            pk_column="id",
            pk_values=[1],
            field_values={"qty": [9]},
            auto_commit=False,
        )
        await backend.bulk_update(options)
        assert backend.in_transaction is True
        await backend.rollback_transaction()
