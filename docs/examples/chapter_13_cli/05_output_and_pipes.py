# docs/examples/chapter_13_cli/05_output_and_pipes.py
"""CLI Chapter: Example 5 - Output formats and stdin.

Machine formats write only data to stdout, so they can feed other tools.
Comments and pagination notes go to stderr and never mix into the payload.
"""

import json
import tempfile

from models import temporary_database

from cli_runner import base_args, run_cli


def main():
    print("=" * 60)
    print("Example 5: output formats and stdin")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        database = temporary_database(tmp)
        base = base_args(database)

        print("``-o table`` uses Rich when installed and falls back to JSON otherwise:")
        run_cli(["dql", "list", *base, "--model", "models:User", "-o", "table"])

        print("CSV keeps a header unless --no-header is given:")
        run_cli(
            ["dql", "list", *base, "--model", "models:User", "--limit", "2", "-o", "csv"]
        )
        run_cli(
            [
                "dql",
                "list",
                *base,
                "--model",
                "models:User",
                "--limit",
                "2",
                "-o",
                "tsv",
                "--no-header",
            ]
        )

        print("--fields limits the output columns:")
        run_cli(
            [
                "dql",
                "list",
                *base,
                "--model",
                "models:User",
                "--limit",
                "2",
                "--fields",
                "id,name",
                "-o",
                "json",
            ]
        )

        run_cli(
            ["dql", "count", *base, "--model", "models:User", "-o", "value"]
        )

        print("JSONL is one object per line, ready for a downstream consumer:")
        run_cli(
            ["dql", "list", *base, "--model", "models:User", "--no-limit", "-o", "jsonl"]
        )

        print("--quiet drops the default-pagination note from stderr:")
        run_cli(
            ["dql", "list", *base, "--model", "models:User", "--quiet", "-o", "json"]
        )

        print("--data @- reads the record from stdin:")
        record = json.dumps({"id": 11, "name": "Leo", "age": 27})
        run_cli(
            [
                "dml",
                "create",
                *base,
                "--model",
                "models:User",
                "--data",
                "@-",
                "-o",
                "json",
            ],
            stdin=record,
        )


if __name__ == "__main__":
    main()
