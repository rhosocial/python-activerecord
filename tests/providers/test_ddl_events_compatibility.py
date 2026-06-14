# tests/providers/test_ddl_events_compatibility.py
"""
验证 DDL 表达式与 SQLite events schema 文件兼容性。
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from providers.fixtures.events import (
    create_event_tests_table,
    create_event_test_models_table,
    create_event_tracking_models_table,
    TABLE_EXPRESSIONS,
)
from providers.ddl_verify import verify_table

DIALECT = SQLiteDialect(version=(3, 45, 0))
SCHEMA_DIR = Path(__file__).parent.parent / "rhosocial" / "activerecord_test" / "feature" / "events" / "schema"

TABLE_CHECKS = [
    (create_event_tests_table, "event_tests", "event_tests.sql"),
    (create_event_test_models_table, "event_test_models", "event_test_models.sql"),
    (create_event_tracking_models_table, "event_tracking_models", "event_tracking_models.sql"),
]


def test_all_events_tables():
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
    print(f"Events DDL Compatibility: {passed} passed, {failed} failed out of {len(results)}")
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
    test_all_events_tables()
