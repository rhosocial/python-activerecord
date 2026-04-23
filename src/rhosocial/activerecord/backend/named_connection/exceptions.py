# src/rhosocial/activerecord/backend/named_connection/exceptions.py
"""
Custom exceptions for named connection functionality.

This module defines all exception types that can be raised during named connection
resolution. Each exception includes detailed information about the error condition.

Exception Hierarchy:
    NamedConnectionError (base)
    ├── NamedConnectionNotFoundError
    ├── NamedConnectionModuleNotFoundError
    ├── NamedConnectionInvalidReturnTypeError
    ├── NamedConnectionInvalidParameterError
    ├── NamedConnectionMissingParameterError
    ├── NamedConnectionNotCallableError

Usage:
    >>> try:
    ...     resolver = NamedConnectionResolver("myapp.connections.prod_db").load()
    ... except NamedConnectionModuleNotFoundError as e:
    ...     print(f"Module error: {e}")
    ... except NamedConnectionNotFoundError as e:
    ...     print(f"Connection not found: {e}")
"""


class NamedConnectionError(Exception):
    """Base exception for all named connection errors.

    This is the root exception class from which all named-connection-specific
    exceptions inherit. It provides the basic interface for error handling
    across the named connection system.

    Attributes:
        message: The error message describing what went wrong.
    """

    pass


class NamedConnectionNotFoundError(NamedConnectionError):
    """Raised when a named connection callable cannot be found.

    This exception indicates that the specified qualified name does not
    exist as a callable attribute in the specified module.

    Args:
        qualified_name: The fully qualified name that was attempted.
        message: Optional additional error details.

    Attributes:
        qualified_name: The fully qualified name that was not found.
    """

    def __init__(self, qualified_name: str, message: str = ""):
        self.qualified_name = qualified_name
        error_msg = f"Named connection not found: {qualified_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedConnectionModuleNotFoundError(NamedConnectionError):
    """Raised when a module cannot be imported.

    This exception indicates that the specified module does not exist or
    cannot be found in the Python path.

    Args:
        module_name: The name of the module that could not be imported.
        message: Optional additional error details.

    Attributes:
        module_name: The name of the module that was not found.
    """

    def __init__(self, module_name: str, message: str = ""):
        self.module_name = module_name
        error_msg = f"Module not found: {module_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedConnectionInvalidReturnTypeError(NamedConnectionError):
    """Raised when a named connection returns an invalid type.

    This exception indicates that the callable returned a type that does
    not implement ConnectionConfig. All named connection callables must
    return a ConnectionConfig subclass.

    Args:
        qualified_name: The fully qualified name of the callable.
        actual_type: The type name that was actually returned.
        message: Optional additional error details.

    Attributes:
        qualified_name: The qualified name that returned invalid type.
        actual_type: The type name that was returned.
    """

    def __init__(self, qualified_name: str, actual_type: str, message: str = ""):
        self.qualified_name = qualified_name
        self.actual_type = actual_type
        error_msg = (
            f"Named connection '{qualified_name}' returned {actual_type}, "
            f"not ConnectionConfig. Named connections must return ConnectionConfig."
        )
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedConnectionInvalidParameterError(NamedConnectionError):
    """Raised when a parameter is invalid or unknown.

    Args:
        param_name: The name of the invalid parameter.
        message: Optional additional error details.

    Attributes:
        param_name: The name of the problematic parameter.
    """

    def __init__(self, param_name: str, message: str = ""):
        self.param_name = param_name
        error_msg = f"Invalid parameter: {param_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedConnectionMissingParameterError(NamedConnectionError):
    """Raised when a required parameter is missing.

    Args:
        param_name: The name of the missing parameter.
        message: Optional additional error details.

    Attributes:
        param_name: The name of the missing parameter.
    """

    def __init__(self, param_name: str, message: str = ""):
        self.param_name = param_name
        error_msg = f"Missing required parameter: {param_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedConnectionNotCallableError(NamedConnectionError):
    """Raised when the target is not callable.

    Args:
        qualified_name: The fully qualified name that is not callable.
        message: Optional additional error details.

    Attributes:
        qualified_name: The qualified name that is not callable.
    """

    def __init__(self, qualified_name: str, message: str = ""):
        self.qualified_name = qualified_name
        error_msg = f"Named connection '{qualified_name}' is not callable"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)
