# tests/rhosocial/activerecord_test/feature/basic/ddl/test_default_model_ddl.py
"""Default-type model rendering — SQLite.

``DefaultUser`` declares plain Python types with no ``UseSqlType``, so each
backend derives the column types via ``suggest_column_type``. This file pins
the SQLite result; sibling files cover MySQL, PostgreSQL and the other
backend repositories.
"""

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.examples.ddl_default_types import DefaultUser


def _render() -> str:
    sql, _ = DefaultUser.generate_create_table(dialect=SQLiteDialect()).to_sql()
    return sql


def test_default_user_has_no_explicit_sql_types():
    assert DefaultUser.__table_field_sql_types__ == {}


def test_sqlite_default_user_ddl_columns():
    sql = _render()
    assert 'CREATE TABLE "default_users"' in sql
    assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT' in sql
    assert '"username" TEXT NOT NULL' in sql
    assert '"email" TEXT NOT NULL' in sql
    assert '"is_active" NUMERIC NOT NULL' in sql
    assert '"balance" REAL NOT NULL' in sql
    assert '"created_at" NUMERIC NOT NULL' in sql
    assert '"metadata" TEXT NOT NULL' in sql
    assert '"avatar" BLOB NOT NULL' in sql
    assert '"birthday" NUMERIC' in sql