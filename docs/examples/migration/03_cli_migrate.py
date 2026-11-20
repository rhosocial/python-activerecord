# docs/examples/migration/03_cli_migrate.py
"""Drive migrations through the `migrate` CLI command, in-process.

Shows --list, --plan, --dry-run, a real UP, a DOWN, and -o json. The migration
function and model live in `migration_models.py` because the CLI resolves them
by fully qualified name (module:Class / module:function).
"""
import os
import sys
import tempfile

# Make the sibling migration_models module importable by FQN.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rhosocial.activerecord.cli import main
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from migration_models import CliUser

FQN_MIGRATION = "migration_models:create_cli_users"
FQN_MODEL = "migration_models:CliUser"


def run(args):
    print(f"\n$ rhosocial-activerecord {' '.join(args)}")
    code = main(args)
    print(f"  exit={code}")
    return code


def main_demo():
    db_path = tempfile.mktemp(suffix=".db")
    rec_path = tempfile.mktemp(suffix=".json")

    # Configure the model so --model can obtain a connection from it.
    CliUser.configure(SQLiteConnectionConfig(database=db_path), SQLiteBackend)
    try:
        base = [FQN_MIGRATION, "--model", FQN_MODEL, "--record-store", rec_path]

        run(["migrate", FQN_MIGRATION, "--list", "--model", FQN_MODEL])
        run(["migrate", "--plan", *base])
        run(["migrate", *base, "--dry-run"])
        run(["migrate", *base])
        run(["migrate", *base, "--direction", "down", "-o", "json"])
    finally:
        for path in (db_path, rec_path):
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    main_demo()
