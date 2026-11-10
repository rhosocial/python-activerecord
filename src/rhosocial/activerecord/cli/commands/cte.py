# src/rhosocial/activerecord/cli/commands/cte.py
"""CTE command handlers."""

from ..output import render_list
from ..runtime import (
    ASYNC_CTE_QUERY_TYPES,
    CTE_QUERY_TYPES,
    context_fields,
    resolve_query_reference,
    resolve_query_reference_async,
    validate_query,
)


def _render_rows(rows, ctx):
    fields = context_fields(None, ctx.args, rows)
    render_list(rows, None, fields, ctx.output, ctx.rich_ascii, ctx.args.no_header)


def _run_sync(ctx):
    query = resolve_query_reference(ctx.args.query, "cte query")
    validate_query(
        query, CTE_QUERY_TYPES, ASYNC_CTE_QUERY_TYPES, is_async=False, label="--query"
    )
    rows = query.aggregate()
    _render_rows(rows, ctx)
    return 0


async def _run_async(ctx):
    query = await resolve_query_reference_async(ctx.args.query, "cte query")
    validate_query(
        query, CTE_QUERY_TYPES, ASYNC_CTE_QUERY_TYPES, is_async=True, label="--query"
    )
    rows = await query.aggregate()
    _render_rows(rows, ctx)
    return 0


def execute_sync(ctx) -> int:
    return _run_sync(ctx)


async def execute_async(ctx) -> int:
    return await _run_async(ctx)


def execute_auto(ctx) -> int:
    """Execute ``cte run`` when no model/backend is configured up front."""
    import asyncio

    query = resolve_query_reference(ctx.args.query, "cte query")
    is_async = validate_query(
        query, CTE_QUERY_TYPES, ASYNC_CTE_QUERY_TYPES, label="--query"
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
