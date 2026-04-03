"""
Logging Chapter: Example 3 - Per-Logger Configuration
Demonstrates core concepts:
1. Logger naming rules for ActiveRecord classes
2. Different summarization modes for different loggers
3. Hierarchical inheritance
4. Custom summarizer per logger
5. Runtime configuration control
"""

from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.logging import (
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
)

# --- Models ---


class User(ActiveRecord):
    """User Model with sensitive fields"""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str      # Will be masked in logs
    email: str         # Will be masked in logs
    credit_card: str   # Will be masked in logs


class Product(ActiveRecord):
    """Product Model"""
    __table_name__ = "products"
    id: Optional[int] = None
    name: str
    description: str
    price: float


# --- Custom Logger Name Example ---

class Order(ActiveRecord):
    """Order Model with custom logger name"""
    __logger_name__ = 'myapp.models.order'  # Custom logger name
    __table_name__ = "orders"
    id: Optional[int] = None
    user_id: int
    total: float


# --- Main Execution ---


def main():
    print("=" * 60)
    print("Example 3: Per-Logger Configuration")
    print("=" * 60)

    # 1. Logger Naming Rules
    print("\n" + "-" * 40)
    print("1. Logger Naming Rules")
    print("-" * 40)

    # Default naming: rhosocial.activerecord.model.{ClassName}
    print(f"User logger name: {User._get_logger_name()}")
    print(f"Product logger name: {Product._get_logger_name()}")
    # Custom naming: uses __logger_name__ attribute
    print(f"Order logger name (custom): {Order._get_logger_name()}")

    # 2. Global Configuration
    print("\n" + "-" * 40)
    print("2. Global Configuration")
    print("-" * 40)

    manager = get_logging_manager()
    manager.reset()

    # Set global default
    manager.config.log_data_mode = 'summary'
    print(f"Global mode: {manager.config.log_data_mode}")

    test_data = {'username': 'john', 'password': 'secret', 'bio': 'A' * 150}

    # 3. Configure for Specific Model (User)
    print("\n" + "-" * 40)
    print("3. Configure for Specific Model (User)")
    print("-" * 40)

    # Create custom summarizer for User class
    user_summarizer = SummarizerConfig(
        max_string_length=30,  # Shorter truncation
        sensitive_fields={'password', 'email', 'credit_card'},
        mask_placeholder='[PROTECTED]',
    )

    user_config = LoggerConfig(
        name='rhosocial.activerecord.model.User',
        log_data_mode='summary',
        summarizer_config=user_summarizer,
    )
    manager.config.add_logger_config(user_config)

    user_result = manager.config.summarize_data(
        {'username': 'alice', 'password': 'secret123', 'email': 'alice@example.com', 'credit_card': '4111111111111111'},
        logger_name='rhosocial.activerecord.model.User'
    )
    print(f"User model result: {user_result}")
    print("Note: password, email, credit_card show as [PROTECTED]")

    # Product uses global config (no custom config)
    product_result = manager.config.summarize_data(test_data, logger_name='rhosocial.activerecord.model.Product')
    print(f"Product model (global): {product_result}")

    # 4. Configure Backend Layer (keys_only for security)
    print("\n" + "-" * 40)
    print("4. Backend Layer: keys_only (Production Security)")
    print("-" * 40)

    backend_config = LoggerConfig(
        name='rhosocial.activerecord.backend',
        log_data_mode='keys_only',  # Don't show values in backend logs
    )
    manager.config.add_logger_config(backend_config)

    # Backend and its children will use keys_only
    backend_result = manager.config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend')
    print(f"Backend result: {backend_result}")

    # sqlite inherits from backend
    sqlite_result = manager.config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend.sqlite')
    print(f"SQLite (inherits): {sqlite_result}")
    print("Note: sqlite inherits keys_only from backend")

    # 5. Configure Query Layer (full for debugging)
    print("\n" + "-" * 40)
    print("5. Query Layer: full (Development Debugging)")
    print("-" * 40)

    query_config = LoggerConfig(
        name='rhosocial.activerecord.query',
        log_data_mode='full',  # Show full data for query debugging
    )
    manager.config.add_logger_config(query_config)

    query_result = manager.config.summarize_data(test_data, logger_name='rhosocial.activerecord.query')
    print(f"Query result: {query_result}")

    # ActiveQuery inherits from query
    activequery_result = manager.config.summarize_data(
        test_data, logger_name='rhosocial.activerecord.query.ActiveQuery'
    )
    print(f"ActiveQuery (inherits): {activequery_result}")
    print("Note: ActiveQuery inherits full from query")

    # 6. Configure Custom Logger Name (Order)
    print("\n" + "-" * 40)
    print("6. Custom Logger Name (Order)")
    print("-" * 40)

    order_summarizer = SummarizerConfig(
        sensitive_fields={'total'},  # Mask total in logs
        mask_placeholder='[HIDDEN]',
    )

    order_config = LoggerConfig(
        name='myapp.models.order',  # Matches __logger_name__
        log_data_mode='summary',
        summarizer_config=order_summarizer,
    )
    manager.config.add_logger_config(order_config)

    order_result = manager.config.summarize_data(
        {'user_id': 1, 'total': 99.99},
        logger_name='myapp.models.order'
    )
    print(f"Order result: {order_result}")
    print("Note: total is masked with custom placeholder")

    # 7. Verify Hierarchical Inheritance
    print("\n" + "-" * 40)
    print("7. Hierarchical Inheritance Summary")
    print("-" * 40)

    test_loggers = [
        'rhosocial.activerecord',
        'rhosocial.activerecord.model',
        'rhosocial.activerecord.model.User',
        'rhosocial.activerecord.model.Product',
        'rhosocial.activerecord.backend',
        'rhosocial.activerecord.backend.sqlite',
        'rhosocial.activerecord.query',
        'rhosocial.activerecord.query.ActiveQuery',
        'rhosocial.activerecord.transaction',
        'myapp.models.order',
    ]

    print("Logger Name                                    | Mode")
    print("-" * 60)
    for logger_name in test_loggers:
        mode = manager.config.get_log_data_mode(logger_name)
        print(f"{logger_name:45} | {mode}")

    # 8. Real-world Scenario with CRUD Operations
    print("\n" + "-" * 40)
    print("8. Real-world Scenario with CRUD Operations")
    print("-" * 40)

    # Setup database
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)
    backend = User.backend()
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            password VARCHAR(100),
            email VARCHAR(100),
            credit_card VARCHAR(20)
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create user - User model uses custom summarizer
    print("\nCreating user (watch the logs):")
    user = User(
        username='alice',
        password='my_password',
        email='alice@example.com',
        credit_card='4111111111111111'
    )
    user.save()
    print(f"Created user: {user.username}")
    print("\nObserve logs:")
    print("- User model logs show [PROTECTED] for sensitive fields")
    print("- Backend logs show keys_only (field names only)")

    # 9. Override Mode at Call Time
    print("\n" + "-" * 40)
    print("9. Override Mode at Call Time")
    print("-" * 40)

    # Even though backend is keys_only, we can force full mode
    override_result = manager.config.summarize_data(
        test_data,
        mode='full',
        logger_name='rhosocial.activerecord.backend'
    )
    print(f"Forced full mode on backend: {override_result}")
    print("Note: Explicit mode parameter overrides logger config")


if __name__ == "__main__":
    main()
