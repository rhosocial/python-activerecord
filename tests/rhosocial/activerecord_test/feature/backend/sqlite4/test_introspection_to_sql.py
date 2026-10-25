# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_to_sql.py
"""
Tests to cover missing lines in expression/introspection.py.
Uses SQLiteDialect which supports introspection format methods.

Targets all to_sql() delegation methods and IntrospectionExpression base.
"""

import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.introspection import (
    IntrospectionExpression,
    DatabaseInfoQueryStatement,
    TableListQueryStatement,
    TableInfoQueryStatement,
    ColumnInfoQueryStatement,
    IndexInfoQueryStatement,
    ForeignKeyQueryStatement,
    ViewListQueryStatement,
    ViewInfoQueryStatement,
    TriggerListQueryStatement,
    TriggerInfoQueryStatement,
)


@pytest.fixture
def sqlite_dialect():
    return SQLiteDialect(version=(3, 35, 0))


class TestIntrospectionExpressionBase:
    """Cover IntrospectionExpression.to_sql() raising NotImplementedError."""

    def test_base_to_sql_raises_not_implemented(self, sqlite_dialect):
        expr = IntrospectionExpression(sqlite_dialect)
        with pytest.raises(NotImplementedError):
            expr.to_sql()


class TestDatabaseInfoToSql:
    """Cover DatabaseInfoQueryStatement.to_sql() delegation."""

    def test_database_info_to_sql(self, sqlite_dialect):
        expr = DatabaseInfoQueryStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert len(sql) > 0


class TestTableListToSql:
    """Cover TableListQueryStatement.to_sql() delegation."""

    def test_table_list_to_sql(self, sqlite_dialect):
        expr = TableListQueryStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_include_system(self, sqlite_dialect):
        expr = TableListQueryStatement(sqlite_dialect, include_system=True)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["include_system"] is True

    def test_table_type(self, sqlite_dialect):
        expr = TableListQueryStatement(sqlite_dialect, table_type="TABLE")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["table_type"] == "TABLE"


class TestTableInfoToSql:
    """Cover TableInfoQueryStatement.to_sql() delegation."""

    def test_table_info_to_sql(self, sqlite_dialect):
        expr = TableInfoQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert len(sql) > 0

    def test_include_indexes(self, sqlite_dialect):
        expr = TableInfoQueryStatement(sqlite_dialect, table_name="users", include_indexes=False)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["include_indexes"] is False

    def test_include_foreign_keys(self, sqlite_dialect):
        expr = TableInfoQueryStatement(
            sqlite_dialect, table_name="users", include_foreign_keys=False
        )
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["include_foreign_keys"] is False


class TestColumnInfoToSql:
    """Cover ColumnInfoQueryStatement.to_sql() delegation."""

    def test_column_info_to_sql(self, sqlite_dialect):
        expr = ColumnInfoQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name(self, sqlite_dialect):
        expr = ColumnInfoQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["table_name"] == "users"

    def test_include_hidden(self, sqlite_dialect):
        expr = ColumnInfoQueryStatement(sqlite_dialect, table_name="users", include_hidden=True)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["include_hidden"] is True


class TestIndexInfoToSql:
    """Cover IndexInfoQueryStatement.to_sql() delegation."""

    def test_index_info_to_sql(self, sqlite_dialect):
        expr = IndexInfoQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name(self, sqlite_dialect):
        expr = IndexInfoQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["table_name"] == "users"


class TestForeignKeyToSql:
    """Cover ForeignKeyQueryStatement.to_sql() delegation."""

    def test_foreign_key_to_sql(self, sqlite_dialect):
        expr = ForeignKeyQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name(self, sqlite_dialect):
        expr = ForeignKeyQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["table_name"] == "users"


class TestViewListToSql:
    """Cover ViewListQueryStatement.to_sql() delegation."""

    def test_view_list_to_sql(self, sqlite_dialect):
        expr = ViewListQueryStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)


class TestViewInfoToSql:
    """Cover ViewInfoQueryStatement.to_sql() delegation."""

    def test_view_info_to_sql(self, sqlite_dialect):
        expr = ViewInfoQueryStatement(sqlite_dialect, view_name="user_summary")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_view_name(self, sqlite_dialect):
        expr = ViewInfoQueryStatement(sqlite_dialect, view_name="user_summary")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["view_name"] == "user_summary"

    def test_include_columns(self, sqlite_dialect):
        expr = ViewInfoQueryStatement(
            sqlite_dialect, view_name="user_summary", include_columns=False
        )
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["include_columns"] is False


class TestTriggerListToSql:
    """Cover TriggerListQueryStatement.to_sql() delegation."""

    def test_trigger_list_to_sql(self, sqlite_dialect):
        expr = TriggerListQueryStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)


class TestTriggerInfoToSql:
    """Cover TriggerInfoQueryStatement.to_sql() delegation."""

    def test_trigger_info_to_sql(self, sqlite_dialect):
        expr = TriggerInfoQueryStatement(sqlite_dialect, trigger_name="update_ts")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_trigger_name(self, sqlite_dialect):
        expr = TriggerInfoQueryStatement(sqlite_dialect, trigger_name="update_ts")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["trigger_name"] == "update_ts"

    def test_trigger_table_name(self, sqlite_dialect):
        expr = TriggerInfoQueryStatement(
            sqlite_dialect, trigger_name="update_ts", table_name="users"
        )
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert expr.get_params()["table_name"] == "users"


class TestSqliteTableCountToSql:
    """Cover SQLiteTableCountStatement.to_sql() delegation."""

    def test_counts_tables_of_the_default_database(self, sqlite_dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
            SQLiteTableCountStatement,
        )

        sql, params = SQLiteTableCountStatement(sqlite_dialect).to_sql()

        assert sql == (
            'SELECT COUNT(*) AS "table_count" FROM main.sqlite_master '
            """WHERE "type" = 'table' AND "name" NOT LIKE 'sqlite_%'"""
        )
        assert params == ()

    def test_names_the_database_it_counts(self, sqlite_dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
            SQLiteTableCountStatement,
        )

        expr = SQLiteTableCountStatement(sqlite_dialect, "aux")
        sql, params = expr.to_sql()

        assert "FROM aux.sqlite_master" in sql
        assert expr.get_params() == {"schema": "aux"}


class TestSqliteTableDdlToSql:
    """Cover SQLiteTableDdlStatement.to_sql() delegation."""

    def test_reads_the_stored_statement(self, sqlite_dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
            SQLiteTableDdlStatement,
        )

        sql, params = SQLiteTableDdlStatement(sqlite_dialect, "users").to_sql()

        assert sql == (
            'SELECT "sql" FROM main.sqlite_master '
            """WHERE "type" = 'table' AND "name" = ? AND "tbl_name" = ?"""
        )
        assert params == ("users", "users")

    def test_names_the_database_it_reads(self, sqlite_dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
            SQLiteTableDdlStatement,
        )

        expr = SQLiteTableDdlStatement(sqlite_dialect, "users", "aux")
        sql, params = expr.to_sql()

        assert "FROM aux.sqlite_master" in sql
        assert expr.get_params() == {"table_name": "users", "schema": "aux"}


class TestSqliteIndexDdlToSql:
    """Cover SQLiteIndexDdlStatement.to_sql() delegation."""

    def test_reads_the_stored_statement(self, sqlite_dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
            SQLiteIndexDdlStatement,
        )

        sql, params = SQLiteIndexDdlStatement(sqlite_dialect, "idx_users_email").to_sql()

        assert sql == (
            'SELECT "sql" FROM main.sqlite_master ' """WHERE "type" = 'index' AND "name" = ?"""
        )
        assert params == ("idx_users_email",)

    def test_names_the_database_it_reads(self, sqlite_dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
            SQLiteIndexDdlStatement,
        )

        expr = SQLiteIndexDdlStatement(sqlite_dialect, "idx_users_email", "aux")
        sql, params = expr.to_sql()

        assert "FROM aux.sqlite_master" in sql
        assert expr.get_params() == {"index_name": "idx_users_email", "schema": "aux"}
