# src/rhosocial/activerecord/cli/runtime.py
"""Shared runtime helpers: model fields, query construction, and query factories."""

import asyncio
import inspect
import json
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type

from ..backend.expression import Column, ComparisonPredicate, Literal
from ..query import (
    ActiveQuery,
    AsyncActiveQuery,
    AsyncCTEQuery,
    AsyncSetOperationQuery,
    CTEQuery,
    SetOperationQuery,
)
from .backends import import_symbol
from .errors import CLIError
from .input import coerce_filter_value, coerce_pk_value
from .output import selected_fields


def run_coroutine(coro):
    """Run one coroutine, using a selector loop on Windows.

    psycopg (and other async drivers) cannot use Windows' default
    ProactorEventLoop.  The CLI owns its loop, so it must choose a compatible
    one instead of relying on the interpreter default.
    """
    if sys.platform == "win32":
        import selectors

        loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
    return asyncio.run(coro)


def context_fields(model, args, rows=None) -> List[str]:
    """Resolve ``--fields`` against model fields or dict-row keys."""
    fields_argument = getattr(args, "fields", None)
    if model is None and rows is None:
        if fields_argument:
            raise CLIError("--fields requires a model or row data to resolve against")
        return []
    return selected_fields(model, fields_argument, rows)


class RuntimeContext:
    """Everything a command handler needs for one invocation."""

    def __init__(self, args, model, is_async: bool):
        self.args = args
        self.model = model
        self.is_async = is_async
        self.fields = context_fields(model, args)
        from .interaction import resolve_output

        self.output = resolve_output(args)
        self.rich_ascii = bool(getattr(args, "rich_ascii", False))


def parse_pk(model, args):
    """Return a primary-key condition: scalar for one field, dict for several."""
    value = getattr(args, "pk_json", None)
    plain = getattr(args, "pk", None)
    if value is not None and plain is not None:
        raise CLIError("Use --pk or --pk-json, not both")
    if value is None:
        value = plain
    if value is None:
        raise CLIError("A primary key is required: pass --pk or --pk-json")

    pk_fields = list(model.primary_key_fields())
    if not pk_fields:
        raise CLIError(
            f"{model.__name__} has no primary key; use --where with dql list instead"
        )

    parsed = None
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise CLIError(f"--pk is not valid JSON: {exc}") from None

    if isinstance(parsed, dict):
        keys = set(parsed)
        if keys != set(pk_fields):
            raise CLIError(
                f"--pk keys must be exactly the primary key fields "
                f"({', '.join(pk_fields)}); got {', '.join(sorted(keys))}"
            )
        converted = {
            field: coerce_pk_value(model, field, parsed[field]) for field in pk_fields
        }
        if len(pk_fields) == 1:
            return converted[pk_fields[0]]
        return converted

    if model.is_composite_pk():
        raise CLIError(
            f"{model.__name__} has a composite primary key; pass --pk as a JSON object "
            f"with keys {', '.join(pk_fields)}"
        )
    return coerce_pk_value(model, pk_fields[0], value)


def parse_pk_mapping(model, mapping: Dict[str, Any], label: str = "record"):
    """Extract and coerce a primary key from a bulk input object."""
    pk_fields = list(model.primary_key_fields())
    missing = [field for field in pk_fields if field not in mapping]
    if missing:
        raise CLIError(f"{label} is missing primary key field(s): {', '.join(missing)}")
    converted = {
        field: coerce_pk_value(model, field, mapping[field]) for field in pk_fields
    }
    if len(pk_fields) == 1:
        return converted[pk_fields[0]]
    return converted


def parse_where(model, clauses: Optional[Sequence[str]]):
    """Turn ``field=value`` clauses into expression predicates."""
    predicates = []
    dialect = model.backend().dialect
    for clause in clauses or []:
        if "=" not in clause:
            raise CLIError(f'Invalid --where "{clause}": expected field=value')
        field_name, raw_value = clause.split("=", 1)
        field_name = field_name.strip()
        if field_name not in model.model_fields:
            raise CLIError(
                f'Unknown --where field "{field_name}". '
                f"Available fields: {', '.join(model.model_fields)}"
            )
        value = coerce_filter_value(model, field_name, raw_value.strip())
        column = Column(dialect, model.column_name(field_name))
        predicates.append(
            ComparisonPredicate(dialect, "=", column, Literal(dialect, value))
        )
    return predicates


def parse_order_by(model, clauses: Optional[Sequence[str]]):
    """Turn ``field [asc|desc]`` clauses into order_by arguments."""
    clauses_out = []
    dialect = model.backend().dialect
    for clause in clauses or []:
        parts = clause.split()
        if not parts:
            raise CLIError("--order-by cannot be empty")
        field_name = parts[0]
        if field_name not in model.model_fields:
            raise CLIError(
                f'Unknown --order-by field "{field_name}". '
                f"Available fields: {', '.join(model.model_fields)}"
            )
        direction = "ASC"
        if len(parts) > 1:
            if len(parts) > 2 or parts[1].lower() not in ("asc", "desc"):
                raise CLIError(
                    f'Invalid --order-by "{clause}": expected field or field asc|desc'
                )
            direction = parts[1].upper()
        clauses_out.append((Column(dialect, model.column_name(field_name)), direction))
    return clauses_out


def parse_select(model, argument: Optional[str]):
    """Turn ``--select a,b`` into model column expressions."""
    if not argument:
        return None
    names = [part.strip() for part in argument.split(",") if part.strip()]
    if not names:
        raise CLIError("--select must name at least one column")
    unknown = [name for name in names if name not in model.model_fields]
    if unknown:
        raise CLIError(
            f"Unknown --select field(s): {', '.join(unknown)}. "
            f"Available fields: {', '.join(model.model_fields)}"
        )
    dialect = model.backend().dialect
    return [Column(dialect, model.column_name(name)) for name in names]


def base_query(model, args):
    """Return the model's query, honoring soft-delete visibility flags."""
    include_deleted = getattr(args, "include_deleted", False)
    only_deleted = getattr(args, "only_deleted", False)
    if include_deleted and only_deleted:
        raise CLIError("Use --include-deleted or --only-deleted, not both")
    if only_deleted:
        query_method = getattr(model, "query_only_deleted", None)
        if not callable(query_method):
            raise CLIError(f"{model.__name__} has no query_only_deleted() method")
        return query_method()
    if include_deleted:
        query_method = getattr(model, "query_with_deleted", None)
        if not callable(query_method):
            raise CLIError(f"{model.__name__} has no query_with_deleted() method")
        return query_method()
    return model.query()


def apply_filters(query, model, args):
    """Apply the simple ``--where`` / ``--order-by`` / ``--select`` options."""
    for predicate in parse_where(model, getattr(args, "where", None)):
        query = query.where(predicate)
    order_clauses = parse_order_by(model, getattr(args, "order_by", None))
    if order_clauses:
        query = query.order_by(*order_clauses)
    select_columns = parse_select(model, getattr(args, "select", None))
    if select_columns:
        query = query.select(*select_columns)
    return query


def resolve_query_reference(reference: str, label: str = "query") -> Any:
    """Import and call a user query factory without arguments."""
    target = import_symbol(reference, label)
    if not callable(target):
        raise CLIError(
            f'The query reference "{reference}" resolves to {type(target).__name__}; '
            "a callable returning a Query object is required."
        )
    try:
        return target()
    except Exception as exc:
        raise CLIError(f'Query factory "{reference}" failed: {exc}') from None


async def resolve_query_reference_async(reference: str, label: str = "query") -> Any:
    """Like :func:`resolve_query_reference`, but awaits an async factory."""
    result = resolve_query_reference(reference, label)
    if inspect.isawaitable(result):
        result = await result
    return result


def validate_query(
    query: Any,
    sync_types: Tuple[Type, ...],
    async_types: Tuple[Type, ...],
    *,
    is_async: Optional[bool] = None,
    label: str = "query",
) -> bool:
    """Validate a user-supplied query and return whether it is asynchronous."""
    if is_async is True:
        if not isinstance(query, async_types):
            raise CLIError(
                f"{label} returned {type(query).__name__}; expected one of "
                f"{', '.join(cls.__name__ for cls in async_types)}"
            )
        return True
    if is_async is False:
        if not isinstance(query, sync_types):
            raise CLIError(
                f"{label} returned {type(query).__name__}; expected one of "
                f"{', '.join(cls.__name__ for cls in sync_types)}"
            )
        return False
    if isinstance(query, async_types):
        return True
    if isinstance(query, sync_types):
        return False
    expected = tuple(dict.fromkeys(sync_types + async_types))
    raise CLIError(
        f"{label} returned {type(query).__name__}; expected one of "
        f"{', '.join(cls.__name__ for cls in expected)}"
    )


#: Query classes accepted by ``dql run``.
ACTIVE_QUERY_TYPES = (ActiveQuery,)
ASYNC_ACTIVE_QUERY_TYPES = (AsyncActiveQuery,)
#: Query classes accepted by ``set run``.
SET_QUERY_TYPES = (SetOperationQuery,)
ASYNC_SET_QUERY_TYPES = (AsyncSetOperationQuery,)
#: Query classes accepted by ``cte run``.
CTE_QUERY_TYPES = (CTEQuery,)
ASYNC_CTE_QUERY_TYPES = (AsyncCTEQuery,)
