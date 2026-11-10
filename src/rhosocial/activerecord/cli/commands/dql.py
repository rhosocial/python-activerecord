# src/rhosocial/activerecord/cli/commands/dql.py
"""DQL command handlers: ActiveQuery reads and user-defined query execution."""


from ...backend.expression import Column
from ...backend.expression import functions
from ..errors import CLIError, NotFoundError
from ..interaction import apply_pagination
from ..output import render_list, render_record, render_scalar
from ..runtime import (
    ACTIVE_QUERY_TYPES,
    ASYNC_ACTIVE_QUERY_TYPES,
    apply_filters,
    base_query,
    context_fields,
    parse_pk,
    resolve_query_reference,
    resolve_query_reference_async,
    validate_query,
)


def _query(ctx):
    return apply_filters(base_query(ctx.model, ctx.args), ctx.model, ctx.args)


def _list_sync(ctx):
    query = apply_pagination(_query(ctx), ctx.args, label="rows")
    records = query.all()
    render_list(
        records, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii, ctx.args.no_header
    )
    return 0


async def _list_async(ctx):
    query = apply_pagination(_query(ctx), ctx.args, label="rows")
    records = await query.all()
    render_list(
        records, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii, ctx.args.no_header
    )
    return 0


def _get_sync(ctx):
    pk = parse_pk(ctx.model, ctx.args)
    record = ctx.model.find_one(pk)
    if record is None:
        raise NotFoundError(f"{ctx.model.__name__} with pk={pk!r} was not found")
    render_record(record, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    return 0


async def _get_async(ctx):
    pk = parse_pk(ctx.model, ctx.args)
    record = await ctx.model.find_one(pk)
    if record is None:
        raise NotFoundError(f"{ctx.model.__name__} with pk={pk!r} was not found")
    render_record(record, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    return 0


def _count_sync(ctx):
    count = _query(ctx).count()
    render_scalar(count, ctx.output)
    return 0


async def _count_async(ctx):
    count = await _query(ctx).count()
    render_scalar(count, ctx.output)
    return 0


def _exists_sync(ctx):
    exists = _query(ctx).exists()
    render_scalar(exists, ctx.output)
    return 0


async def _exists_async(ctx):
    exists = await _query(ctx).exists()
    render_scalar(exists, ctx.output)
    return 0


def _aggregate_expression(ctx, field):
    dialect = ctx.model.backend().dialect
    fn = ctx.args.fn
    if field == "*":
        if fn != "count":
            raise CLIError(f"--fn {fn} requires a concrete --field, not *")
        return functions.count(dialect, "*", is_distinct=ctx.args.distinct, alias="value")
    column = Column(dialect, ctx.model.column_name(field))
    if fn == "count":
        return functions.count(
            dialect, column, is_distinct=ctx.args.distinct, alias="value"
        )
    if fn == "sum":
        return functions.sum_(
            dialect, column, is_distinct=ctx.args.distinct, alias="value"
        )
    if fn == "avg":
        return functions.avg(
            dialect, column, is_distinct=ctx.args.distinct, alias="value"
        )
    if fn == "min":
        return functions.min_(dialect, column, is_distinct=ctx.args.distinct, alias="value")
    if fn == "max":
        return functions.max_(dialect, column, is_distinct=ctx.args.distinct, alias="value")
    raise CLIError(f"Unsupported aggregate function: {fn}")


def _aggregate_query(ctx):
    query = _query(ctx)
    group_by = ctx.args.group_by or []
    if not group_by:
        return None, query
    for field in group_by:
        if field not in ctx.model.model_fields:
            raise CLIError(
                f'Unknown --group-by field "{field}". '
                f"Available fields: {', '.join(ctx.model.model_fields)}"
            )
    dialect = ctx.model.backend().dialect
    group_columns = [Column(dialect, ctx.model.column_name(field)) for field in group_by]
    query = query.group_by(*group_columns)
    query = query.select(
        *group_columns, _aggregate_expression(ctx, ctx.args.field)
    )
    return group_columns, query


def _scalar_aggregate(ctx, query):
    if ctx.args.field == "*":
        if ctx.args.fn != "count":
            raise CLIError(f"--fn {ctx.args.fn} requires a concrete --field, not *")
        value = query.count(is_distinct=ctx.args.distinct)
    elif ctx.args.fn == "count":
        value = query.count(ctx.args.field, is_distinct=ctx.args.distinct)
    elif ctx.args.fn == "sum":
        value = query.sum_(ctx.args.field, is_distinct=ctx.args.distinct)
    elif ctx.args.fn == "avg":
        value = query.avg(ctx.args.field, is_distinct=ctx.args.distinct)
    elif ctx.args.fn == "min":
        value = query.min_(ctx.args.field)
    elif ctx.args.fn == "max":
        value = query.max_(ctx.args.field)
    else:
        raise CLIError(f"Unsupported aggregate function: {ctx.args.fn}")
    render_scalar(value, ctx.output)
    return value


async def _scalar_aggregate_async(ctx, query):
    if ctx.args.field == "*":
        if ctx.args.fn != "count":
            raise CLIError(f"--fn {ctx.args.fn} requires a concrete --field, not *")
        value = await query.count(is_distinct=ctx.args.distinct)
    elif ctx.args.fn == "count":
        value = await query.count(ctx.args.field, is_distinct=ctx.args.distinct)
    elif ctx.args.fn == "sum":
        value = await query.sum_(ctx.args.field, is_distinct=ctx.args.distinct)
    elif ctx.args.fn == "avg":
        value = await query.avg(ctx.args.field, is_distinct=ctx.args.distinct)
    elif ctx.args.fn == "min":
        value = await query.min_(ctx.args.field)
    elif ctx.args.fn == "max":
        value = await query.max_(ctx.args.field)
    else:
        raise CLIError(f"Unsupported aggregate function: {ctx.args.fn}")
    render_scalar(value, ctx.output)
    return value


def _aggregate_sync(ctx):
    group_columns, query = _aggregate_query(ctx)
    if group_columns is None:
        _scalar_aggregate(ctx, apply_filters(base_query(ctx.model, ctx.args), ctx.model, ctx.args))
        return 0
    query = apply_pagination(query, ctx.args, label="groups")
    rows = query.aggregate()
    fields = context_fields(None, ctx.args, rows)
    render_list(rows, None, fields, ctx.output, ctx.rich_ascii, ctx.args.no_header)
    return 0


async def _aggregate_async(ctx):
    group_columns, query = _aggregate_query(ctx)
    if group_columns is None:
        await _scalar_aggregate_async(
            ctx, apply_filters(base_query(ctx.model, ctx.args), ctx.model, ctx.args)
        )
        return 0
    query = apply_pagination(query, ctx.args, label="groups")
    rows = await query.aggregate()
    fields = context_fields(None, ctx.args, rows)
    render_list(rows, None, fields, ctx.output, ctx.rich_ascii, ctx.args.no_header)
    return 0


def _run_query_sync(ctx, reference):
    query = resolve_query_reference(reference, "query")
    validate_query(
        query, ACTIVE_QUERY_TYPES, ASYNC_ACTIVE_QUERY_TYPES,
        is_async=False, label="--query",
    )
    mode = ctx.args.mode
    if mode in ("list", "aggregate"):
        query = apply_pagination(query, ctx.args, label="rows")
    if mode == "list":
        records = query.all()
        render_list(
            records, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii, ctx.args.no_header
        )
    elif mode == "one":
        record = query.one()
        if record is None:
            raise NotFoundError("Query returned no record")
        render_record(record, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    elif mode == "count":
        render_scalar(query.count(), ctx.output)
    elif mode == "exists":
        render_scalar(query.exists(), ctx.output)
    else:
        rows = query.aggregate()
        fields = context_fields(None, ctx.args, rows)
        render_list(rows, None, fields, ctx.output, ctx.rich_ascii, ctx.args.no_header)
    return 0


async def _run_query_async(ctx, reference):
    query = await resolve_query_reference_async(reference, "query")
    validate_query(
        query, ACTIVE_QUERY_TYPES, ASYNC_ACTIVE_QUERY_TYPES,
        is_async=True, label="--query",
    )
    mode = ctx.args.mode
    if mode in ("list", "aggregate"):
        query = apply_pagination(query, ctx.args, label="rows")
    if mode == "list":
        records = await query.all()
        render_list(
            records, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii, ctx.args.no_header
        )
    elif mode == "one":
        record = await query.one()
        if record is None:
            raise NotFoundError("Query returned no record")
        render_record(record, ctx.model, ctx.fields, ctx.output, ctx.rich_ascii)
    elif mode == "count":
        render_scalar(await query.count(), ctx.output)
    elif mode == "exists":
        render_scalar(await query.exists(), ctx.output)
    else:
        rows = await query.aggregate()
        fields = context_fields(None, ctx.args, rows)
        render_list(rows, None, fields, ctx.output, ctx.rich_ascii, ctx.args.no_header)
    return 0


def _run_sync(ctx):
    return _run_query_sync(ctx, ctx.args.query)


async def _run_async(ctx):
    return await _run_query_async(ctx, ctx.args.query)


SYNC_HANDLERS = {
    "get": _get_sync,
    "list": _list_sync,
    "count": _count_sync,
    "exists": _exists_sync,
    "aggregate": _aggregate_sync,
    "run": _run_sync,
}

ASYNC_HANDLERS = {
    "get": _get_async,
    "list": _list_async,
    "count": _count_async,
    "exists": _exists_async,
    "aggregate": _aggregate_async,
    "run": _run_async,
}
