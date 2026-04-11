# src/rhosocial/activerecord/backend/expression/functions/system.py
"""System information function factories."""

from typing import TYPE_CHECKING

from ..core import FunctionCall

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def current_user(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a CURRENT_USER function call.

    SQL:2003 standard function returning the current user name.

    Usage rules:
    - To generate CURRENT_USER: current_user(dialect)

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the CURRENT_USER function
    """
    return FunctionCall(dialect, "CURRENT_USER")


def session_user(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a SESSION_USER function call.

    SQL:2003 standard function returning the session user name.

    Usage rules:
    - To generate SESSION_USER: session_user(dialect)

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the SESSION_USER function
    """
    return FunctionCall(dialect, "SESSION_USER")


def system_user(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a SYSTEM_USER function call.

    SQL:2003 standard function returning the system user name.

    Usage rules:
    - To generate SYSTEM_USER: system_user(dialect)

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the SYSTEM_USER function
    """
    return FunctionCall(dialect, "SYSTEM_USER")
