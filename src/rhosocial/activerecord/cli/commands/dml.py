# src/rhosocial/activerecord/cli/commands/dml.py
"""DML command handlers: single-record and bulk ActiveRecord operations."""

from typing import Any, Dict, List

from pydantic import ValidationError

from ..errors import CLIError, NotFoundError
from ..input import check_fields, convert_field, read_object, read_records, read_values
from ..interaction import confirm, ensure_writable, soft_delete_action, soft_delete_field
from ..output import render_affected, render_delete, render_list, render_record
from ..runtime import parse_pk, parse_pk_mapping


def _read_record_data(args) -> Dict[str, Any]:
    return read_object(args.data)


def _make_record(model, data: Dict[str, Any]):
    check_fields(model, data)
    try:
        return model(**data)
    except ValidationError as exc:
        raise CLIError(f"Invalid data for {model.__name__}: {exc}") from None


def _update_values(model, data: Dict[str, Any]) -> Dict[str, Any]:
    pk_fields = set(model.primary_key_fields())
    present_pk = [field for field in data if field in pk_fields]
    if present_pk:
        raise CLIError(
            "Cannot update primary key field(s) "
            f"{', '.join(present_pk)}; delete and create a new record instead"
        )
    check_fields(model, data)
    return {name: convert_field(model, name, value) for name, value in data.items()}


def _load_sync(model, pk):
    return model.find_one(pk)


async def _load_async(model, pk):
    return await model.find_one(pk)


def _not_found(model, pk):
    return NotFoundError(f"{model.__name__} with pk={pk!r} was not found")


def _create_sync(ctx):
    ensure_writable(ctx.model, "dml create")
    record = _make_record(ctx.model, _read_record_data(ctx.args))
    record.save()
    render_record(record, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    return 0


async def _create_async(ctx):
    ensure_writable(ctx.model, "dml create")
    record = _make_record(ctx.model, _read_record_data(ctx.args))
    await record.save()
    render_record(record, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    return 0


def _update_sync(ctx):
    ensure_writable(ctx.model, "dml update")
    pk = parse_pk(ctx.model, ctx.args)
    record = _load_sync(ctx.model, pk)
    if record is None:
        raise _not_found(ctx.model, pk)
    for name, value in _update_values(ctx.model, _read_record_data(ctx.args)).items():
        setattr(record, name, value)
    record.save()
    render_record(record, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    return 0


async def _update_async(ctx):
    ensure_writable(ctx.model, "dml update")
    pk = parse_pk(ctx.model, ctx.args)
    record = await _load_async(ctx.model, pk)
    if record is None:
        raise _not_found(ctx.model, pk)
    for name, value in _update_values(ctx.model, _read_record_data(ctx.args)).items():
        setattr(record, name, value)
    await record.save()
    render_record(record, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    return 0


def _delete_sync(ctx):
    ensure_writable(ctx.model, "dml delete")
    pk = parse_pk(ctx.model, ctx.args)
    record = _load_sync(ctx.model, pk)
    if record is None:
        raise _not_found(ctx.model, pk)
    action = soft_delete_action(ctx.model)
    field_name = soft_delete_field(ctx.model)
    if ctx.args.dry_run:
        render_delete(pk, 1, ctx.model, ctx.output, ctx.rich_ascii, action, field_name, True)
        return 0
    confirm(
        f"Delete {ctx.model.__name__} pk={pk!r} ({action})?", ctx.args
    )
    affected = record.delete()
    render_delete(pk, affected, ctx.model, ctx.output, ctx.rich_ascii, action, field_name)
    return 0


async def _delete_async(ctx):
    ensure_writable(ctx.model, "dml delete")
    pk = parse_pk(ctx.model, ctx.args)
    record = await _load_async(ctx.model, pk)
    if record is None:
        raise _not_found(ctx.model, pk)
    action = soft_delete_action(ctx.model)
    field_name = soft_delete_field(ctx.model)
    if ctx.args.dry_run:
        render_delete(pk, 1, ctx.model, ctx.output, ctx.rich_ascii, action, field_name, True)
        return 0
    confirm(
        f"Delete {ctx.model.__name__} pk={pk!r} ({action})?", ctx.args
    )
    affected = await record.delete()
    render_delete(pk, affected, ctx.model, ctx.output, ctx.rich_ascii, action, field_name)
    return 0


def _bulk_records(ctx) -> List[Dict[str, Any]]:
    return read_records(ctx.args.data, ctx.args.input_format)


def _bulk_create_sync(ctx):
    ensure_writable(ctx.model, "dml bulk create")
    records = [_make_record(ctx.model, data) for data in _bulk_records(ctx)]
    if ctx.args.dry_run:
        render_affected("create", len(records), ctx.output, dry_run=True)
        return 0
    result = ctx.model.bulk_create(records, batch_size=ctx.args.batch_size)
    render_list(result, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    return 0


async def _bulk_create_async(ctx):
    ensure_writable(ctx.model, "dml bulk create")
    records = [_make_record(ctx.model, data) for data in _bulk_records(ctx)]
    if ctx.args.dry_run:
        render_affected("create", len(records), ctx.output, dry_run=True)
        return 0
    result = await ctx.model.bulk_create(records, batch_size=ctx.args.batch_size)
    render_list(result, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    return 0


def _bulk_update_parts(model, data):
    """Return ``(pk, values)`` for one bulk-update object."""
    pk_fields = set(model.primary_key_fields())
    pk = parse_pk_mapping(model, data)
    values = {name: value for name, value in data.items() if name not in pk_fields}
    return pk, values


def _select_update_fields(ctx, parts) -> List[str]:
    explicit = getattr(ctx.args, "update_fields", None)
    if explicit:
        names = [part.strip() for part in explicit.split(",") if part.strip()]
        if not names:
            raise CLIError("--update-fields must name at least one field")
    else:
        sets = [set(values) for _, values in parts]
        if not sets or not sets[0]:
            raise CLIError("Bulk update needs at least one non-primary-key field")
        if any(field_set != sets[0] for field_set in sets[1:]):
            raise CLIError(
                "Bulk update objects must all contain the same fields; "
                "pass --update-fields to choose them explicitly"
            )
        names = list(sets[0])
    for index, (_, values) in enumerate(parts):
        missing = [name for name in names if name not in values]
        if missing:
            raise CLIError(
                f"bulk update item {index + 1} is missing field(s): {', '.join(missing)}"
            )
    return names


def _bulk_update_sync(ctx):
    ensure_writable(ctx.model, "dml bulk update")
    parts = [_bulk_update_parts(ctx.model, data) for data in _bulk_records(ctx)]
    names = _select_update_fields(ctx, parts)
    records = []
    for index, (pk, values) in enumerate(parts):
        record = _load_sync(ctx.model, pk)
        if record is None:
            raise NotFoundError(
                f"{ctx.model.__name__} bulk update item {index + 1} with pk={pk!r} "
                "was not found"
            )
        for name in names:
            setattr(record, name, convert_field(ctx.model, name, values[name]))
        records.append(record)
    if ctx.args.dry_run:
        render_affected("update", len(records), ctx.output, dry_run=True)
        return 0
    affected = ctx.model.bulk_update(
        records, names, batch_size=ctx.args.batch_size
    )
    render_affected("update", affected, ctx.output)
    return 0


async def _bulk_update_async(ctx):
    ensure_writable(ctx.model, "dml bulk update")
    parts = [_bulk_update_parts(ctx.model, data) for data in _bulk_records(ctx)]
    names = _select_update_fields(ctx, parts)
    records = []
    for index, (pk, values) in enumerate(parts):
        record = await _load_async(ctx.model, pk)
        if record is None:
            raise NotFoundError(
                f"{ctx.model.__name__} bulk update item {index + 1} with pk={pk!r} "
                "was not found"
            )
        for name in names:
            setattr(record, name, convert_field(ctx.model, name, values[name]))
        records.append(record)
    if ctx.args.dry_run:
        render_affected("update", len(records), ctx.output, dry_run=True)
        return 0
    affected = await ctx.model.bulk_update(
        records, names, batch_size=ctx.args.batch_size
    )
    render_affected("update", affected, ctx.output)
    return 0


def _bulk_delete_values(model, values):
    pks = []
    for index, value in enumerate(values):
        if isinstance(value, dict):
            pks.append(parse_pk_mapping(model, value, f"bulk delete item {index + 1}"))
        elif model.is_composite_pk():
            raise CLIError(
                f"Bulk delete item {index + 1} must be an object for composite primary key"
            )
        else:
            pks.append(parse_pk(model, _PkArgs(value)))
    return pks


class _PkArgs:
    def __init__(self, value):
        self.pk = value
        self.pk_json = None


def _bulk_delete_sync(ctx):
    ensure_writable(ctx.model, "dml bulk delete")
    pks = _bulk_delete_values(ctx.model, read_values(ctx.args.data, ctx.args.input_format))
    records = []
    for index, pk in enumerate(pks):
        record = _load_sync(ctx.model, pk)
        if record is None:
            raise NotFoundError(
                f"{ctx.model.__name__} bulk delete item {index + 1} with pk={pk!r} "
                "was not found"
            )
        records.append(record)
    action = soft_delete_action(ctx.model)
    if ctx.args.dry_run:
        render_affected(action, len(records), ctx.output, dry_run=True)
        return 0
    confirm(f"Delete {len(records)} {ctx.model.__name__} records ({action})?", ctx.args)
    affected = ctx.model.bulk_delete(records)
    render_affected(action, affected, ctx.output)
    return 0


async def _bulk_delete_async(ctx):
    ensure_writable(ctx.model, "dml bulk delete")
    pks = _bulk_delete_values(ctx.model, read_values(ctx.args.data, ctx.args.input_format))
    records = []
    for index, pk in enumerate(pks):
        record = await _load_async(ctx.model, pk)
        if record is None:
            raise NotFoundError(
                f"{ctx.model.__name__} bulk delete item {index + 1} with pk={pk!r} "
                "was not found"
            )
        records.append(record)
    action = soft_delete_action(ctx.model)
    if ctx.args.dry_run:
        render_affected(action, len(records), ctx.output, dry_run=True)
        return 0
    confirm(f"Delete {len(records)} {ctx.model.__name__} records ({action})?", ctx.args)
    affected = await ctx.model.bulk_delete(records)
    render_affected(action, affected, ctx.output)
    return 0


SYNC_HANDLERS = {
    "create": _create_sync,
    "update": _update_sync,
    "delete": _delete_sync,
    "bulk_create": _bulk_create_sync,
    "bulk_update": _bulk_update_sync,
    "bulk_delete": _bulk_delete_sync,
}

ASYNC_HANDLERS = {
    "create": _create_async,
    "update": _update_async,
    "delete": _delete_async,
    "bulk_create": _bulk_create_async,
    "bulk_update": _bulk_update_async,
    "bulk_delete": _bulk_delete_async,
}
