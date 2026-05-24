"""
Logging Chapter: Example 1 - Basic Logging Configuration

This example shows the three logging configuration owners:
1. ActiveRecord.__logging_config__ for model logging defaults
2. Model.__logging_config__ for one model's override
3. configure_logging()/get_logger() for framework-level loggers
"""

import logging
from typing import Optional, Type

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.logging import LoggingConfig, LogDataMode, configure_logging, get_logger
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    email: str


class AuditUser(ActiveRecord):
    __table_name__ = "audit_users"
    id: Optional[int] = None
    username: str
    email: str


def create_table(model: Type[ActiveRecord]) -> None:
    backend = model.backend()
    backend.execute(
        f"""
        CREATE TABLE {model.__table_name__} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100)
        )
        """,
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )


def main():
    print("=" * 60)
    print("Example 1: Basic Logging Configuration")
    print("=" * 60)

    ActiveRecord.__logging_config__ = LoggingConfig(
        default_level=logging.INFO,
        log_data_mode=LogDataMode.SUMMARY,
    )
    AuditUser.__logging_config__ = LoggingConfig(
        default_level=logging.DEBUG,
        log_data_mode=LogDataMode.KEYS_ONLY,
    )

    print(f"ActiveRecord default level: {logging.getLevelName(ActiveRecord.__logging_config__.default_level)}")
    print(f"User inherits mode: {User.get_logging_config().log_data_mode}")
    print(f"AuditUser override mode: {AuditUser.get_logging_config().log_data_mode}")

    config = SQLiteConnectionConfig(database=":memory:")
    User.configure(config, SQLiteBackend)
    AuditUser.configure(config, SQLiteBackend)
    create_table(User)
    create_table(AuditUser)

    user = User(username="alice", email="alice@example.com")
    user.save()
    print(f"Created user: {user.username}")

    audit_user = AuditUser(username="bob", email="bob@example.com")
    audit_user.save()
    print(f"Created audit user: {audit_user.username}")

    configure_logging(level=logging.WARNING, propagate=False)
    framework_logger = get_logger("rhosocial.activerecord.worker")
    print(f"Framework logger: {framework_logger.name}")
    print("configure_logging() controls framework loggers, not model class logging config.")


if __name__ == "__main__":
    main()
