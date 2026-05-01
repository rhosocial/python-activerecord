# src/rhosocial/activerecord/backend/named_connection/validators.py
"""
Validators for named connection functionality.

This module provides validation functions to ensure named connection
callables return valid ConnectionConfig instances.
"""

from typing import Type

from rhosocial.activerecord.backend.config import BaseConfig

from .exceptions import NamedConnectionInvalidReturnTypeError


# Sensitive field names that should be filtered in describe()
SENSITIVE_FIELDS = frozenset({
    "password",
    "secret",
    "token",
    "api_key",
    "private_key",
})


def validate_connection_config(
    config: BaseConfig,
    qualified_name: str,
) -> Type[BaseConfig]:
    """Validate that a config is a ConnectionConfig subclass.

    This function checks that the returned object is a BaseConfig subclass,
    which is required for all named connections to ensure type-safe
    connection configuration.

    Args:
        config: The config object to validate.
        qualified_name: The qualified name of the named connection (used for error messages).

    Returns:
        Type[BaseConfig]: The type of the validated config.

    Raises:
        NamedConnectionInvalidReturnTypeError: If config is not a BaseConfig subclass.

    Example:
        >>> from rhosocial.activerecord.backend.config import BaseConfig
        >>> config = MySQLConnectionConfig(host="localhost")
        >>> validate_connection_config(config, "myapp.connections.prod")
        <class 'MySQLConnectionConfig'>
    """
    if not isinstance(config, BaseConfig):
        raise NamedConnectionInvalidReturnTypeError(
            qualified_name,
            type(config).__name__,
            "Config must be a BaseConfig subclass",
        )
    return type(config)


def filter_sensitive_fields(data: dict) -> dict:
    """Filter sensitive fields from a config dictionary.

    This function removes sensitive fields like password, secret, token, etc.
    from the dictionary before returning it for describe() output.

    Args:
        data: The config dictionary to filter.

    Returns:
        dict: The filtered dictionary without sensitive fields.

    Example:
        >>> data = {"host": "localhost", "password": "secret", "username": "user"}
        >>> filter_sensitive_fields(data)
        {"host": "localhost", "username": "user"}
    """
    return {k: v for k, v in data.items() if k not in SENSITIVE_FIELDS}
