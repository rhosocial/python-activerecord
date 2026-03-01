# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_drop_index.py
import pytest
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import (
    CreateIndexExpression, DropIndexExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateDropIndexStatements:
    """Tests for CREATE INDEX and DROP INDEX statements."""

    def test_basic_create_index(self, dummy_dialect: DummyDialect):
        """Tests basic CREATE INDEX statement."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_users_email",
            table_name="users",
            columns=["email"]
        )
        sql, params = create_index.to_sql()

        assert 'CREATE INDEX "idx_users_email"' in sql
        assert 'ON "users"' in sql
        assert '"email"' in sql
        assert params == ()

    def test_create_unique_index(self, dummy_dialect: DummyDialect):
        """Tests CREATE UNIQUE INDEX statement."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_users_username",
            table_name="users",
            columns=["username"],
            unique=True
        )
        sql, params = create_index.to_sql()

        assert 'CREATE UNIQUE INDEX' in sql
        assert '"idx_users_username"' in sql
        assert 'ON "users"' in sql
        assert params == ()

    def test_create_index_if_not_exists(self, dummy_dialect: DummyDialect):
        """Tests CREATE INDEX IF NOT EXISTS statement."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_users_email",
            table_name="users",
            columns=["email"],
            if_not_exists=True
        )
        sql, params = create_index.to_sql()

        assert 'CREATE INDEX IF NOT EXISTS' in sql
        assert params == ()

    def test_create_composite_index(self, dummy_dialect: DummyDialect):
        """Tests CREATE INDEX with multiple columns."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_orders_user_date",
            table_name="orders",
            columns=["user_id", "created_at"]
        )
        sql, params = create_index.to_sql()

        assert 'CREATE INDEX "idx_orders_user_date"' in sql
        assert 'ON "orders"' in sql
        assert '"user_id"' in sql
        assert '"created_at"' in sql
        assert params == ()

    def test_create_index_with_type(self, dummy_dialect: DummyDialect):
        """Tests CREATE INDEX with index type."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_users_name_hash",
            table_name="users",
            columns=["name"],
            index_type="HASH"
        )
        sql, params = create_index.to_sql()

        assert 'USING HASH' in sql
        assert params == ()

    def test_create_index_with_where_clause(self, dummy_dialect: DummyDialect):
        """Tests CREATE INDEX with WHERE clause (partial index)."""
        where_condition = Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_active_users",
            table_name="users",
            columns=["email"],
            where=where_condition
        )
        sql, params = create_index.to_sql()

        assert 'CREATE INDEX "idx_active_users"' in sql
        assert 'WHERE "status" = ?' in sql
        assert params == ("active",)

    def test_create_index_with_include(self, dummy_dialect: DummyDialect):
        """Tests CREATE INDEX with INCLUDE clause."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_users_email",
            table_name="users",
            columns=["email"],
            include=["id", "name"]
        )
        sql, params = create_index.to_sql()

        assert 'INCLUDE ("id", "name")' in sql
        assert params == ()

    def test_create_index_with_tablespace(self, dummy_dialect: DummyDialect):
        """Tests CREATE INDEX with TABLESPACE."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_large_table",
            table_name="large_table",
            columns=["id"],
            tablespace="fast_ssd"
        )
        sql, params = create_index.to_sql()

        assert 'TABLESPACE "fast_ssd"' in sql
        assert params == ()

    def test_create_index_with_expression_column(self, dummy_dialect: DummyDialect):
        """Tests CREATE INDEX with expression as column."""
        from rhosocial.activerecord.backend.expression import FunctionCall
        lower_expr = FunctionCall(dummy_dialect, "LOWER", Column(dummy_dialect, "email"))
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_users_email_lower",
            table_name="users",
            columns=[lower_expr]
        )
        sql, params = create_index.to_sql()

        assert 'LOWER("email")' in sql
        assert params == ()

    def test_basic_drop_index(self, dummy_dialect: DummyDialect):
        """Tests basic DROP INDEX statement."""
        drop_index = DropIndexExpression(
            dummy_dialect,
            index_name="idx_users_email"
        )
        sql, params = drop_index.to_sql()

        assert sql == 'DROP INDEX "idx_users_email"'
        assert params == ()

    def test_drop_index_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP INDEX IF EXISTS statement."""
        drop_index = DropIndexExpression(
            dummy_dialect,
            index_name="idx_old_index",
            if_exists=True
        )
        sql, params = drop_index.to_sql()

        assert sql == 'DROP INDEX IF EXISTS "idx_old_index"'
        assert params == ()

    def test_drop_index_with_table_name(self, dummy_dialect: DummyDialect):
        """Tests DROP INDEX with table context."""
        drop_index = DropIndexExpression(
            dummy_dialect,
            index_name="idx_orders_status",
            table_name="orders"
        )
        sql, params = drop_index.to_sql()

        assert sql == 'DROP INDEX "idx_orders_status" ON "orders"'
        assert params == ()

    def test_drop_index_if_exists_with_table_name(self, dummy_dialect: DummyDialect):
        """Tests DROP INDEX IF EXISTS with table context."""
        drop_index = DropIndexExpression(
            dummy_dialect,
            index_name="idx_old_index",
            table_name="old_table",
            if_exists=True
        )
        sql, params = drop_index.to_sql()

        assert sql == 'DROP INDEX IF EXISTS "idx_old_index" ON "old_table"'
        assert params == ()

    def test_index_roundtrip_creation_and_deletion(self, dummy_dialect: DummyDialect):
        """Tests creating an index and then dropping it."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_test",
            table_name="test_table",
            columns=["id"]
        )
        create_sql, create_params = create_index.to_sql()

        drop_index = DropIndexExpression(
            dummy_dialect,
            index_name="idx_test"
        )
        drop_sql, drop_params = drop_index.to_sql()

        assert 'CREATE INDEX "idx_test"' in create_sql
        assert 'DROP INDEX "idx_test"' == drop_sql
        assert create_params == ()
        assert drop_params == ()

    @pytest.mark.parametrize("index_name,expected_identifier", [
        pytest.param("simple_index", '"simple_index"', id="simple_name"),
        pytest.param("index_with_underscores", '"index_with_underscores"', id="underscore_name"),
        pytest.param("IndexWithCamelCase", '"IndexWithCamelCase"', id="camelcase_name"),
        pytest.param("index-with-hyphens", '"index-with-hyphens"', id="hyphen_name"),
    ])
    def test_create_index_various_names(self, dummy_dialect: DummyDialect, index_name, expected_identifier):
        """Tests CREATE INDEX with various index name formats."""
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name=index_name,
            table_name="users",
            columns=["id"]
        )
        sql, params = create_index.to_sql()

        assert f'CREATE INDEX {expected_identifier}' in sql
        assert params == ()

    def test_create_index_all_options(self, dummy_dialect: DummyDialect):
        """Tests CREATE INDEX with all options."""
        where_condition = Column(dummy_dialect, "active") == Literal(dummy_dialect, True)
        create_index = CreateIndexExpression(
            dummy_dialect,
            index_name="idx_complex",
            table_name="users",
            columns=["email", "username"],
            unique=True,
            if_not_exists=True,
            index_type="BTREE",
            where=where_condition,
            include=["created_at"],
            tablespace="index_space"
        )
        sql, params = create_index.to_sql()

        assert 'CREATE UNIQUE INDEX IF NOT EXISTS' in sql
        assert 'USING BTREE' in sql
        assert '"email"' in sql
        assert '"username"' in sql
        assert 'INCLUDE' in sql
        assert 'WHERE "active" = ?' in sql
        assert 'TABLESPACE' in sql
        assert params == (True,)
