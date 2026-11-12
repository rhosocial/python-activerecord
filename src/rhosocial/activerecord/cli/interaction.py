# src/rhosocial/activerecord/cli/interaction.py
"""TTY, pagination, confirmation, and read-only helpers."""

import sys
from typing import Optional

from ..interface.update import IDeleteBehavior
from .args import DEFAULT_LIST_LIMIT
from .errors import (
    CancelledError,
    CLIError,
    ConfirmationRequiredError,
    ReadOnlyModelError,
)


def is_tty() -> bool:
    """Whether stdout is an interactive terminal."""
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def resolve_output(args) -> str:
    """Return the explicit output format, or a TTY-aware default."""
    output = getattr(args, "output", None)
    if output:
        return output
    return "table" if is_tty() else "json"


def _has_limit(query) -> bool:
    clause = getattr(query, "limit_offset_clause", None)
    return clause is not None and getattr(clause, "limit", None) is not None


def apply_pagination(query, args, *, default: bool = True, label: str = "result"):
    """Apply explicit or default pagination to a query.

    Returns the query.  When a default limit is injected, a one-line note is
    written to stderr unless ``--quiet`` is set.
    """
    limit = getattr(args, "limit", None)
    offset = getattr(args, "offset", None)
    no_limit = getattr(args, "no_limit", False)
    page = getattr(args, "page", None)
    page_size = getattr(args, "page_size", None)

    if limit is not None and limit < 0:
        raise CLIError("--limit must be greater than or equal to 0")
    if offset is not None and offset < 0:
        raise CLIError("--offset must be greater than or equal to 0")

    if page is not None or page_size is not None:
        if page is None or page_size is None:
            raise CLIError("--page and --page-size must be used together")
        if limit is not None or offset is not None:
            raise CLIError("Use --page/--page-size or --limit/--offset, not both")
        if page < 1 or page_size < 1:
            raise CLIError("--page and --page-size must be positive")
        query = query.limit(page_size)
        query = query.offset((page - 1) * page_size)
        return query

    if limit is not None and limit > 0:
        query = query.limit(limit)
    if offset is not None and offset > 0:
        query = query.offset(offset)

    if no_limit or limit is not None:
        return query
    if not default:
        return query
    if _has_limit(query):
        return query

    query = query.limit(DEFAULT_LIST_LIMIT)
    if not getattr(args, "quiet", False):
        print(
            f"Showing first {DEFAULT_LIST_LIMIT} {label} (default pagination); "
            "use --limit N or --no-limit to change.",
            file=sys.stderr,
        )
    return query


def soft_delete_action(model) -> str:
    """Return ``soft_delete`` or ``delete`` for this model."""
    if issubclass(model, IDeleteBehavior):
        return "soft_delete"
    return "delete"


def soft_delete_field(model) -> Optional[str]:
    """Return the declared soft-delete field name, if any."""
    reader = getattr(model, "deleted_at_field", None)
    if not callable(reader):
        return None
    return reader()


def ensure_writable(model, operation: str) -> None:
    """Refuse a DML operation when the model declares itself read-only.

    Reads the *value* returned by ``read_only()``; membership in
    ``IReadOnlyBehavior`` only says a method exists, not that it is true.
    """
    read_only = getattr(model, "read_only", None)
    if callable(read_only) and read_only():
        raise ReadOnlyModelError(model.__name__, operation)


def confirm(prompt: str, args) -> None:
    """Confirm a destructive action, or fail with the dedicated exit code."""
    if getattr(args, "yes", False):
        return
    if not is_tty() or not getattr(sys.stdin, "isatty", lambda: False)():
        raise ConfirmationRequiredError(
            f"{prompt} Pass --yes to confirm in a non-interactive context."
        )
    answer = input(f"{prompt} [y/N] ")
    if answer.strip().lower() not in ("y", "yes"):
        raise CancelledError()
