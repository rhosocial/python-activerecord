"""
Logging Chapter: Example 4 - Advanced Scenarios & Best Practices
Demonstrates core concepts:
1. Production configuration
2. Development configuration
3. Custom logger names for user models
4. Integration with application logging
"""

import logging
import sys
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.logging import (
    configure_logging,
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
    ActiveRecordFormatter,
)

# --- Models ---

class User(ActiveRecord):
    """User Model with custom logger name"""
    __table_name__ = "users"
    __logger_name__ = 'myapp.models.user'  # Custom logger name
    id: Optional[int] = None
    username: str
    password: str
    email: str

class Order(ActiveRecord):
    """Order Model"""
    __table_name__ = "orders"
    id: Optional[int] = None
    user_id: int
    total: float
    credit_card: str  # Sensitive field

# --- Configuration Presets ---

def configure_production_logging():
    """Configure logging for production environment."""
    manager = get_logging_manager()
    manager.reset()

    # Production: Use INFO level, summary mode
    configure_logging(
        level=logging.INFO,
        propagate=False,  # Don't propagate to root logger
    )

    # Backend: keys_only for security (PCI compliance)
    backend_config = LoggerConfig(
        name='rhosocial.activerecord.backend',
        log_data_mode='keys_only',
        level=logging.WARNING,  # Only warnings and above
    )
    manager.config.add_logger_config(backend_config)

    # Transaction: summary mode
    tx_config = LoggerConfig(
        name='rhosocial.activerecord.transaction',
        log_data_mode='summary',
        level=logging.INFO,
    )
    manager.config.add_logger_config(tx_config)

    # Model: summary with extra sensitive fields
    model_summarizer = SummarizerConfig(
        sensitive_fields={
            'password', 'token', 'api_key', 'secret',
            'credit_card', 'ssn', 'cvv', 'pin'
        },
        mask_placeholder='[REDACTED]',
    )
    model_config = LoggerConfig(
        name='rhosocial.activerecord.model',
        log_data_mode='summary',
        summarizer_config=model_summarizer,
    )
    manager.config.add_logger_config(model_config)

    print("Production logging configured:")
    print("  - Global level: INFO")
    print("  - Backend: keys_only, WARNING level (PCI compliant)")
    print("  - Model: summary with extended sensitive fields")
    return manager

def configure_development_logging():
    """Configure logging for development environment."""
    manager = get_logging_manager()
    manager.reset()

    # Development: Use DEBUG level, more verbose
    configure_logging(
        level=logging.DEBUG,
        propagate=True,  # Propagate to root logger for easy viewing
    )

    # Query: full mode for debugging queries
    query_config = LoggerConfig(
        name='rhosocial.activerecord.query',
        log_data_mode='full',
    )
    manager.config.add_logger_config(query_config)

    # Backend: summary mode (show some data for debugging)
    backend_config = LoggerConfig(
        name='rhosocial.activerecord.backend',
        log_data_mode='summary',
    )
    manager.config.add_logger_config(backend_config)

    print("Development logging configured:")
    print("  - Global level: DEBUG")
    print("  - Query: full mode (show complete queries)")
    print("  - Backend: summary mode")
    return manager

# --- Main Execution ---

def main():
    print("=" * 60)
    print("Example 4: Advanced Scenarios & Best Practices")
    print("=" * 60)

    test_data = {
        'username': 'john_doe',
        'password': 'my_password',
        'credit_card': '4111-1111-1111-1111',
        'cvv': '123',
    }

    # 1. Production Configuration
    print("\n" + "=" * 50)
    print("SCENARIO 1: Production Environment")
    print("=" * 50)

    manager = configure_production_logging()

    print("\nTest data with production config:")
    for logger_name in ['rhosocial.activerecord.backend',
                        'rhosocial.activerecord.model',
                        'rhosocial.activerecord.query']:
        result = manager.config.summarize_data(test_data, logger_name=logger_name)
        mode = manager.config.get_log_data_mode(logger_name)
        print(f"  {logger_name}: [{mode}] {result}")

    # 2. Development Configuration
    print("\n" + "=" * 50)
    print("SCENARIO 2: Development Environment")
    print("=" * 50)

    manager = configure_development_logging()

    print("\nTest data with development config:")
    for logger_name in ['rhosocial.activerecord.backend',
                        'rhosocial.activerecord.model',
                        'rhosocial.activerecord.query']:
        result = manager.config.summarize_data(test_data, logger_name=logger_name)
        mode = manager.config.get_log_data_mode(logger_name)
        print(f"  {logger_name}: [{mode}] {result}")

    # 3. Custom Logger Name for User Models
    print("\n" + "=" * 50)
    print("SCENARIO 3: Custom Logger Name")
    print("=" * 50)

    # User model has custom logger name
    print(f"User model logger name: {User._get_logger_name()}")
    print("User-defined models can have custom logger names for integration")
    print("with application logging infrastructure")

    # Configure custom handler for user model
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ActiveRecordFormatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))

    user_logger_config = LoggerConfig(
        name='myapp.models.user',
        level=logging.DEBUG,
        handlers=[handler],
    )
    manager.config.add_logger_config(user_logger_config)

    # 4. Integration with Application Logging
    print("\n" + "=" * 50)
    print("SCENARIO 4: Integration with Application Logging")
    print("=" * 50)

    # You can also configure propagation
    # This allows ActiveRecord logs to be captured by your application's root logger

    # Setup application root logger
    app_handler = logging.StreamHandler(sys.stdout)
    app_handler.setFormatter(logging.Formatter(
        '[APP] %(name)s - %(levelname)s: %(message)s'
    ))
    root_logger = logging.getLogger()
    root_logger.addHandler(app_handler)
    root_logger.setLevel(logging.DEBUG)

    # Configure propagation for ActiveRecord loggers
    configure_logging(propagate=True)

    print("With propagation enabled, ActiveRecord logs go to root logger")
    print("This allows unified log handling across your application")

    # 5. Best Practices Summary
    print("\n" + "=" * 50)
    print("BEST PRACTICES SUMMARY")
    print("=" * 50)

    print("""
1. PRODUCTION ENVIRONMENT:
   - Use INFO or WARNING level
   - Set backend to keys_only for security
   - Never use 'full' mode in production
   - Add application-specific sensitive fields

2. DEVELOPMENT ENVIRONMENT:
   - Use DEBUG level for verbose output
   - Can use 'full' mode temporarily for debugging
   - Set propagate=True for easy viewing

3. COMPLIANCE (GDPR/PCI):
   - Use keys_only mode for sensitive operations
   - Ensure sensitive_fields includes all PII
   - Consider custom placeholder for audit trails

4. PERFORMANCE:
   - Avoid 'full' mode with large datasets
   - Use keys_only for high-frequency logging
   - Configure appropriate log levels per component

5. INTEGRATION:
   - Use custom __logger_name__ for user models
   - Configure propagate=True for centralized logging
   - Share formatter with application logger
""")

if __name__ == "__main__":
    main()
