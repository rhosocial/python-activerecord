"""
Logging Chapter: Example 3 - Per-Logger Configuration

Per-logger rules belong to the LoggingConfig object that owns them.
ActiveRecord and backend logging configs are independent unless explicitly shared.
"""

from typing import Optional

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.logging import LoggerConfig, LoggingConfig, LogDataMode, SummarizerConfig
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str
    email: str
    credit_card: str


class Product(ActiveRecord):
    __table_name__ = "products"
    id: Optional[int] = None
    name: str
    description: str
    price: float


class Order(ActiveRecord):
    __logger_name__ = "myapp.models.order"
    __table_name__ = "orders"
    id: Optional[int] = None
    user_id: int
    total: float


def main():
    print("=" * 60)
    print("Example 3: Per-Logger Configuration")
    print("=" * 60)

    model_config = LoggingConfig(log_data_mode=LogDataMode.SUMMARY)
    model_config.add_logger_config(
        LoggerConfig(
            name="__main__.User",
            log_data_mode=LogDataMode.SUMMARY,
            summarizer_config=SummarizerConfig(
                max_string_length=30,
                sensitive_fields={"password", "email", "credit_card"},
                mask_placeholder="[PROTECTED]",
            ),
        )
    )
    model_config.add_logger_config(
        LoggerConfig(
            name="myapp.models.order",
            log_data_mode=LogDataMode.KEYS_ONLY,
        )
    )
    ActiveRecord.__logging_config__ = model_config

    backend_config = LoggingConfig(log_data_mode=LogDataMode.KEYS_ONLY)
    backend_config.add_logger_config(
        LoggerConfig(
            name="rhosocial.activerecord.backend.sqlite",
            log_data_mode=LogDataMode.SUMMARY,
        )
    )

    test_data = {
        "username": "john",
        "password": "secret",
        "email": "john@example.com",
        "credit_card": "4111111111111111",
        "bio": "A" * 150,
    }

    print("\nLogger names:")
    print(f"User logger name: {User._get_logger_name()}")
    print(f"Product logger name: {Product._get_logger_name()}")
    print(f"Order logger name: {Order._get_logger_name()}")

    print("\nModel config results:")
    for logger_name in (
        "__main__.User",
        "rhosocial.activerecord.model.Product",
        "myapp.models.order",
    ):
        print(f"{logger_name}: {model_config.summarize_data(test_data, logger_name=logger_name)}")

    print("\nBackend config results:")
    for logger_name in (
        "rhosocial.activerecord.backend",
        "rhosocial.activerecord.backend.sqlite",
        "rhosocial.activerecord.query.ActiveQuery",
    ):
        print(f"{logger_name}: {backend_config.summarize_data(test_data, logger_name=logger_name)}")

    User.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend, logging_config=backend_config)
    backend = User.backend()
    backend.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            password VARCHAR(100),
            email VARCHAR(100),
            credit_card VARCHAR(20)
        )
        """,
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )

    user = User(
        username="alice",
        password="my_password",
        email="alice@example.com",
        credit_card="4111111111111111",
    )
    user.save()
    print(f"\nCreated user: {user.username}")


if __name__ == "__main__":
    main()
