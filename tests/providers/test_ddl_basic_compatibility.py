# tests/providers/test_ddl_basic_compatibility.py
"""
验证 DDL 表达式与 SQLite 现有 schema 文件兼容性。

这是过渡期验证：后端用自己的 DDL 表达式与现有 .sql 文件对比，
暴露 dialect 实现缺口。

运行：
    pytest tests/providers/test_ddl_basic_compatibility.py -v
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from providers.fixtures.basic import (
    create_users_table,
    create_type_cases_table,
    create_type_tests_table,
    create_validated_field_users_table,
    create_validated_users_table,
    create_pydantic_validated_models_table,
    create_bulk_users_table,
    create_posts_table,
    create_comments_table,
    create_column_mapping_items_table,
    create_mixed_annotation_items_table,
    create_type_adapter_tests_table,
)
from providers.ddl_verify import verify_table

DIALECT = SQLiteDialect(version=(3, 45, 0))
SCHEMA_DIR = Path(__file__).parent.parent / "rhosocial" / "activerecord_test" / "feature" / "basic" / "schema"

TABLE_CHECKS = [
    (create_users_table, "users", "users.sql"),
    (create_type_cases_table, "type_cases", "type_cases.sql"),
    (create_type_tests_table, "type_tests", "type_tests.sql"),
    (create_validated_field_users_table, "validated_field_users", "validated_field_users.sql"),
    (create_validated_users_table, "validated_users", "validated_users.sql"),
    (create_pydantic_validated_models_table, "pydantic_validated_models", "pydantic_validated_models.sql"),
    (create_bulk_users_table, "bulk_users", "bulk_users.sql"),
    (create_posts_table, "posts", "posts.sql"),
    (create_comments_table, "comments", "comments.sql"),
    (create_column_mapping_items_table, "column_mapping_items", "column_mapping_items.sql"),
    (create_mixed_annotation_items_table, "mixed_annotation_items", "mixed_annotation_items.sql"),
    (create_type_adapter_tests_table, "type_adapter_tests", "type_adapter_tests.sql"),
]


def test_all_basic_tables():
    results = []
    for fn, table_name, schema_file in TABLE_CHECKS:
        schema_path = SCHEMA_DIR / schema_file
        if not schema_path.exists():
            print(f"  SKIP {table_name}: schema file not found")
            continue
        result = verify_table(fn, DIALECT, schema_path, table_name, "sqlite")
        results.append(result)

    passed = sum(1 for r in results if r["matches"])
    failed = sum(1 for r in results if not r["matches"])

    print(f"\n{'='*60}")
    print(f"SQLite DDL Compatibility: {passed} passed, {failed} failed out of {len(results)}")
    print(f"{'='*60}")

    for r in results:
        status = "OK" if r["matches"] else "FAIL"
        print(f"  [{status}] {r['table']}")

    for r in results:
        if not r["matches"]:
            print(f"\n{'='*60}")
            print(f"[FAIL] {r['table']}")
            print(f"{'='*60}")
            print(f"  EXPECTED:\n    {r['expected_norm']}")
            print(f"  ACTUAL:\n    {r['actual_norm']}")

    assert passed == len(results), f"{failed} tables failed DDL compatibility check"


if __name__ == "__main__":
    test_all_basic_tables()
