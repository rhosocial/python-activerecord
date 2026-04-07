"""
Logging Chapter: Example 2 - Data Summarization
Demonstrates core concepts:
1. Sensitive field masking
2. Data truncation
3. Three logging modes: summary, keys_only, full
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
    SummarizerConfig,
)

# --- Models ---


class User(ActiveRecord):
    """User Model with sensitive fields"""

    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str  # Will be masked
    email: str
    api_key: str  # Will be masked
    bio: str  # Long text, will be truncated


# --- Main Execution ---


def main():
    print("=" * 60)
    print("Example 2: Data Summarization")
    print("=" * 60)

    # Configure logging
    configure_logging(level=logging.DEBUG)

    # Setup database
    config = SQLiteConnectionConfig(database=":memory:")
    User.configure(config, SQLiteBackend)
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

    manager = get_logging_manager()
    test_data = {
        "username": "john_doe",
        "password": "super_secret_password_123",
        "email": "john@example.com",
        "api_key": "sk-api-key-12345-abcdef",
        "bio": "This is a very long biography " * 20,  # ~600 chars
    }

    # 1. Summary Mode (Default)
    print("\n" + "-" * 40)
    print("1. Summary Mode (Default)")
    print("-" * 40)

    manager.config.log_data_mode = "summary"
    summary_result = manager.config.summarize_data(test_data)
    print(f"Result: {summary_result}")
    print("\nNote: password and api_key are masked, bio is truncated")

    # 2. Keys-Only Mode
    print("\n" + "-" * 40)
    print("2. Keys-Only Mode")
    print("-" * 40)

    manager.config.log_data_mode = "keys_only"
    keys_result = manager.config.summarize_data(test_data)
    print(f"Result: {keys_result}")
    print("\nNote: Only field names with type hints, values hidden")

    # 3. Full Mode (Use with caution!)
    print("\n" + "-" * 40)
    print("3. Full Mode (WARNING: Shows sensitive data!)")
    print("-" * 40)

    manager.config.log_data_mode = "full"
    full_result = manager.config.summarize_data(test_data)
    print(f"Result: {full_result}")
    print("\nWARNING: Sensitive data is visible! Use only for debugging.")

    # 4. Custom Sensitive Fields
    print("\n" + "-" * 40)
    print("4. Custom Sensitive Fields")
    print("-" * 40)

    custom_config = SummarizerConfig(
        sensitive_fields={"password", "api_key", "email"},  # Add email to masked fields
        max_string_length=30,  # Shorter truncation
        mask_placeholder="[REDACTED]",
    )
    manager.config.summarizer_config = custom_config
    manager.config.log_data_mode = "summary"

    custom_result = manager.config.summarize_data(test_data)
    print(f"Result: {custom_result}")
    print("\nNote: email is now also masked, shorter truncation, custom placeholder")

    # 5. Custom Field Maskers (Lambda Functions)
    print("\n" + "-" * 40)
    print("5. Custom Field Maskers (Lambda Functions)")
    print("-" * 40)

    masker_config = SummarizerConfig(
        sensitive_fields={"password", "email", "api_key"},
        # Global callable mask_placeholder (used when no field-specific masker)
        mask_placeholder=lambda v: f"<{len(str(v))} chars hidden>",
        # Field-specific maskers
        field_maskers={
            # Partially reveal email format (show first char of local part)
            "email": lambda v: v.split("@")[0][:1] + "***@" + v.split("@")[1] if "@" in str(v) else "***",
            # Show password length as asterisks
            "password": lambda v: "*" * min(len(str(v)), 8),
        },
    )
    manager.config.summarizer_config = masker_config
    manager.config.log_data_mode = "summary"

    masker_result = manager.config.summarize_data(test_data)
    print(f"Result: {masker_result}")
    print("\nNote: email shows partial format, password shows asterisks, api_key uses global callable")

    # 6. Using log_data method in models
    print("\n" + "-" * 40)
    print("6. Using log_data Method")
    print("-" * 40)

    # Reset to default config
    manager.reset()
    manager.config.log_data_mode = "summary"

    # log_data automatically applies summarization
    User.log_data(logging.INFO, "Test data log", test_data)

    # Convenience methods
    User.log_data_keys_only(logging.INFO, "Keys only", test_data)

    # 7. Real database operation with summarization
    print("\n" + "-" * 40)
    print("7. Real Database Operation")
    print("-" * 40)

    # Password will be masked in logs automatically
    user = User(
        username="alice",
        password="my_secret_password",
        email="alice@example.com",
        api_key="sk-12345",
        bio="A" * 200,  # Long bio
    )
    user.save()
    print(f"Created user: {user.username}")
    print("\nObserve the logs above - sensitive fields are automatically masked!")


if __name__ == "__main__":
    main()
