"""
Logging Chapter: Example 4 - Advanced Scenarios & Best Practices

Shows production/development presets with separate ActiveRecord and backend configs.
"""

import logging
import sys
from typing import Optional

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.connection.group import BackendGroup
from rhosocial.activerecord.logging import (
    ActiveRecordFormatter,
    LoggerConfig,
    LoggingConfig,
    LogDataMode,
    SummarizerConfig,
    configure_logging,
)
from rhosocial.activerecord.model import ActiveRecord


class User(ActiveRecord):
    __table_name__ = "users"
    __logger_name__ = "myapp.models.user"
    id: Optional[int] = None
    username: str
    password: str
    email: str


class Order(ActiveRecord):
    __table_name__ = "orders"
    id: Optional[int] = None
    user_id: int
    total: float
    credit_card: str


def production_configs():
    model_config = LoggingConfig(
        default_level=logging.INFO,
        log_data_mode=LogDataMode.SUMMARY,
        summarizer_config=SummarizerConfig(
            sensitive_fields={"password", "token", "api_key", "secret", "credit_card", "ssn", "cvv", "pin"},
            mask_placeholder="[REDACTED]",
        ),
    )
    backend_config = LoggingConfig(default_level=logging.WARNING, log_data_mode=LogDataMode.KEYS_ONLY)
    backend_config.add_logger_config(
        LoggerConfig(
            name="rhosocial.activerecord.transaction",
            level=logging.INFO,
            log_data_mode=LogDataMode.SUMMARY,
        )
    )
    return model_config, backend_config


def development_configs():
    model_config = LoggingConfig(default_level=logging.DEBUG, log_data_mode=LogDataMode.SUMMARY)
    backend_config = LoggingConfig(default_level=logging.DEBUG, log_data_mode=LogDataMode.SUMMARY)
    backend_config.add_logger_config(
        LoggerConfig(
            name="rhosocial.activerecord.query",
            log_data_mode=LogDataMode.FULL,
        )
    )
    return model_config, backend_config


def print_config_result(title: str, model_config: LoggingConfig, backend_config: LoggingConfig) -> None:
    test_data = {
        "username": "john_doe",
        "password": "my_password",
        "credit_card": "4111-1111-1111-1111",
        "cvv": "123",
    }
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)
    print(f"model: {model_config.summarize_data(test_data, logger_name='rhosocial.activerecord.model')}")
    print(f"backend: {backend_config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend')}")
    print(f"query: {backend_config.summarize_data(test_data, logger_name='rhosocial.activerecord.query')}")


def main():
    print("=" * 60)
    print("Example 4: Advanced Scenarios & Best Practices")
    print("=" * 60)

    production_model_config, production_backend_config = production_configs()
    print_config_result("SCENARIO 1: Production Environment", production_model_config, production_backend_config)

    development_model_config, development_backend_config = development_configs()
    print_config_result("SCENARIO 2: Development Environment", development_model_config, development_backend_config)

    ActiveRecord.__logging_config__ = production_model_config
    group = BackendGroup(
        name="production",
        models=[User, Order],
        config=SQLiteConnectionConfig(database=":memory:"),
        backend_class=SQLiteBackend,
        logging_config=production_backend_config,
    )
    group.configure()
    try:
        print("\nBackendGroup configured:")
        print(f"User model config mode: {User.get_logging_config().log_data_mode}")
        print(f"Order model config mode: {Order.get_logging_config().log_data_mode}")
        print(f"Backend config mode: {group.get_backend()._logging_config.log_data_mode}")
    finally:
        group.disconnect()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ActiveRecordFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    User.set_logger(logging.getLogger("myapp.models.user"))
    User.get_logger().handlers.clear()
    User.get_logger().addHandler(handler)
    User.get_logger().setLevel(logging.DEBUG)
    User.get_logger().propagate = False
    print(f"\nCustom user logger name: {User._get_logger_name()}")

    configure_logging(level=logging.INFO, propagate=True)
    print("configure_logging() is for framework loggers outside model/backend ownership.")

    print("""
Best practices:
1. Production: use SUMMARY for model logs and KEYS_ONLY for backend logs.
2. Development: FULL mode is only suitable for controlled debugging.
3. Compliance: define sensitive_fields on the owning LoggingConfig.
4. BackendGroup(logging_config=...) binds backend logging independently.
5. Custom __logger_name__ changes where logs are emitted, not data visibility rules.
""")


if __name__ == "__main__":
    main()
