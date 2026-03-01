#!/usr/bin/env python3
# scripts/verify_ddl_documentation.py
"""
验证 DDL 文档示例的脚本。

此脚本验证 docs/en_US/backend/expression/statements.md 和
docs/zh_CN/backend/expression/statements.md 中新增的 DDL 表达式示例。
"""
import sys
sys.path.insert(0, 'src')

from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression import (
    Column, Literal, QueryExpression, TableExpression, TruncateExpression
)
from rhosocial.activerecord.backend.expression.statements import (
    CreateSchemaExpression, DropSchemaExpression,
    CreateIndexExpression, DropIndexExpression,
    CreateSequenceExpression, DropSequenceExpression, AlterSequenceExpression
)


def verify_section(name: str):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f" {name}")
    print('='*60)


def verify_test(name: str, sql: str, params: tuple, expected_sql: str, expected_params: tuple):
    """验证测试结果"""
    sql_match = expected_sql in sql if expected_sql else True
    params_match = params == expected_params
    
    status = "✓" if sql_match and params_match else "✗"
    print(f"\n{status} {name}")
    print(f"  SQL:    {sql}")
    print(f"  Params: {params}")
    
    if not sql_match:
        print(f"  ERROR: Expected '{expected_sql}' in SQL")
    if not params_match:
        print(f"  ERROR: Expected params {expected_params}")
    
    return sql_match and params_match


def main():
    dialect = DummyDialect()
    all_passed = True
    
    print("="*60)
    print(" DDL 文档示例验证")
    print("="*60)
    
    # =========================================
    # TruncateExpression
    # =========================================
    verify_section("TruncateExpression")
    
    truncate = TruncateExpression(dialect, table_name="logs")
    sql, params = truncate.to_sql()
    all_passed &= verify_test("基本 TRUNCATE", sql, params, 'TRUNCATE TABLE "logs"', ())
    
    truncate = TruncateExpression(
        dialect,
        table_name="orders",
        restart_identity=True,
        cascade=True
    )
    sql, params = truncate.to_sql()
    all_passed &= verify_test("带 RESTART IDENTITY 和 CASCADE", sql, params, 'TRUNCATE TABLE "orders"', ())
    all_passed &= "RESTART IDENTITY" in sql and "CASCADE" in sql
    
    # =========================================
    # Schema DDL
    # =========================================
    verify_section("Schema DDL")
    
    create_schema = CreateSchemaExpression(dialect, schema_name="my_schema")
    sql, params = create_schema.to_sql()
    all_passed &= verify_test("基本 CREATE SCHEMA", sql, params, 'CREATE SCHEMA "my_schema"', ())
    
    create_schema = CreateSchemaExpression(
        dialect,
        schema_name="app_schema",
        if_not_exists=True,
        authorization="app_user"
    )
    sql, params = create_schema.to_sql()
    all_passed &= verify_test("CREATE SCHEMA IF NOT EXISTS with AUTHORIZATION", sql, params, 'CREATE SCHEMA', ())
    all_passed &= "IF NOT EXISTS" in sql and "AUTHORIZATION" in sql
    
    drop_schema = DropSchemaExpression(
        dialect,
        schema_name="old_schema",
        if_exists=True,
        cascade=True
    )
    sql, params = drop_schema.to_sql()
    all_passed &= verify_test("DROP SCHEMA with CASCADE", sql, params, 'DROP SCHEMA', ())
    all_passed &= "IF EXISTS" in sql and "CASCADE" in sql
    
    # =========================================
    # Index DDL
    # =========================================
    verify_section("Index DDL")
    
    create_index = CreateIndexExpression(
        dialect,
        index_name="idx_users_email",
        table_name="users",
        columns=["email"]
    )
    sql, params = create_index.to_sql()
    all_passed &= verify_test("基本 CREATE INDEX", sql, params, 'CREATE INDEX', ())
    all_passed &= '"idx_users_email"' in sql and '"users"' in sql and '"email"' in sql
    
    create_index = CreateIndexExpression(
        dialect,
        index_name="idx_active_users",
        table_name="users",
        columns=["email"],
        unique=True,
        where=Column(dialect, "status") == Literal(dialect, "active")
    )
    sql, params = create_index.to_sql()
    all_passed &= verify_test("UNIQUE INDEX with WHERE", sql, params, 'CREATE UNIQUE INDEX', ("active",))
    all_passed &= "WHERE" in sql
    
    create_index = CreateIndexExpression(
        dialect,
        index_name="idx_orders_user_date",
        table_name="orders",
        columns=["user_id", "created_at"],
        index_type="BTREE"
    )
    sql, params = create_index.to_sql()
    all_passed &= verify_test("复合索引 with index type", sql, params, 'USING BTREE', ())
    
    create_index = CreateIndexExpression(
        dialect,
        index_name="idx_users_email",
        table_name="users",
        columns=["email"],
        include=["id", "name"]
    )
    sql, params = create_index.to_sql()
    all_passed &= verify_test("INDEX with INCLUDE", sql, params, 'INCLUDE', ())
    all_passed &= '"id"' in sql and '"name"' in sql
    
    drop_index = DropIndexExpression(
        dialect,
        index_name="idx_old_index",
        if_exists=True,
        table_name="users"
    )
    sql, params = drop_index.to_sql()
    all_passed &= verify_test("DROP INDEX", sql, params, 'DROP INDEX IF EXISTS', ())
    all_passed &= '"idx_old_index"' in sql and 'ON "users"' in sql
    
    # =========================================
    # Sequence DDL
    # =========================================
    verify_section("Sequence DDL")
    
    create_seq = CreateSequenceExpression(dialect, sequence_name="user_id_seq")
    sql, params = create_seq.to_sql()
    all_passed &= verify_test("基本 CREATE SEQUENCE", sql, params, 'CREATE SEQUENCE', ())
    all_passed &= '"user_id_seq"' in sql
    
    create_seq = CreateSequenceExpression(
        dialect,
        sequence_name="order_seq",
        if_not_exists=True,
        start=1000,
        increment=1,
        minvalue=1000,
        maxvalue=999999,
        cycle=True,
        cache=20,
        owned_by="orders.id"
    )
    sql, params = create_seq.to_sql()
    all_passed &= verify_test("CREATE SEQUENCE with all options", sql, params, 'CREATE SEQUENCE', ())
    all_passed &= all(opt in sql for opt in ["IF NOT EXISTS", "START WITH 1000", "INCREMENT BY 1", 
                                              "MINVALUE 1000", "MAXVALUE 999999", "CYCLE", 
                                              "CACHE 20", "OWNED BY orders.id"])
    
    drop_seq = DropSequenceExpression(dialect, sequence_name="old_seq", if_exists=True)
    sql, params = drop_seq.to_sql()
    all_passed &= verify_test("DROP SEQUENCE", sql, params, 'DROP SEQUENCE IF EXISTS', ())
    
    alter_seq = AlterSequenceExpression(dialect, sequence_name="user_id_seq", restart=1000)
    sql, params = alter_seq.to_sql()
    all_passed &= verify_test("ALTER SEQUENCE restart", sql, params, 'ALTER SEQUENCE', ())
    all_passed &= "RESTART WITH 1000" in sql
    
    alter_seq = AlterSequenceExpression(
        dialect,
        sequence_name="order_seq",
        increment=2,
        maxvalue=1000000,
        cycle=True
    )
    sql, params = alter_seq.to_sql()
    all_passed &= verify_test("ALTER SEQUENCE multiple changes", sql, params, 'ALTER SEQUENCE', ())
    all_passed &= all(opt in sql for opt in ["INCREMENT BY 2", "MAXVALUE 1000000", "CYCLE"])
    
    # =========================================
    # 总结
    # =========================================
    print("\n" + "="*60)
    if all_passed:
        print(" ✓ 所有验证通过！")
    else:
        print(" ✗ 部分验证失败！")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
