# docs/examples/chapter_13_cli/01_dml.py
"""CLI Chapter: Example 1 - Single-record DML.

Shows create, update, dry-run, delete, the not-found exit code, the read-only
refusal, and the soft-delete action label.
"""

import tempfile

from models import temporary_database

from cli_runner import base_args, run_cli


def main():
    print("=" * 60)
    print("Example 1: single-record DML")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        database = temporary_database(tmp)
        base = base_args(database)

        run_cli(
            [
                "dml",
                "create",
                *base,
                "--model",
                "models:User",
                "--data",
                '{"id": 5, "name": "Eve", "email": "eve@example.com", "age": 28}',
                "-o",
                "json",
            ]
        )

        run_cli(
            [
                "dml",
                "update",
                *base,
                "--model",
                "models:User",
                "--pk",
                "5",
                "--data",
                '{"age": 29}',
                "-o",
                "json",
            ]
        )

        run_cli(
            [
                "dml",
                "delete",
                *base,
                "--model",
                "models:User",
                "--pk",
                "5",
                "--yes",
                "--dry-run",
                "-o",
                "json",
            ]
        )

        run_cli(
            [
                "dml",
                "delete",
                *base,
                "--model",
                "models:User",
                "--pk",
                "5",
                "--yes",
                "-o",
                "json",
            ]
        )

        print("A missing primary key exits with code 3:")
        run_cli(
            [
                "dml",
                "delete",
                *base,
                "--model",
                "models:User",
                "--pk",
                "999",
                "--yes",
                "-o",
                "json",
            ]
        )

        print("Read-only models refuse DML before touching the database (code 6):")
        run_cli(
            [
                "dml",
                "create",
                *base,
                "--model",
                "models:ReadOnlyUser",
                "--data",
                '{"id": 6, "name": "Grace"}',
                "-o",
                "json",
            ]
        )

        print("A soft-delete model reports the soft_delete action instead of delete:")
        run_cli(
            [
                "dml",
                "delete",
                *base,
                "--model",
                "models:Task",
                "--pk",
                "1",
                "--yes",
                "-o",
                "json",
            ]
        )


if __name__ == "__main__":
    main()
