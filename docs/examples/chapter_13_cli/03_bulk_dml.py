# docs/examples/chapter_13_cli/03_bulk_dml.py
"""CLI Chapter: Example 3 - Bulk DML.

Shows JSON and JSONL input, ``--input-format``, ``--batch-size``,
``--update-fields``, confirmed bulk delete, and the soft-delete label.
"""

import json
import tempfile

from models import temporary_database

from cli_runner import base_args, run_cli


def main():
    print("=" * 60)
    print("Example 3: bulk DML")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        database = temporary_database(tmp)
        base = base_args(database)

        run_cli(
            [
                "dml",
                "bulk",
                "create",
                *base,
                "--model",
                "models:User",
                "--data",
                json.dumps(
                    [
                        {"name": "Grace", "email": "grace@example.com", "age": 26},
                        {"name": "Heidi", "email": "heidi@example.com", "age": 33},
                        {"name": "Ivan", "email": "ivan@example.com", "age": 41},
                    ]
                ),
                "--batch-size",
                "2",
                "-o",
                "json",
            ]
        )

        print("JSONL from stdin keeps one object per line:")
        rows = [
            {"name": "Judy", "email": "judy@example.com", "age": 24},
            {"name": "Karl", "email": "karl@example.com", "age": 38},
        ]
        payload = "\n".join(json.dumps(row) for row in rows) + "\n"
        run_cli(
            [
                "dml",
                "bulk",
                "create",
                *base,
                "--model",
                "models:User",
                "--data",
                "@-",
                "--input-format",
                "jsonl",
                "-o",
                "json",
            ],
            stdin=payload,
        )

        print("Every object in bulk update must carry the same update fields:")
        print("The ids below are the ones the previous bulk creates returned.")
        run_cli(
            [
                "dml",
                "bulk",
                "update",
                *base,
                "--model",
                "models:User",
                "--data",
                json.dumps([{"id": 8, "age": 25}, {"id": 9, "age": 39}]),
                "--update-fields",
                "age",
                "-o",
                "json",
            ]
        )

        run_cli(
            [
                "dml",
                "bulk",
                "delete",
                *base,
                "--model",
                "models:User",
                "--data",
                "[2, 4]",
                "--yes",
                "-o",
                "json",
            ]
        )

        print("Bulk delete on a soft-delete model marks rows instead of removing them:")
        run_cli(
            [
                "dml",
                "bulk",
                "delete",
                *base,
                "--model",
                "models:Task",
                "--data",
                "[1, 2]",
                "--yes",
                "-o",
                "json",
            ]
        )


if __name__ == "__main__":
    main()
