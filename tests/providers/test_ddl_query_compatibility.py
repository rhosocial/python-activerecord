# tests/providers/test_ddl_query_compatibility.py
"""
验证 DDL 表达式与 SQLite query schema 文件兼容性。
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from providers.fixtures.query import (
    create_users_table,
    create_posts_table,
    create_comments_table,
    create_profiles_table,
    create_orders_table,
    create_order_items_table,
    create_extended_orders_table,
    create_extended_order_items_table,
    create_json_users_table,
    create_searchable_items_table,
    create_nodes_table,
)
from providers.ddl_verify import verify_table

DIALECT = SQLiteDialect(version=(3, 45, 0))
SCHEMA_DIR = Path(__file__).parent.parent / "rhosocial" / "activerecord_test" / "feature" / "query" / "schema"

TABLE_CHECKS = [
    (create_users_table, "users", "users.sql"),
    (create_posts_table, "posts", "posts.sql"),
    (create_comments_table, "comments", "comments.sql"),
    (create_profiles_table, "profiles", "profiles.sql"),
    (create_orders_table, "orders", "orders.sql"),
    (create_order_items_table, "order_items", "order_items.sql"),
    (create_extended_orders_table, "extended_orders", "extended_orders.sql"),
    (create_extended_order_items_table, "extended_order_items", "extended_order_items.sql"),
    (create_json_users_table, "json_users", "json_users.sql"),
    (create_searchable_items_table, "searchable_items", "searchable_items.sql"),
    (create_nodes_table, "nodes", "nodes.sql"),
]


def test_all_query_tables():
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
    print(f"Query DDL Compatibility: {passed} passed, {failed} failed out of {len(results)}")
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
    test_all_query_tables()
