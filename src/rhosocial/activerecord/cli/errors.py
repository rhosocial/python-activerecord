# src/rhosocial/activerecord/cli/errors.py
"""Exit codes and user-facing errors for the ActiveRecord model CLI."""

import sys
from typing import Optional

#: Successful command.
EXIT_OK = 0

#: Model loading, connection, validation, or database failure.
EXIT_ERROR = 1

#: argparse owns this code; it is documented here for callers reading the list.
EXIT_USAGE = 2

#: A record addressed by primary key does not exist.
EXIT_NOT_FOUND = 3

#: The selected backend package is not installed or is unknown.
EXIT_BACKEND_UNAVAILABLE = 4

#: A destructive command needs --yes in a non-interactive context.
EXIT_CONFIRMATION_REQUIRED = 5

#: A DML command was attempted on a model that declares itself read-only.
EXIT_READ_ONLY = 6

#: A downstream pipe closed before the CLI finished writing.
EXIT_BROKEN_PIPE = 141


class CLIError(Exception):
    """A recoverable CLI failure with its process exit code.

    Args:
        message: Human-readable explanation, printed to stderr.
        exit_code: The process exit code that represents this failure.
        hint: Optional follow-up line, such as an install command.
    """

    def __init__(self, message: str, exit_code: int = EXIT_ERROR, hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.hint = hint


class NotFoundError(CLIError):
    """The requested record does not exist."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=EXIT_NOT_FOUND)


class BackendUnavailableError(CLIError):
    """The backend named by the user cannot be loaded."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message, exit_code=EXIT_BACKEND_UNAVAILABLE, hint=hint)


class ConfirmationRequiredError(CLIError):
    """A destructive command needs --yes because stdin/stdout is not a TTY."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=EXIT_CONFIRMATION_REQUIRED)


class ReadOnlyModelError(CLIError):
    """DML was refused because the model declares itself read-only."""

    def __init__(self, model_name: str, operation: str):
        super().__init__(
            f"{model_name} is read-only (__read_only__ = True); "
            f"'{operation}' is not allowed.",
            exit_code=EXIT_READ_ONLY,
        )


def report_error(error: CLIError) -> None:
    """Write an error, and an optional hint, to stderr."""
    print(f"Error: {error.message}", file=sys.stderr)
    if error.hint:
        print(error.hint, file=sys.stderr)


def report_unexpected(error: Exception) -> None:
    """Write an unexpected failure to stderr without polluting stdout."""
    print(f"Error: {error}", file=sys.stderr)
