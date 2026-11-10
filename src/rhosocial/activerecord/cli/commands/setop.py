# src/rhosocial/activerecord/cli/commands/setop.py
"""SetOperation command handlers."""


from ...query import AsyncSetOperationQuery, SetOperationQuery
from ..interaction import apply_pagination
from ..output import render_list
from ..runtime import (
    ASYNC_SET_QUERY_TYPES,
    SET_QUERY_TYPES,
    apply_filters,
    base_query,
    context_fields,
    resolve_query_reference,
    resolve_query_reference_async,
    validate_query,
)

_OPERATIONS = {
    "union": "UNION",
    "union-all": "UNION ALL",
    "intersect": "INTERSECT",
    "except": "EXCEPT",
}


def _arm_query(model, args, where):
    query = base_query(model, args)
    if where:
        from ..runtime import parse_where

        for predicate in parse_where(model, where):
            query = query.where(predicate)
    query = apply_filters(query, model, args)
    return apply_pagination(query, args, default=False)


def _render_rows(rows, ctx):
    fields = context_fields(None, ctx.args, rows)
    render_list(rows, None, fields, ctx.output, ctx.rich_ascii, ctx.args.no_header)


def _simple_sync(ctx, left_model, right_model, operation):
    left = _arm_query(left_model, ctx.args, ctx.args.left_where)
    right = _arm_query(right_model, ctx.args, ctx.args.right_where)
    op = _OPERATIONS[operation]
    if op == "UNION":
        combined = left.union(right)
    elif op == "INTERSECT":
        combined = left.intersect(right)
    elif op == "EXCEPT":
        combined = left.except_(right)
    else:
        combined = SetOperationQuery(left, right, "UNION ALL")
    rows = combined.aggregate()
    _render_rows(rows, ctx)
    return 0


async def _simple_async(ctx, left_model, right_model, operation):
    left = _arm_query(left_model, ctx.args, ctx.args.left_where)
    right = _arm_query(right_model, ctx.args, ctx.args.right_where)
    op = _OPERATIONS[operation]
    if op == "UNION":
        combined = left.union(right)
    elif op == "INTERSECT":
        combined = left.intersect(right)
    elif op == "EXCEPT":
        combined = left.except_(right)
    else:
        combined = AsyncSetOperationQuery(left, right, "UNION ALL")
    rows = await combined.aggregate()
    _render_rows(rows, ctx)
    return 0


def _run_sync(ctx):
    query = resolve_query_reference(ctx.args.query, "set query")
    validate_query(
        query, SET_QUERY_TYPES, ASYNC_SET_QUERY_TYPES, is_async=False, label="--query"
    )
    rows = query.aggregate()
    _render_rows(rows, ctx)
    return 0


async def _run_async(ctx):
    query = await resolve_query_reference_async(ctx.args.query, "set query")
    validate_query(
        query, SET_QUERY_TYPES, ASYNC_SET_QUERY_TYPES, is_async=True, label="--query"
    )
    rows = await query.aggregate()
    _render_rows(rows, ctx)
    return 0


def execute_sync(ctx, left_model=None, right_model=None) -> int:
    operation = getattr(ctx.args, "set_operation", None)
    if operation in _OPERATIONS:
        return _simple_sync(ctx, left_model, right_model, operation)
    return _run_sync(ctx)


async def execute_async(ctx, left_model=None, right_model=None) -> int:
    operation = getattr(ctx.args, "set_operation", None)
    if operation in _OPERATIONS:
        return await _simple_async(ctx, left_model, right_model, operation)
    return await _run_async(ctx)


def execute_auto(ctx) -> int:
    """Execute ``set run`` when no model/backend is configured up front."""
    import asyncio

    query = resolve_query_reference(ctx.args.query, "set query")
    is_async = validate_query(
        query, SET_QUERY_TYPES, ASYNC_SET_QUERY_TYPES, label="--query"
    )
    if is_async:
        return asyncio.run(_render_async(query, ctx))
    rows = query.aggregate()
    _render_rows(rows, ctx)
    return 0


async def _render_async(query, ctx):
    rows = await query.aggregate()
    _render_rows(rows, ctx)
    return 0
