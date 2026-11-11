# docs/examples/chapter_13_cli/cli_runner.py
"""Helper that runs the model CLI in a subprocess.

Examples execute real commands instead of calling ``main()`` in-process, so the
printed command line is the same one a shell would run. The only difference is
``python -m rhosocial.activerecord.cli`` in place of the installed
``rhosocial-activerecord`` console script.
"""

import os
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_SRC = HERE.parents[2] / "src"

SQLITE_BACKEND = "rhosocial.activerecord.backend.impl.sqlite.backend:SQLiteBackend"
SQLITE_CONFIG = "rhosocial.activerecord.backend.impl.sqlite.config:SQLiteConnectionConfig"


def connection_args(database):
    """Backend and config arguments for a SQLite file database."""
    return [
        "--backend-class",
        SQLITE_BACKEND,
        "--config-class",
        SQLITE_CONFIG,
        "--config",
        f"database={database}",
    ]


def base_args(database):
    """Arguments shared by every command: model path plus connection."""
    return ["--path", str(HERE), *connection_args(database)]


def _shorten(reference):
    """Keep only the class name of a ``module:Class`` reference."""
    return reference.rsplit(":", 1)[-1].rsplit(".", 1)[-1]


def _display_args(args):
    """Shorten absolute paths and class references so commands stay readable."""
    display = []
    index = 0
    while index < len(args):
        arg = args[index]
        value = args[index + 1] if index + 1 < len(args) else None
        if arg == "--path":
            display.extend(["--path", "docs/examples/chapter_13_cli"])
            index += 2
        elif arg in ("--backend-class", "--config-class"):
            display.extend([arg, _shorten(value)])
            index += 2
        elif arg == "--config":
            database = value.partition("=")[2]
            display.extend(["--config", f"database={Path(database).name}"])
            index += 2
        else:
            display.append(arg)
            index += 1
    return display


def build_env():
    """Make ``models`` and the package importable from a source checkout."""
    env = os.environ.copy()
    entries = [str(HERE)]
    if REPO_SRC.is_dir():
        entries.append(str(REPO_SRC))
    existing = env.get("PYTHONPATH")
    if existing:
        entries.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(entries)
    return env


def run_cli(args, stdin=None, echo=True):
    """Run the CLI and return the completed process."""
    argv = [sys.executable, "-m", "rhosocial.activerecord.cli", *args]
    completed = subprocess.run(
        argv,
        cwd=str(HERE),
        env=build_env(),
        input=stdin,
        text=True,
        capture_output=True,
    )
    if echo:
        command = "rhosocial-activerecord " + " ".join(
            shlex.quote(arg) for arg in _display_args(args)
        )
        print(f"$ {command}")
        stdout_text = completed.stdout or ""
        stderr_text = completed.stderr or ""
        if stdout_text.strip():
            print(stdout_text.rstrip())
        if stderr_text.strip():
            print(f"[stderr] {stderr_text.rstrip()}")
        print(f"[exit {completed.returncode}]")
        print()
    return completed
