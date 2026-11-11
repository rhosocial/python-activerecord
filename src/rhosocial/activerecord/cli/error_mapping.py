# src/rhosocial/activerecord/cli/error_mapping.py
"""Translate model and backend exceptions into CLI errors.

The CLI never changes framework semantics: models still raise their own
exceptions, and this module only decides which command-level error and exit
code describes them. Every translation keeps the original exception chain with
``raise translated from exc``.

The model layer raises ``RecordNotFound``; the CLI layer raises
``CliNotFoundError``. They stay separate classes because one describes a query
result and the other describes a command outcome and exit code.
"""

from typing import Optional

from pydantic import ValidationError as PydanticValidationError

from ..backend.errors import (
    BulkStateError,
    BulkValidationError,
    ConcurrencyError,
    ConnectionError as BackendConnectionError,
    DataError,
    DatabaseError,
    DeadlockError,
    InfrastructureError,
    IntegrityError,
    LockError,
    OperationalError,
    PolicyError,
    QueryError,
    ReadOnlyError,
    RecordError,
    RecordNotFound,
    StaleRecordError,
    TransactionError,
    TypeConversionError,
    UnaddressableRecordError,
    ValidationError as DBValidationError,
)
from .errors import CLIError, CliNotFoundError, ReadOnlyModelError, EXIT_READ_ONLY


def _pydantic_summary(error: PydanticValidationError) -> str:
    """Return the first error as ``field: message``."""
    details = error.errors()
    if not details:
        return str(error)
    first = details[0]
    location = ".".join(str(part) for part in first.get("loc", ()))
    message = first.get("msg", "")
    return f"{location}: {message}" if location else message


def operation_context(operation: str) -> str:
    """Return `` during <operation>`` or an empty string."""
    return f" during {operation}" if operation else ""


def translate_error(
    exc: Exception,
    *,
    operation: str = "",
    model=None,
    pk=None,
) -> Optional[CLIError]:
    """Return the CLI error that describes ``exc``, or ``None`` if unknown.

    Args:
        exc: The exception raised by a model or backend call.
        operation: Command label such as ``"dml update"``; used in the message.
        model: Optional model class, used when the message needs a name.
        pk: Optional primary key, used for not-found and update messages.
    """
    context = operation_context(operation)
    model_name = model.__name__ if model is not None else "model"

    if isinstance(exc, CLIError):
        return exc
    if isinstance(exc, PydanticValidationError):
        return CLIError(f"Invalid data for {model_name}: {_pydantic_summary(exc)}")
    if isinstance(exc, UnaddressableRecordError):
        if model is not None:
            return CLIError(
                f"{model.__name__} has no primary key; {operation or 'this command'} cannot "
                "address a single row. Use `dql list --where ...` instead."
            )
        return CLIError(str(exc))
    if isinstance(exc, RecordNotFound):
        if pk is not None:
            return CliNotFoundError(f"{model_name} with pk={pk!r} was not found")
        return CliNotFoundError(str(exc))
    if isinstance(exc, ReadOnlyError):
        return ReadOnlyModelError(exc.model_name, exc.operation)
    if isinstance(exc, StaleRecordError):
        return CLIError(
            f"Record version mismatch{context}; it may have been updated or deleted "
            "by another process. Reload the record and retry."
        )
    if isinstance(exc, DeadlockError):
        return CLIError(f"Deadlock detected{context}; retry the operation")
    if isinstance(exc, LockError):
        return CLIError(f"Record is locked{context}; retry after the lock clears")
    if isinstance(exc, BulkValidationError):
        details = getattr(exc, "errors", None) or []
        if details:
            index, message = details[0]
            return CLIError(f"Bulk operation failed at item {index + 1}: {message}")
        return CLIError(str(exc))
    if isinstance(exc, BulkStateError):
        return CLIError(f"Bulk operation cannot run{context}: {exc}")
    if isinstance(exc, IntegrityError):
        return CLIError(f"Integrity constraint failed{context}: {exc}")
    if isinstance(exc, TypeConversionError):
        return CLIError(f"Invalid value{context}: {exc}")
    if isinstance(exc, DBValidationError):
        return CLIError(f"Invalid data for {model_name}{context}: {exc}")
    if isinstance(exc, BackendConnectionError):
        return CLIError(f"Database connection failed{context}: {exc}")
    if isinstance(exc, OperationalError):
        return CLIError(f"Database operation failed{context}: {exc}")
    if isinstance(exc, QueryError):
        return CLIError(f"Query failed{context}: {exc}")
    if isinstance(exc, TransactionError):
        return CLIError(f"Database transaction failed{context}: {exc}")
    # Category fallbacks: backend-specific subclasses inherit these bases, so a
    # new driver-specific error still gets a sensible message and exit code.
    if isinstance(exc, PolicyError):
        if exc.model_name and exc.operation:
            return ReadOnlyModelError(exc.model_name, exc.operation)
        return CLIError(f"Operation refused by policy{context}: {exc}", exit_code=EXIT_READ_ONLY)
    if isinstance(exc, RecordError):
        return CLIError(f"Record error{context}: {exc}")
    if isinstance(exc, ConcurrencyError):
        return CLIError(
            f"Concurrency conflict{context}: {exc}. Reload the record and retry."
        )
    if isinstance(exc, InfrastructureError):
        return CLIError(f"Database infrastructure error{context}: {exc}")
    if isinstance(exc, DataError):
        return CLIError(f"Invalid data{context}: {exc}")
    if isinstance(exc, DatabaseError):
        return CLIError(f"Database error{context}: {exc}")
    return None


def operation_label(args) -> str:
    """Build a human-readable command label from parsed arguments."""
    section = getattr(args, "section", None)
    if section == "dml":
        command = getattr(args, "bulk_command", None)
        if getattr(args, "command", None) == "bulk" and command:
            return f"dml bulk {command}"
        if getattr(args, "command", None):
            return f"dml {args.command}"
    if section == "dql" and getattr(args, "command", None):
        return f"dql {args.command}"
    if section == "set" and getattr(args, "set_operation", None):
        return f"set {args.set_operation}"
    if section == "cte":
        return "cte run"
    return section or "command"
