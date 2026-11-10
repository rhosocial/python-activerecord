# docs/examples/chapter_13_cli/04_set_cte.py
"""CLI Chapter: Example 4 - Set operations and CTEs.

The simple form combines two model queries. The composed form passes a factory
that returns an existing ``SetOperationQuery`` or ``CTEQuery``.
"""

import tempfile

from models import temporary_database

from cli_runner import base_args, run_cli


def main():
    print("=" * 60)
    print("Example 4: set operations and CTEs")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        database = temporary_database(tmp)
        base = base_args(database)

        run_cli(
            [
                "set",
                "union",
                *base,
                "--left-model",
                "models:User",
                "--right-model",
                "models:Admin",
                "--left-where",
                "age=30",
                "--right-where",
                "age=30",
                "-o",
                "json",
            ]
        )

        run_cli(
            [
                "set",
                "intersect",
                *base,
                "--left-model",
                "models:User",
                "--right-model",
                "models:Admin",
                "--left-where",
                "age=30",
                "--right-where",
                "age=35",
                "-o",
                "json",
            ]
        )

        run_cli(
            [
                "set",
                "except",
                *base,
                "--left-model",
                "models:User",
                "--right-model",
                "models:Admin",
                "-o",
                "json",
            ]
        )

        print("A factory can compose the arms in Python and return the query object:")
        run_cli(
            [
                "set",
                "run",
                *base,
                "--model",
                "models:User",
                "--query",
                "models:user_union",
                "-o",
                "json",
            ]
        )

        run_cli(
            [
                "cte",
                "run",
                *base,
                "--model",
                "models:User",
                "--query",
                "models:older_users_cte",
                "-o",
                "json",
            ]
        )


if __name__ == "__main__":
    main()
