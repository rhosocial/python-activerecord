# src/rhosocial/activerecord/backend/named_query/exceptions.py
"""
Custom exceptions for named query functionality.
"""


class NamedQueryError(Exception):
    """Base exception for named query errors."""

    pass


class NamedQueryNotFoundError(NamedQueryError):
    """Raised when a named query cannot be found."""

    def __init__(self, qualified_name: str, message: str = ""):
        self.qualified_name = qualified_name
        error_msg = f"Named query not found: {qualified_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryModuleNotFoundError(NamedQueryError):
    """Raised when a module cannot be found."""

    def __init__(self, module_name: str, message: str = ""):
        self.module_name = module_name
        error_msg = f"Module not found: {module_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryInvalidReturnTypeError(NamedQueryError):
    """Raised when a named query returns an invalid type."""

    def __init__(self, qualified_name: str, actual_type: str, message: str = ""):
        self.qualified_name = qualified_name
        self.actual_type = actual_type
        error_msg = (
            f"Named query '{qualified_name}' returned {actual_type}, "
            f"not BaseExpression. Direct SQL strings are not allowed for safety. "
            f"Use 'query' subcommand for raw SQL execution."
        )
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryInvalidParameterError(NamedQueryError):
    """Raised when a parameter is invalid."""

    def __init__(self, param_name: str, message: str = ""):
        self.param_name = param_name
        error_msg = f"Invalid parameter: {param_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryMissingParameterError(NamedQueryError):
    """Raised when a required parameter is missing."""

    def __init__(self, param_name: str, message: str = ""):
        self.param_name = param_name
        error_msg = f"Missing required parameter: {param_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryNotCallableError(NamedQueryError):
    """Raised when the named query target is not callable."""

    def __init__(self, qualified_name: str, message: str = ""):
        self.qualified_name = qualified_name
        error_msg = f"Named query '{qualified_name}' is not callable"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryExplainNotAllowedError(NamedQueryError):
    """Raised when EXPLAIN is not allowed for execution."""

    def __init__(self, message: str = "EXPLAIN queries are not allowed for actual execution"):
        super().__init__(message)