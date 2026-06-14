# tests/providers/test_ddl_mixins_compatibility.py
"""
验证 DDL 表达式与 SQLite mixins schema 文件兼容性。
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from providers.fixtures.mixins import (
    create_timestamped_posts_table,
    create_versioned_products_table,
    create_tasks_table,
    create_combined_articles_table,
)
from providers.ddl_verify import verify_table

DIALECT = SQLiteDialect(version=(3, 45, 0))
SCHEMA_DIR = Path(__file__).parent.parent / "rhosocial" / "activerecord_test" / "feature" / "mixins" / "schema"

TABLE_CHECKS = [
    (create_timestamped_posts_table, "timestamped_posts", "timestamped_posts.sql"),
    (create_versioned_products_table, "versioned_products", "versioned_products.sql"),
    (create_tasks_table, "tasks", "tasks.sql"),
    (create_combined_articles_table, "combined_articles", "combined_articles.sql"),
]


def test_all_mixins_tables():
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
    print(f"Mixins DDL Compatibility: {passed} passed, {failed} failed out of {len(results)}")
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
    test_all_mixins_tables()
