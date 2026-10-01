# src/rhosocial/activerecord/backend/expression/functions/system.py
"""System information function factories."""

from typing import TYPE_CHECKING

from ...dialect.exceptions import UnsupportedFeatureError
from ..core import FunctionCall

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def current_schema_unsupported(dialect: "SQLDialectBase", reason: str) -> None:
    """Reject a current-schema query for a backend that has no such concept.

    A backend whose SQL has no session-level namespace -- SQLite has no schema
    layer at all, BigQuery binds a dataset per query rather than as session
    state -- cannot answer this. Rather than substitute a default namespace,
    which would be a guess, this raises so the caller passes one explicitly.

    Args:
        dialect: The SQL dialect instance
        reason: Why this dialect has no current schema, phrased for the user

    Raises:
        UnsupportedFeatureError: Always.
    """
    raise UnsupportedFeatureError(dialect.name, "reading the current schema", reason)


def current_user(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a CURRENT_USER niladic value function.

    SQL:2003 standard niladic function — generates CURRENT_USER
    without parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the CURRENT_USER value function
    """
    return FunctionCall(dialect, "CURRENT_USER", niladic=True)


def session_user(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a SESSION_USER niladic value function.

    SQL:2003 standard niladic function — generates SESSION_USER
    without parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the SESSION_USER value function
    """
    return FunctionCall(dialect, "SESSION_USER", niladic=True)


def system_user(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a SYSTEM_USER niladic value function.

    SQL:2003 standard niladic function — generates SYSTEM_USER
    without parentheses, as required by the standard.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the SYSTEM_USER value function
    """
    return FunctionCall(dialect, "SYSTEM_USER", niladic=True)
