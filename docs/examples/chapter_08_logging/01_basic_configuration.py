"""
Logging Chapter: Example 1 - Basic Logging Configuration
Demonstrates core concepts:
1. Global logging configuration
2. Log level settings
3. Logger namespace hierarchy
"""

import logging
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.logging import (
    configure_logging,
    get_logging_manager,
)

# --- Models ---

class User(ActiveRecord):
    """User Model"""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    email: str

# --- Main Execution ---

def main():
    # 1. Basic Configuration
    print("=" * 60)
    print("Example 1: Basic Logging Configuration")
    print("=" * 60)

    # Configure logging with INFO level
    configure_logging(level=logging.INFO)

    # Get the logging manager
    manager = get_logging_manager()
    print(f"Global log level: {logging.getLevelName(manager.config.default_level)}")
    print(f"Propagation enabled: {manager.config.propagate}")

    # 2. Logger Namespace Hierarchy
    print("\n" + "-" * 40)
    print("Logger Namespace Hierarchy:")
    print("-" * 40)

    print(f"ROOT_LOGGER: {manager.ROOT_LOGGER}")
    print(f"LOGGER_MODEL: {manager.LOGGER_MODEL}")
    print(f"LOGGER_BACKEND: {manager.LOGGER_BACKEND}")
    print(f"LOGGER_QUERY: {manager.LOGGER_QUERY}")
    print(f"LOGGER_TRANSACTION: {manager.LOGGER_TRANSACTION}")

    # 3. Get specific loggers
    print("\n" + "-" * 40)
    print("Get Specific Loggers:")
    print("-" * 40)

    model_logger = manager.get_model_logger()
    backend_logger = manager.get_backend_logger()
    query_logger = manager.get_query_logger()
    transaction_logger = manager.get_transaction_logger()

    print(f"Model logger name: {model_logger.name}")
    print(f"Backend logger name: {backend_logger.name}")
    print(f"Query logger name: {query_logger.name}")
    print(f"Transaction logger name: {transaction_logger.name}")

    # 4. Configure database and observe logs
    print("\n" + "-" * 40)
    print("Database Operations (observe logs):")
    print("-" * 40)

    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)

    # Create table
    backend = User.backend()
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100)
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create user (logs will appear based on log level)
    user = User(username="alice", email="alice@example.com")
    user.save()
    print(f"Created user: {user.username}")

    # 5. Change log level at runtime
    print("\n" + "-" * 40)
    print("Runtime Log Level Change:")
    print("-" * 40)

    # Change to DEBUG for more verbose logging
    configure_logging(level=logging.DEBUG)

    # Create another user - more detailed logs will appear
    user2 = User(username="bob", email="bob@example.com")
    user2.save()
    print(f"Created user: {user2.username}")

    # 6. Control specific logger level
    print("\n" + "-" * 40)
    print("Control Specific Logger Level:")
    print("-" * 40)

    # Only set backend logger to DEBUG, others remain INFO
    backend_logger.setLevel(logging.DEBUG)
    model_logger.setLevel(logging.WARNING)  # Only warnings and above for model

    print(f"Backend logger level: {logging.getLevelName(backend_logger.level)}")
    print(f"Model logger level: {logging.getLevelName(model_logger.level)}")

if __name__ == "__main__":
    main()
