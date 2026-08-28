# src/rhosocial/activerecord/backend/impl/sqlite/cli/named_migration.py
"""named-migration subcommand — SQLite adapter for the shared CLI helper."""

from __future__ import annotations

from .connection import create_connection_parent_parser, resolve_connection_config_from_args
from .output import create_provider


def create_parser(subparsers):
    """Create the named-migration subcommand parser.

    Provides connection and output arguments via a parent parser.
    """
    from rhosocial.activerecord.backend.migration.cli import create_named_migration_parser

    local_parent = create_connection_parent_parser()
    return create_named_migration_parser(subparsers, local_parent)


def handle(args):
    """Handle the named-migration subcommand."""
    from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
    from rhosocial.activerecord.backend.migration.cli import handle_named_migration as handle_nm

    provider = create_provider(args.output, ascii_borders=args.rich_ascii)

    backend = None

    def backend_factory():
        nonlocal backend
        config = resolve_connection_config_from_args(args)
        config.check_same_thread = False
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()
        return backend

    def disconnect():
        if backend and getattr(backend, "_connection", None):
            backend.disconnect()

    is_async = getattr(args, "is_async", False)
    if is_async:
        async_backend = None

        def backend_async_factory():
            nonlocal async_backend
            from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

            config = resolve_connection_config_from_args(args)
            config.check_same_thread = False
            async_backend = AsyncSQLiteBackend(connection_config=config)
            return async_backend

        async def disconnect_async(backend=None):
            if backend and getattr(backend, "_connection", None):
                await backend.disconnect()

        handle_nm(
            args,
            provider,
            backend_factory=backend_factory,
            disconnect=disconnect,
            backend_async_factory=backend_async_factory,
            disconnect_async=disconnect_async,
        )
        return

    handle_nm(
        args,
        provider,
        backend_factory=backend_factory,
        disconnect=disconnect,
    )