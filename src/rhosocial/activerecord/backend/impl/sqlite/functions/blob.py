# src/rhosocial/activerecord/backend/impl/sqlite/functions/blob.py
"""
SQLite BLOB function factories.

Functions: zeroblob, randomblob
"""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.functions import FunctionCall
from rhosocial.activerecord.backend.expression.value_types import Parameter

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def zeroblob(dialect: "SQLDialectBase", length: int) -> "FunctionCall":
    """
    Creates a ZEROBLOB function call.

    Returns a BLOB of the specified length filled with zeros.

    Usage:
        - zeroblob(dialect, 100) -> ZEROBLOB(100)

    Args:
        dialect: The SQL dialect instance
        length: Length of the BLOB in bytes

    Returns:
        A FunctionCall instance representing the ZEROBLOB function
    """
    return FunctionCall(dialect, "ZEROBLOB", Parameter(dialect, length))


def randomblob(dialect: "SQLDialectBase", length: int) -> "FunctionCall":
    """
    Creates a RANDOMBLOB function call.

    Returns a BLOB of the specified length filled with random bytes.

    Usage:
        - randomblob(dialect, 16) -> RANDOMBLOB(16)

    Args:
        dialect: The SQL dialect instance
        length: Length of the BLOB in bytes

    Returns:
        A FunctionCall instance representing the RANDOMBLOB function
    """
    return FunctionCall(dialect, "RANDOMBLOB", Parameter(dialect, length))


__all__ = [
    "zeroblob",
    "randomblob",
]
