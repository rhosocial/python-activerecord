# src/rhosocial/activerecord/backend/dialect/exceptions.py
"""
Exceptions for SQL dialect feature support.

This module defines exceptions raised when dialects don't support requested
features or haven't implemented required protocols.
"""
from typing import Optional


class UnsupportedFeatureError(Exception):
    """
    Raised when a dialect doesn't support a specific feature.

    This exception is raised when code attempts to use a database feature
    that the current dialect doesn't support.
    """

    def __init__(
            self,
            dialect_name: str,
            feature_name: str,
            suggestion: Optional[str] = None
    ):
        """
        Initialize unsupported feature error.

        Args:
            dialect_name: Name of the dialect
            feature_name: Name of the unsupported feature
            suggestion: Optional suggestion for alternative approach
        """
        self.dialect_name = dialect_name
        self.feature_name = feature_name
        self.suggestion = suggestion

        message = f"'{dialect_name}' dialect does not support {feature_name}."
        if suggestion:
            message += f" Suggestion: {suggestion}"

        super().__init__(message)


class ProtocolNotImplementedError(Exception):
    """
    Raised when a dialect hasn't implemented a required protocol.

    This exception is raised when code requires a specific protocol interface
    but the dialect hasn't implemented it.
    """

    def __init__(
            self,
            dialect_name: str,
            protocol_name: str,
            required_by: str
    ):
        """
        Initialize protocol not implemented error.

        Args:
            dialect_name: Name of the dialect
            protocol_name: Name of the missing protocol
            required_by: Name of the component requiring the protocol
        """
        self.dialect_name = dialect_name
        self.protocol_name = protocol_name
        self.required_by = required_by

        message = (
            f"'{dialect_name}' dialect does not implement {protocol_name} protocol, "
            f"which is required by {required_by}."
        )
        super().__init__(message)