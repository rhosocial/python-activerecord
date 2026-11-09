"""Logging Chapter: Example 9 - Backend execution logging

This example shows the single SQL logging point:

* the quiet default emits nothing;
* INFO emits one DML/DQL summary per execution, without SQL or values;
* DEBUG emits the SQL text plus redacted parameter metadata.
"""

import logging
import sys
from typing import Optional

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions, LogContext
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.logging import ActiveRecordEventFormatter
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    name: str = ""
    secret: str = ""


def emit(level: int, label: str) -> None:
    """Run the same operations at one application-chosen root level."""
    root = logging.getLogger()
    root.setLevel(level)
    print(f"--- {label} (root={logging.getLevelName(level)}) ---")
    User(name="alice", secret="top-secret").save()
    User.query().all()


def main() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(logging.StreamHandler(sys.stdout))
    root.handlers[0].setFormatter(
        ActiveRecordEventFormatter("%(levelname)s %(message)s")
    )

    User.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    backend = User.backend()
    backend.connect()
    backend.execute(
        'CREATE TABLE "users" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, '
        '"name" TEXT, "secret" TEXT)',
        options=ExecutionOptions(
            stmt_type=StatementType.DDL,
            log_context=LogContext(operation="create", object_name="users"),
        ),
    )

    print("=" * 60)
    print("Example 9: Backend execution logging")
    print("=" * 60)

    emit(logging.WARNING, "default root level")
    emit(logging.INFO, "INFO summaries")
    emit(logging.DEBUG, "DEBUG SQL and redacted parameters")

    print("\nThe backend writes SQL once; the query layer only supplies LogContext.")
    backend.disconnect()


if __name__ == "__main__":
    main()
