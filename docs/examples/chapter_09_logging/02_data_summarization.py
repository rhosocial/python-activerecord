"""
Logging Chapter: Example 2 - Data Summarization

Data payload visibility is controlled only by LoggingConfig.log_data_mode.
"""

import logging
from typing import Optional

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.logging import LoggingConfig, LogDataMode, SummarizerConfig
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str
    email: str
    api_key: str
    bio: str


def main():
    print("=" * 60)
    print("Example 2: Data Summarization")
    print("=" * 60)

    test_data = {
        "username": "john_doe",
        "password": "super_secret_password_123",
        "email": "john@example.com",
        "api_key": "sk-api-key-12345-abcdef",
        "bio": "This is a very long biography " * 20,
    }

    config = LoggingConfig(
        default_level=logging.DEBUG,
        summarizer_config=SummarizerConfig(
            sensitive_fields={"password", "api_key"},
            max_string_length=40,
        ),
        log_data_mode=LogDataMode.SUMMARY,
    )
    User.__logging_config__ = config

    for mode in (LogDataMode.HIDDEN, LogDataMode.KEYS_ONLY, LogDataMode.SUMMARY, LogDataMode.FULL):
        config.log_data_mode = mode
        print("\n" + "-" * 40)
        print(f"Mode: {mode.value}")
        print("-" * 40)
        print(config.summarize_data(test_data))

    config.summarizer_config = SummarizerConfig(
        sensitive_fields={"password", "api_key", "email"},
        max_string_length=30,
        mask_placeholder="[REDACTED]",
        field_maskers={
            "email": lambda value: (
                str(value).split("@")[0][:1] + "***@" + str(value).split("@")[1] if "@" in str(value) else "***"
            ),
        },
    )
    config.log_data_mode = LogDataMode.SUMMARY
    print("\n" + "-" * 40)
    print("Custom summarizer config")
    print("-" * 40)
    print(config.summarize_data(test_data))

    User.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend, logging_config=config)
    backend = User.backend()
    backend.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            password VARCHAR(100),
            email VARCHAR(100),
            api_key VARCHAR(100),
            bio TEXT
        )
        """,
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )

    user = User(
        username="alice",
        password="my_secret_password",
        email="alice@example.com",
        api_key="sk-12345",
        bio="A" * 200,
    )
    user.save()
    User.log_data(logging.INFO, "Model data log", test_data)
    print(f"Created user: {user.username}")


if __name__ == "__main__":
    main()
