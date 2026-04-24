# src/rhosocial/activerecord/backend/impl/sqlite/cli/__init__.py
"""SQLite CLI common definitions and subcommand registration."""

import importlib

COMMAND_NAMES = [
    'info', 'query', 'introspect', 'status',
    'named-query', 'named-procedure', 'named-connection',
]


def register_commands(subparsers):
    """Register all subcommands.

    Args:
        subparsers: argparse.Subparsers object
    """
    from .info import create_parser as info_parser
    from .query import create_parser as query_parser
    from .introspect import create_parser as introspect_parser
    from .status import create_parser as status_parser
    from .named_query import create_parser as nq_parser
    from .named_procedure import create_parser as np_parser
    from .named_connection import create_parser as nc_parser

    info_parser(subparsers)
    query_parser(subparsers)
    introspect_parser(subparsers)
    status_parser(subparsers)
    nq_parser(subparsers)
    np_parser(subparsers)
    nc_parser(subparsers)


def get_handler(command_name: str):
    """Get the handler function for a subcommand.

    Args:
        command_name: Subcommand name (e.g. 'info', 'named-query')

    Returns:
        The corresponding handle function
    """
    module_name = command_name.replace('-', '_')
    module = importlib.import_module(f'.{module_name}', __name__)
    return module.handle
