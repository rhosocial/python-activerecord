# tests/support/cli.py
"""Helpers shared by the core CLI tests: run the CLI in-process."""

import io
from contextlib import redirect_stderr, redirect_stdout

from rhosocial.activerecord.cli import main

from .logging import preserve_logging

SQLITE_BACKEND = "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend"
ASYNC_SQLITE_BACKEND = (
    "rhosocial.activerecord.backend.impl.sqlite.backend:AsyncSQLiteBackend"
)
SQLITE_CONFIG = "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig"


def connection_args(database, backend=SQLITE_BACKEND):
    """Build the explicit backend, config class, and database arguments."""
    return [
        "--backend-class",
        backend,
        "--config-class",
        SQLITE_CONFIG,
        "--config",
        f"database={database}",
    ]


def run_cli(argv, capture=True):
    """Run the CLI in-process and return (exit_code, stdout, stderr)."""
    with preserve_logging():
        if not capture:
            try:
                return main(argv), "", ""
            except SystemExit as exc:
                return (exc.code if exc.code is not None else 0), "", ""
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = main(argv)
            except SystemExit as exc:
                code = exc.code if exc.code is not None else 0
        return code, out.getvalue(), err.getvalue()
