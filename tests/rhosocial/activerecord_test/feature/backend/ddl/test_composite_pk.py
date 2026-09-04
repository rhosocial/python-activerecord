# tests/rhosocial/activerecord_test/feature/backend/ddl/test_composite_pk.py
import pytest
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.errors import IntegrityError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

_SETUP_STMTS = [
    """CREATE TABLE order_items (
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (order_id, product_id))""",
    "INSERT INTO order_items VALUES (1,101,2),(1,102,1),(2,101,5)",
]
_CLEANUP_STMTS = ["DROP TABLE IF EXISTS order_items"]


@pytest.fixture
def composite_pk_backend(sqlite_file_backend: SQLiteBackend):
    for stmt in _SETUP_STMTS:
        sqlite_file_backend.execute(stmt)
    yield sqlite_file_backend
    for stmt in _CLEANUP_STMTS:
        sqlite_file_backend.execute(stmt)


class TestCompositePKDDL:
    def test_create_table(self, composite_pk_backend: SQLiteBackend):
        result = composite_pk_backend.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='order_items'",
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert len(result.data) == 1

    def test_insert_unique_constraint(self, composite_pk_backend: SQLiteBackend):
        with pytest.raises(IntegrityError):
            composite_pk_backend.execute(
                "INSERT INTO order_items VALUES (1, 101, 99)"
            )


class TestCompositePKDML:
    def test_update_by_composite_pk(self, composite_pk_backend: SQLiteBackend):
        composite_pk_backend.execute(
            "UPDATE order_items SET quantity = 99 WHERE order_id = 1 AND product_id = 101"
        )
        result = composite_pk_backend.execute(
            "SELECT quantity FROM order_items WHERE order_id = 1 AND product_id = 101",
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result.data[0]["quantity"] == 99
        result = composite_pk_backend.execute(
            "SELECT quantity FROM order_items WHERE order_id = 1 AND product_id = 102",
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result.data[0]["quantity"] == 1

    def test_delete_by_composite_pk(self, composite_pk_backend: SQLiteBackend):
        composite_pk_backend.execute(
            "DELETE FROM order_items WHERE order_id = 1 AND product_id = 101"
        )
        result = composite_pk_backend.execute(
            "SELECT COUNT(*) as cnt FROM order_items",
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result.data[0]["cnt"] == 2


class TestCompositePKExplain:
    def test_explain_pk_lookup(self, composite_pk_backend: SQLiteBackend):
        result = composite_pk_backend.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM order_items WHERE order_id = 1 AND product_id = 101",
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        explain_text = " ".join(str(row) for row in result.data)
        assert "USING" in explain_text

    def test_explain_prefix_only(self, composite_pk_backend: SQLiteBackend):
        result = composite_pk_backend.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM order_items WHERE order_id = 1",
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )
        assert result is not None


class TestCompositePKReturning:
    def test_returning_insert(self, composite_pk_backend: SQLiteBackend):
        dialect = composite_pk_backend.dialect
        if not dialect.supports_returning_insert():
            pytest.skip("SQLite version does not support RETURNING")
        result = composite_pk_backend.execute(
            "INSERT INTO order_items VALUES (3, 201, 7) RETURNING order_id, product_id",
            options=ExecutionOptions(stmt_type=StatementType.DML, process_result_set=True),
        )
        assert len(result.data) == 1
        row = result.data[0]
        assert row["order_id"] == 3
        assert row["product_id"] == 201
