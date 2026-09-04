# tests/rhosocial/activerecord_test/feature/basic/ddl/test_typed_model_ddl.py
"""Cross-backend UseSqlType demonstration — SQLite rendering.

The same model (``TypedUser``) is exercised in the mysql and postgres backend
repositories; this file pins the SQLite rendering. Types are core **generic**
types, so each backend renders its native form without per-dialect mappings.
"""

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.examples.ddl_types import TypedUser


def _render() -> str:
    sql, _ = TypedUser.generate_create_table(dialect=SQLiteDialect()).to_sql()
    return sql


def test_sqlite_typed_user_ddl_columns():
    sql = _render()
    assert 'CREATE TABLE "typed_users"' in sql
    assert '"id" INTEGER PRIMARY KEY AUTOINCREMENT' in sql
    assert '"username" TEXT NOT NULL' in sql
    assert '"email" TEXT NOT NULL' in sql
    assert '"is_active" NUMERIC NOT NULL' in sql
    assert '"balance" NUMERIC' in sql
    assert '"birthday" NUMERIC' in sql
    assert '"created_at" NUMERIC NOT NULL' in sql
    assert '"bio" TEXT' in sql
    assert '"metadata" TEXT' in sql
    assert '"big_counter" INTEGER' in sql
    assert '"avatar" BLOB' in sql
    assert '"wake_up_time" NUMERIC' in sql


def test_sqlite_typed_user_no_per_dialect_string_keys():
    """UseSqlType carries single DataType instances — no dict mappings remain."""
    for _field_name, marker in TypedUser.__table_field_sql_types__.items():
        assert not hasattr(marker, "dialect_types")
        assert marker.data_type is not None