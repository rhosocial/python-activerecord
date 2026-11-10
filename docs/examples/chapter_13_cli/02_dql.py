# docs/examples/chapter_13_cli/02_dql.py
"""CLI Chapter: Example 2 - Queries.

Shows get, list with filters and ordering, count, exists, aggregate, the
default pagination note, and ``dql run`` with a query factory.
"""

import tempfile

from models import temporary_database

from cli_runner import base_args, run_cli


def main():
    print("=" * 60)
    print("Example 2: DQL")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        database = temporary_database(tmp)
        base = base_args(database)

        run_cli(["dql", "get", *base, "--model", "models:User", "--pk", "1", "-o", "json"])

        run_cli(
            [
                "dql",
                "list",
                *base,
                "--model",
                "models:User",
                "--where",
                "age=30",
                "--order-by",
                "name desc",
                "--limit",
                "2",
                "-o",
                "json",
            ]
        )

        print("Without --limit the CLI pages by default and explains it on stderr:")
        run_cli(["dql", "list", *base, "--model", "models:User", "-o", "json"])
        print("--no-limit disables the default page size:")
        run_cli(
            ["dql", "list", *base, "--model", "models:User", "--no-limit", "-o", "jsonl"]
        )

        run_cli(
            ["dql", "count", *base, "--model", "models:User", "-o", "value"]
        )
        run_cli(
            [
                "dql",
                "exists",
                *base,
                "--model",
                "models:User",
                "--where",
                "age=99",
                "-o",
                "value",
            ]
        )

        print("Grouped aggregate returns one row per group:")
        run_cli(
            [
                "dql",
                "aggregate",
                *base,
                "--model",
                "models:User",
                "--fn",
                "count",
                "--field",
                "*",
                "--group-by",
                "age",
                "-o",
                "json",
            ]
        )
        print("Scalar aggregate fits ``-o value``:")
        run_cli(
            [
                "dql",
                "aggregate",
                *base,
                "--model",
                "models:User",
                "--fn",
                "avg",
                "--field",
                "age",
                "-o",
                "value",
            ]
        )

        print("``dql run`` executes a query factory; comparisons live in Python:")
        run_cli(
            ["dql", "run", *base, "--model", "models:User", "--query", "models:active_users", "-o", "json"]
        )


if __name__ == "__main__":
    main()
