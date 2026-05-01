# src/rhosocial/activerecord/backend/named_query/exceptions.py
"""
Custom exceptions for named query functionality.

This module defines all exception types that can be raised during named query
resolution and execution. Each exception includes detailed information about
the error condition and helpful suggestions for resolution.

Exception Hierarchy:
    NamedQueryError (base)
    ├── NamedQueryNotFoundError
    ├── NamedQueryModuleNotFoundError
    ├── NamedQueryInvalidReturnTypeError
    ├── NamedQueryInvalidParameterError
    ├── NamedQueryMissingParameterError
    ├── NamedQueryNotCallableError
    └── NamedQueryExplainNotAllowedError

Usage:
    >>> try:
    ...     resolver = NamedQueryResolver("myapp.queries.user_active").load()
    ... except NamedQueryModuleNotFoundError as e:
    ...     print(f"Module error: {e}")
    ... except NamedQueryNotFoundError as e:
    ...     print(f"Query not found: {e}")
"""


class NamedQueryError(Exception):
    """Base exception for all named query errors.

    This is the root exception class from which all named-query-specific
    exceptions inherit. It provides the basic interface for error handling
    across the named query system.

    Attributes:
        message: The error message describing what went wrong.

    Example:
        >>> try:
        ...     # some named query operation
        ... except NamedQueryError as e:
        ...     print(f"Named query error: {e}")
    """

    pass


class NamedQueryNotFoundError(NamedQueryError):
    """Raised when a named query callable cannot be found.

    This exception indicates that the specified qualified name does not
    exist as a callable attribute in the specified module. This can
    happen due to:
    - Typo in the qualified name
    - The callable was not exported from the module
    - The module path is incorrect

    Args:
        qualified_name: The fully qualified name that was attempted.
        message: Optional additional error details.

    Attributes:
        qualified_name: The fully qualified name that was not found.

    Example:
        >>> raise NamedQueryNotFoundError(
        ...     "myapp.queries.user_active",
        ...     "Check if the function is exported in __all__"
        ... )
    """

    def __init__(self, qualified_name: str, message: str = ""):
        self.qualified_name = qualified_name
        error_msg = f"Named query not found: {qualified_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryModuleNotFoundError(NamedQueryError):
    """Raised when a module cannot be imported.

    This exception indicates that the specified module does not exist or
    cannot be found in the Python path. This can happen due to:
    - Module not installed in the environment
    - Module path not in PYTHONPATH
    - Typo in the module name
    - Module file was deleted or renamed

    Args:
        module_name: The name of the module that could not be imported.
        message: Optional additional error details.

    Attributes:
        module_name: The name of the module that was not found.

    Example:
        >>> raise NamedQueryModuleNotFoundError(
        ...     "myapp.queries",
        ...     "Ensure the package is installed or in PYTHONPATH"
        ... )
    """

    def __init__(self, module_name: str, message: str = ""):
        self.module_name = module_name
        error_msg = f"Module not found: {module_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryInvalidReturnTypeError(NamedQueryError):
    """Raised when a named query returns an invalid type.

    This exception indicates that the callable returned a type that does
    not implement BaseExpression. The named query system requires that
    all callables return a BaseExpression object to ensure type safety
    and SQL injection prevention.

    This is a security-related exception: direct SQL strings are not
    allowed because they can lead to SQL injection vulnerabilities.

    Args:
        qualified_name: The fully qualified name of the callable.
        actual_type: The type name that was actually returned.
        message: Optional additional error details.

    Attributes:
        qualified_name: The qualified name that returned invalid type.
        actual_type: The type name that was returned.

    Warning:
        This exception is raised for security reasons. Do not return
        raw SQL strings from named query callables. If you need to
        execute raw SQL, use the 'query' subcommand instead.

    Example:
        >>> raise NamedQueryInvalidReturnTypeError(
        ...     "myapp.queries.raw_sql",
        ...     "str",
        ...     "Use query subcommand for raw SQL"
        ... )
    """

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
    """Raised when a parameter is invalid or unknown.

    This exception indicates that an invalid or unknown parameter
    was provided to the named query. This can happen due to:
    - Typo in parameter name
    - Parameter not defined in the callable signature
    - Incorrect parameter type that cannot be converted

    Args:
        param_name: The name of the invalid parameter.
        message: Optional additional error details including
            available parameters.

    Attributes:
        param_name: The name of the problematic parameter.

    Example:
        >>> raise NamedQueryInvalidParameterError(
        ...     "user_id",
        ...     "Unknown parameter. Available: user_id, status"
        ... )
    """

    def __init__(self, param_name: str, message: str = ""):
        self.param_name = param_name
        error_msg = f"Invalid parameter: {param_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryMissingParameterError(NamedQueryError):
    """Raised when a required parameter is missing.

    This exception indicates that a required parameter was not
    provided to the named query. The callable has a parameter that
    does not have a default value, so it must be provided.

    Args:
        param_name: The name of the missing parameter.
        message: Optional additional error details.

    Attributes:
        param_name: The name of the missing parameter.

    Example:
        >>> raise NamedQueryMissingParameterError(
        ...     "user_id",
        ...     "Required parameter 'user_id' not provided"
        ... )
    """

    def __init__(self, param_name: str, message: str = ""):
        self.param_name = param_name
        error_msg = f"Missing required parameter: {param_name}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryNotCallableError(NamedQueryError):
    """Raised when the target is not callable.

    This exception indicates that the specified attribute exists
    but is not a callable (function, method, or class with __call__).
    Only callable objects can be used as named queries.

    Args:
        qualified_name: The fully qualified name that is not callable.
        message: Optional additional error details.

    Attributes:
        qualified_name: The qualified name that is not callable.

    Example:
        >>> raise NamedQueryNotCallableError(
        ...     "myapp.queries.user_active",
        ...     "Must be a function, method, or class with __call__"
        ... )
    """

    def __init__(self, qualified_name: str, message: str = ""):
        self.qualified_name = qualified_name
        error_msg = f"Named query '{qualified_name}' is not callable"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class NamedQueryExplainNotAllowedError(NamedQueryError):
    """Raised when EXPLAIN query execution is not allowed.

    This exception indicates that an EXPLAIN query was attempted
    to be executed without the proper flag. EXPLAIN queries
    should typically be run with --dry-run or --explain to show
    the execution plan without actually modifying data.

    Args:
        message: Optional custom error message.

    Warning:
        EXPLAIN queries can return large result sets and may
        have performance implications. Always use --dry-run first
        to preview the query plan.

    Example:
        >>> raise NamedQueryExplainNotAllowedError(
        ...     "EXPLAIN requires --explain or --dry-run flag"
        ... )
    """

    def __init__(
        self, message: str = "EXPLAIN queries are not allowed for actual execution"
    ):
        super().__init__(message)


class ProcedureError(NamedQueryError):
    """Base exception for named procedure errors."""

    pass


class ProcedureAbortedError(ProcedureError):
    """Raised when a procedure is aborted via ctx.abort().

    This exception indicates that the procedure was intentionally
    aborted by the procedure logic, usually due to a business
    rule condition. This is NOT an error in the traditional
    sense - it indicates the procedure stopped early
    by design, and any changes should be rolled back.

    Args:
        procedure_name: The qualified name of the procedure.
        reason: The reason for aborting.

    Attributes:
        procedure_name: The procedure that was aborted.
        reason: The abort reason.

    Example:
        >>> raise ProcedureAbortedError(
        ...     "myapp.procedures.monthly_report",
        ...     "Total count below threshold"
        ... )
    """

    def __init__(self, procedure_name: str, reason: str):
        self.procedure_name = procedure_name
        self.reason = reason
        error_msg = f"Procedure '{procedure_name}' aborted: {reason}"
        super().__init__(error_msg)


class _ProcedureAbortSignal(ProcedureError):
    """Internal signal for procedure abort.

    This exception is used internally to signal that a procedure
    wants to abort. It carries the abort reason but is not
    meant to be caught by user code.
    """

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class ProcedureStepError(ProcedureError):
    """Raised when a procedure step fails.

    This exception indicates that a step within the
    procedure failed to execute. The procedure should
    be rolled back.

    Args:
        step: The step number or identifier.
        procedure_name: The qualified name of the procedure.
        cause: The underlying error.

    Attributes:
        step: The step that failed.
        procedure_name: The procedure that contained the step.
        cause: The underlying exception.

    Example:
        >>> raise ProcedureStepError(
        ...     3,
        ...     "myapp.procedures.monthly_report",
        ...     "SQL execution failed"
        ... )
    """

    def __init__(self, step: int, procedure_name: str, cause: str):
        self.step = step
        self.procedure_name = procedure_name
        self.cause = cause
        error_msg = (
            f"Procedure '{procedure_name}' failed at step {step}: {cause}"
        )
        super().__init__(error_msg)