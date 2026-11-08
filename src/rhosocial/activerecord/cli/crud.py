# src/rhosocial/activerecord/cli/crud.py
"""CRUD handlers for the ActiveRecord model CLI."""

import json
import sys
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter, ValidationError

from ..backend.expression import Column, ComparisonPredicate, Literal
from .errors import CLIError, NotFoundError
from .output import selected_fields, render_delete, render_list, render_record


def _read_data(argument: str) -> Dict[str, Any]:
    """Read ``--data`` as inline JSON, ``@file``, or ``@-`` stdin."""
    if argument == "@-":
        text = sys.stdin.read()
    elif argument.startswith("@"):
        filename = argument[1:]
        try:
            with open(filename, encoding="utf-8") as handle:
                text = handle.read()
        except OSError as exc:
            raise CLIError(f'Cannot read --data file "{filename}": {exc}') from None
    else:
        text = argument
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CLIError(f"--data is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise CLIError("--data must be a JSON object")
    return data


def _field_adapter(model, field_name: str):
    return TypeAdapter(model.model_fields[field_name].annotation)


def _convert_known_field(model, field_name: str, value: Any) -> Any:
    return _field_adapter(model, field_name).validate_python(value)


def _coerce_pk_value(model, field_name: str, value: Any) -> Any:
    try:
        return _convert_known_field(model, field_name, value)
    except ValidationError as exc:
        raise CLIError(f"Invalid primary key value for {field_name}: {exc}") from None


def _coerce_filter_value(model, field_name: str, value: Any) -> Any:
    try:
        return _convert_known_field(model, field_name, value)
    except ValidationError:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return value
            try:
                return _convert_known_field(model, field_name, parsed)
            except ValidationError:
                return value
        return value


def _check_fields(model, data: Dict[str, Any]) -> None:
    unknown = [key for key in data if key not in model.model_fields]
    if unknown:
        raise CLIError(
            f"Unknown field(s) for {model.__name__}: {', '.join(unknown)}. "
            f"Available fields: {', '.join(model.model_fields)}"
        )


def _parse_pk(model, args):
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
            field: _coerce_pk_value(model, field, parsed[field]) for field in pk_fields
        }
        if len(pk_fields) == 1:
            return converted[pk_fields[0]]
        return converted

    if model.is_composite_pk():
        raise CLIError(
            f"{model.__name__} has a composite primary key; pass --pk as a JSON object "
            f"with keys {', '.join(pk_fields)}"
        )
    return _coerce_pk_value(model, pk_fields[0], value)


def _parse_where(model, clauses: Optional[List[str]]):
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
        value = _coerce_filter_value(model, field_name, raw_value.strip())
        column = Column(dialect, model.column_name(field_name))
        predicates.append(ComparisonPredicate(dialect, "=", column, Literal(dialect, value)))
    return predicates


def _parse_order_by(model, clauses: Optional[List[str]]):
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


def _list_query(model, args):
    query = model.query()
    for predicate in _parse_where(model, getattr(args, "where", None)):
        query = query.where(predicate)
    order_clauses = _parse_order_by(model, getattr(args, "order_by", None))
    if order_clauses:
        query = query.order_by(*order_clauses)
    limit = getattr(args, "limit", None)
    if limit is not None and limit > 0:
        query = query.limit(limit)
    offset = getattr(args, "offset", None)
    if offset is not None and offset > 0:
        query = query.offset(offset)
    return query


def _load_record_sync(model, pk):
    return model.find_one(pk)


async def _load_record_async(model, pk):
    return await model.find_one(pk)


def _fields_for(model, args):
    return selected_fields(model, getattr(args, "fields", None))


def _run_get_sync(ctx):
    pk = _parse_pk(ctx.model, ctx.args)
    record = _load_record_sync(ctx.model, pk)
    if record is None:
        raise NotFoundError(f"{ctx.model.__name__} with pk={pk!r} was not found")
    render_record(record, ctx.model, ctx.fields, ctx.args.output, ctx.args.rich_ascii)
    return 0


async def _run_get_async(ctx):
    pk = _parse_pk(ctx.model, ctx.args)
    record = await _load_record_async(ctx.model, pk)
    if record is None:
        raise NotFoundError(f"{ctx.model.__name__} with pk={pk!r} was not found")
    render_record(record, ctx.model, ctx.fields, ctx.args.output, ctx.args.rich_ascii)
    return 0


def _run_list_sync(ctx):
    records = _list_query(ctx.model, ctx.args).all()
    render_list(records, ctx.model, ctx.fields, ctx.args.output, ctx.args.rich_ascii)
    return 0


async def _run_list_async(ctx):
    records = await _list_query(ctx.model, ctx.args).all()
    render_list(records, ctx.model, ctx.fields, ctx.args.output, ctx.args.rich_ascii)
    return 0


def _run_create_sync(ctx):
    data = _read_data(ctx.args.data)
    _check_fields(ctx.model, data)
    record = ctx.model(**data)
    record.save()
    render_record(record, ctx.model, ctx.fields, ctx.args.output, ctx.args.rich_ascii)
    return 0


async def _run_create_async(ctx):
    data = _read_data(ctx.args.data)
    _check_fields(ctx.model, data)
    record = ctx.model(**data)
    await record.save()
    render_record(record, ctx.model, ctx.fields, ctx.args.output, ctx.args.rich_ascii)
    return 0


def _update_values(model, data):
    pk_fields = set(model.primary_key_fields())
    present_pk = [field for field in data if field in pk_fields]
    if present_pk:
        raise CLIError(
            "Cannot update primary key field(s) "
            f"{', '.join(present_pk)}; delete and create a new record instead"
        )
    _check_fields(model, data)
    values = {}
    for field_name, value in data.items():
        try:
            values[field_name] = _convert_known_field(model, field_name, value)
        except ValidationError as exc:
            raise CLIError(f"Invalid value for {field_name}: {exc}") from None
    return values


def _run_update_sync(ctx):
    pk = _parse_pk(ctx.model, ctx.args)
    record = _load_record_sync(ctx.model, pk)
    if record is None:
        raise NotFoundError(f"{ctx.model.__name__} with pk={pk!r} was not found")
    values = _update_values(ctx.model, _read_data(ctx.args.data))
    for field_name, value in values.items():
        setattr(record, field_name, value)
    record.save()
    render_record(record, ctx.model, ctx.fields, ctx.args.output, ctx.args.rich_ascii)
    return 0


async def _run_update_async(ctx):
    pk = _parse_pk(ctx.model, ctx.args)
    record = await _load_record_async(ctx.model, pk)
    if record is None:
        raise NotFoundError(f"{ctx.model.__name__} with pk={pk!r} was not found")
    values = _update_values(ctx.model, _read_data(ctx.args.data))
    for field_name, value in values.items():
        setattr(record, field_name, value)
    await record.save()
    render_record(record, ctx.model, ctx.fields, ctx.args.output, ctx.args.rich_ascii)
    return 0


def _run_delete_sync(ctx):
    pk = _parse_pk(ctx.model, ctx.args)
    record = _load_record_sync(ctx.model, pk)
    if record is None:
        raise NotFoundError(f"{ctx.model.__name__} with pk={pk!r} was not found")
    affected = record.delete()
    render_delete(pk, affected, ctx.model, ctx.args.output, ctx.args.rich_ascii)
    return 0


async def _run_delete_async(ctx):
    pk = _parse_pk(ctx.model, ctx.args)
    record = await _load_record_async(ctx.model, pk)
    if record is None:
        raise NotFoundError(f"{ctx.model.__name__} with pk={pk!r} was not found")
    affected = await record.delete()
    render_delete(pk, affected, ctx.model, ctx.args.output, ctx.args.rich_ascii)
    return 0


_SYNC_HANDLERS = {
    "get": _run_get_sync,
    "list": _run_list_sync,
    "create": _run_create_sync,
    "update": _run_update_sync,
    "delete": _run_delete_sync,
}

_ASYNC_HANDLERS = {
    "get": _run_get_async,
    "list": _run_list_async,
    "create": _run_create_async,
    "update": _run_update_async,
    "delete": _run_delete_async,
}


class CommandContext:
    """Everything a CRUD handler needs for one invocation."""

    def __init__(self, args, model, is_async: bool):
        self.args = args
        self.model = model
        self.is_async = is_async
        self.fields = _fields_for(model, args)


def execute_sync(args, model) -> int:
    """Dispatch one ``crud`` command for a synchronous model."""
    return _execute_sync(CommandContext(args, model, False))


async def execute_async(args, model) -> int:
    """Dispatch one ``crud`` command for an asynchronous model."""
    return await _execute_async(CommandContext(args, model, True))


def _execute_sync(context: CommandContext) -> int:
    handler = _SYNC_HANDLERS[context.args.command]
    return handler(context)


async def _execute_async(context: CommandContext) -> int:
    handler = _ASYNC_HANDLERS[context.args.command]
    return await handler(context)
