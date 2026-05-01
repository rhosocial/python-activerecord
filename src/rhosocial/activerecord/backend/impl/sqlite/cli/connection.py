# src/rhosocial/activerecord/backend/impl/sqlite/cli/connection.py
"""Connection config resolution and backend factory methods."""

import argparse
import sys
from typing import Callable

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.named_connection import NamedConnectionResolver


def add_connection_args(parser):
    """Add connection-related arguments to a parser.

    Shared by query, introspect, status, named-query, named-procedure.
    Not used by info and named-connection.
    """
    parser.add_argument(
        "--db-file",
        default=None,
        metavar="PATH",
        help="Path to the SQLite database file. This has highest priority and can override "
             "the database specified in a named connection.",
    )
    parser.add_argument(
        "--named-connection",
        dest="named_connection",
        metavar="QUALIFIED_NAME",
        help="Named connection from Python module (e.g., myapp.connections.prod_db). "
             "The --db-file option can override the database specified in this connection.",
    )
    parser.add_argument(
        "--conn-param",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        dest="connection_params",
        help="Connection parameter override for named connection. Can be specified multiple times.",
    )


def create_connection_parent_parser():
    """Create a parent parser with connection and output arguments only.

    Used by named-query/named-procedure shared CLI helpers which
    require a parent_parser argument.
    """
    parser = argparse.ArgumentParser(add_help=False)
    add_connection_args(parser)
    parser.add_argument(
        "-o", "--output",
        choices=["table", "json", "csv", "tsv"],
        default="table",
        help='Output format. Defaults to "table" if rich is installed.',
    )
    parser.add_argument(
        "--rich-ascii",
        action="store_true",
        help="Use ASCII characters for rich table borders.",
    )
    return parser


def _parse_params(params: list) -> dict:
    """Parse --conn-param KEY=VALUE into a dictionary."""
    result = {}
    for param in params:
        if "=" in param:
            key, value = param.split("=", 1)
            result[key] = value
        else:
            print(f"Warning: Invalid parameter format: {param}. Use KEY=VALUE", file=sys.stderr)
    return result


def resolve_connection_config(db_file=None, named_connection=None,
                              connection_params=None) -> SQLiteConnectionConfig:
    """Resolve connection config with priority: db_file > named_connection + connection_params > default memory.

    Args:
        db_file: Database file path (--db-file)
        named_connection: Named connection name (--named-connection)
        connection_params: Connection parameters (--conn-param raw list)

    Returns:
        SQLiteConnectionConfig instance
    """
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLITE_MEMORY_DB

    if connection_params:
        conn_params = _parse_params(connection_params)
    else:
        conn_params = {}

    if named_connection:
        resolver = NamedConnectionResolver(named_connection).load()
        config = resolver.resolve(conn_params)

        # --db-file overrides the database from named connection
        if db_file:
            config.database = db_file
        elif config.database is None:
            config.database = SQLITE_MEMORY_DB

        return config

    # No named connection, use explicit --db-file or default to memory
    if db_file:
        return SQLiteConnectionConfig(database=db_file)

    return SQLiteConnectionConfig()


def resolve_connection_config_from_args(args) -> SQLiteConnectionConfig:
    """Resolve connection config from command-line arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        SQLiteConnectionConfig instance
    """
    return resolve_connection_config(
        db_file=getattr(args, 'db_file', None),
        named_connection=getattr(args, 'named_connection', None),
        connection_params=getattr(args, 'connection_params', []),
    )


def create_backend(args) -> SQLiteBackend:
    """Create and connect a backend.

    For simple use cases like introspect/status.
    The caller is responsible for calling backend.disconnect() in a finally block.

    Args:
        args: Parsed command-line arguments

    Returns:
        Connected and adapted SQLiteBackend instance
    """
    config = resolve_connection_config_from_args(args)
    backend = SQLiteBackend(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    return backend


def create_backend_from_memory() -> SQLiteBackend:
    """Create and connect an in-memory database backend.

    For the info command which does not need connection arguments.

    Returns:
        Connected and adapted SQLiteBackend instance
    """
    config = SQLiteConnectionConfig()
    backend = SQLiteBackend(connection_config=config)
    backend.connect()
    backend.introspect_and_adapt()
    return backend


def create_backend_factory(args) -> Callable[[], SQLiteBackend]:
    """Create a backend factory function.

    For reuse by named-query/named-procedure.

    Args:
        args: Parsed command-line arguments

    Returns:
        Factory function that returns a connected and adapted SQLiteBackend
    """
    def factory():
        config = resolve_connection_config_from_args(args)
        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        backend.introspect_and_adapt()
        return backend
    return factory


def create_async_backend_factory(args) -> Callable:
    """Create an async backend factory function.

    For reuse by named-query/named-procedure in async mode.

    Args:
        args: Parsed command-line arguments

    Returns:
        Async factory function
    """
    def factory():
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
        config = resolve_connection_config_from_args(args)
        async_backend = AsyncSQLiteBackend(connection_config=config)
        return async_backend
    return factory
