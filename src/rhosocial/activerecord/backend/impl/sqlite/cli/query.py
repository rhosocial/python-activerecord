# src/rhosocial/activerecord/backend/impl/sqlite/cli/query.py
"""query subcommand - Execute SQL queries.

query requires connection arguments and --log-level (only query uses this argument).
"""

import argparse
import logging
import sys
import time

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from .connection import add_connection_args, resolve_connection_config_from_args
from .output import create_provider, RICH_AVAILABLE

OUTPUT_CHOICES = ['table', 'json', 'csv', 'tsv']


def create_parser(subparsers):
    """Create the query subcommand parser."""
    parser = subparsers.add_parser(
        'query',
        help='Execute SQL query',
        epilog="""Examples:
  # Query a file database
  %(prog)s query --db-file mydb.sqlite "SELECT * FROM users"

  # Query using named connection
  %(prog)s query --named-connection myapp.connections.prod_db "SELECT 1"

  # Named connection with parameter override (--db-file takes precedence)
  %(prog)s query --named-connection myapp.connections.prod_db --db-file other.db "SELECT * FROM users"

  # Execute SQL from file
  %(prog)s query --db-file mydb.sqlite -f query.sql

  # Execute multi-statement script
  %(prog)s query --db-file mydb.sqlite --executescript -f script.sql
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Output format (all)
    parser.add_argument(
        '-o', '--output',
        choices=OUTPUT_CHOICES,
        default='table',
        help='Output format (default: table)',
    )

    # Connection arguments
    add_connection_args(parser)

    # Log level (query only)
    parser.add_argument(
        '--log-level',
        default='INFO',
        help='Set logging level (e.g., DEBUG, INFO)',
    )

    # Rich display options
    parser.add_argument(
        '--rich-ascii',
        action='store_true',
        help='Use ASCII characters for rich table borders.',
    )

    # query-specific arguments
    parser.add_argument(
        "sql",
        nargs="?",
        default=None,
        help="SQL query to execute. If not provided, reads from --file.",
    )
    parser.add_argument(
        "-f", "--file",
        default=None,
        help="Path to a file containing SQL to execute.",
    )
    parser.add_argument(
        "--executescript",
        action="store_true",
        help="Execute the input as a multi-statement script.",
    )

    return parser


def handle(args):
    """Handle the query subcommand."""
    # Set log level (query only)
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    provider = create_provider(args.output, ascii_borders=args.rich_ascii)

    if RICH_AVAILABLE:
        from rhosocial.activerecord.backend.output_rich import RichOutputProvider
        if isinstance(provider, RichOutputProvider):
            from rich.console import Console
            from rich.logging import RichHandler
            handler = RichHandler(rich_tracebacks=True, show_path=False, console=Console(stderr=True))
            logging.basicConfig(level=numeric_level, format="%(message)s", datefmt="[%X]", handlers=[handler])
        else:
            logging.basicConfig(level=numeric_level, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stderr)
    else:
        logging.basicConfig(level=numeric_level, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stderr)

    provider.display_greeting()

    # Determine SQL source
    sql_source = None
    if args.sql:
        sql_source = args.sql
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                sql_source = f.read()
        except FileNotFoundError:
            logging.error(f"Error: File not found at {args.file}")
            sys.exit(1)
    elif not sys.stdin.isatty():
        sql_source = sys.stdin.read()

    if not sql_source:
        msg = "Error: No SQL query provided. Use a positional argument, the --file flag, or pipe from stdin."
        print(msg, file=sys.stderr)
        sys.exit(1)

    config = resolve_connection_config_from_args(args)
    backend = SQLiteBackend(connection_config=config)

    if args.executescript:
        _execute_script(sql_source, backend, provider)
    else:
        _execute_query(sql_source, backend, provider, use_ascii=args.rich_ascii)


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------

def _guess_statement_type(sql: str) -> StatementType:
    """Guess the statement type from SQL text."""
    sql_stripped = sql.strip().upper()
    if sql_stripped.startswith(("SELECT", "WITH", "EXPLAIN", "PRAGMA")):
        return StatementType.DQL
    elif sql_stripped.startswith(("INSERT", "UPDATE", "DELETE")):
        return StatementType.DML
    elif sql_stripped.startswith(("CREATE", "ALTER", "DROP")):
        return StatementType.DDL
    else:
        return StatementType.OTHER


def _execute_query(sql_query: str, backend: SQLiteBackend, provider, **kwargs):
    """Execute a single SQL query and display results."""
    try:
        backend.connect()
        provider.display_query(sql_query, is_async=False)

        stmt_type = _guess_statement_type(sql_query)
        exec_options = ExecutionOptions(stmt_type=stmt_type)

        result = backend.execute(sql_query, options=exec_options)

        if not result:
            provider.display_no_result_object()
        else:
            provider.display_success(result.affected_rows, result.duration)
            if result.data:
                provider.display_results(result.data, **kwargs)
            else:
                provider.display_no_data()

    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        provider.display_unexpected_error(e, is_async=False)
        sys.exit(1)
    finally:
        if backend._connection:
            backend.disconnect()
        provider.display_disconnect(is_async=False)


def _execute_script(sql_script: str, backend: SQLiteBackend, provider):
    """Execute a multi-statement SQL script."""
    try:
        backend.connect()
        provider.display_query(sql_script, is_async=False)
        start_time = time.perf_counter()
        backend.executescript(sql_script)
        duration = time.perf_counter() - start_time
        provider.display_success(0, duration)
    except ConnectionError as e:
        provider.display_connection_error(e)
        sys.exit(1)
    except QueryError as e:
        provider.display_query_error(e)
        sys.exit(1)
    except Exception as e:
        provider.display_unexpected_error(e, is_async=False)
        sys.exit(1)
    finally:
        if backend._connection:
            backend.disconnect()
        provider.display_disconnect(is_async=False)
