"""
Logging Chapter: Example 3 - Per-Logger Configuration
Demonstrates core concepts:
1. Different summarization modes for different loggers
2. Hierarchical inheritance
3. Custom summarizer per logger
4. Runtime configuration control
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
    """User Model"""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str
    email: str

class Product(ActiveRecord):
    """Product Model"""
    __table_name__ = "products"
    id: Optional[int] = None
    name: str
    description: str
    price: float

# --- Main Execution ---

def main():
    print("=" * 60)
    print("Example 3: Per-Logger Configuration")
    print("=" * 60)

    # 1. Global Configuration
    print("\n" + "-" * 40)
    print("1. Global Configuration")
    print("-" * 40)

    manager = get_logging_manager()
    manager.reset()

    # Set global default
    manager.config.log_data_mode = 'summary'
    print(f"Global mode: {manager.config.log_data_mode}")

    test_data = {'username': 'john', 'password': 'secret', 'bio': 'A' * 150}

    # 2. Configure Backend Layer (keys_only for security)
    print("\n" + "-" * 40)
    print("2. Backend Layer: keys_only (Production Security)")
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

    # 3. Configure Query Layer (full for debugging)
    print("\n" + "-" * 40)
    print("3. Query Layer: full (Development Debugging)")
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

    # 4. Custom Summarizer for Specific Logger
    print("\n" + "-" * 40)
    print("4. Custom Summarizer for Specific Model")
    print("-" * 40)

    # Create custom summarizer with shorter truncation
    user_summarizer = SummarizerConfig(
        max_string_length=20,  # Only show first 20 chars
        sensitive_fields={'password', 'email', 'ssn', 'credit_card'},
        mask_placeholder='[PROTECTED]',
    )

    user_config = LoggerConfig(
        name='rhosocial.activerecord.model.User',
        log_data_mode='summary',
        summarizer_config=user_summarizer,
    )
    manager.config.add_logger_config(user_config)

    user_result = manager.config.summarize_data(test_data, logger_name='rhosocial.activerecord.model.User')
    print(f"User model result: {user_result}")
    print("Note: Custom placeholder and shorter truncation")

    # Other models use global config
    product_result = manager.config.summarize_data(test_data, logger_name='rhosocial.activerecord.model.Product')
    print(f"Product model (global): {product_result}")
    print("Note: Product uses global config")

    # 5. Verify Hierarchical Inheritance
    print("\n" + "-" * 40)
    print("5. Hierarchical Inheritance Summary")
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
    ]

    print("Logger Name                                    | Mode")
    print("-" * 60)
    for logger_name in test_loggers:
        mode = manager.config.get_log_data_mode(logger_name)
        print(f"{logger_name:45} | {mode}")

    # 6. Real-world Scenario
    print("\n" + "-" * 40)
    print("6. Real-world Scenario")
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
            email VARCHAR(100)
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # Create user - backend logs will use keys_only
    user = User(username='alice', password='my_password', email='alice@example.com')
    user.save()
    print(f"Created user: {user.username}")
    print("\nObserve logs:")
    print("- Backend logs show keys_only (for security)")
    print("- Model logs may use custom config")
    print("- Transaction logs use global summary mode")

    # 7. Override Mode at Call Time
    print("\n" + "-" * 40)
    print("7. Override Mode at Call Time")
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
