# src/rhosocial/activerecord/backend/impl/sqlite/__main__.py
import argparse
import logging
import sys
import time

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.output import JsonOutputProvider, CsvOutputProvider, TsvOutputProvider
from rhosocial.activerecord.backend.options import ExecutionOptions # Added import
from rhosocial.activerecord.backend.schema import StatementType

# Attempt to import rich for formatted output
try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rhosocial.activerecord.backend.output_rich import RichOutputProvider
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Define a dummy class if rich is not available
    RichOutputProvider = None

logger = logging.getLogger(__name__)


def guess_statement_type(sql: str) -> StatementType:
    """Makes a best guess at the statement type from a raw SQL string."""
    # A simple parser that looks at the first word.
    # This is non-critical and only for CLI usability.
    sql_stripped = sql.strip().upper()
    if sql_stripped.startswith(("SELECT", "WITH", "EXPLAIN", "PRAGMA")):
        return StatementType.DQL
    elif sql_stripped.startswith(("INSERT", "UPDATE", "DELETE")):
        return StatementType.DML
    elif sql_stripped.startswith(("CREATE", "ALTER", "DROP")):
        return StatementType.DDL
    else:
        # For other types or when in doubt, default to OTHER
        return StatementType.OTHER


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against a SQLite backend.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # Input source arguments
    parser.add_argument(
        'query',
        nargs='?',
        default=None,
        help='SQL query to execute. If not provided, reads from --file or stdin.'
    )
    parser.add_argument(
        '-f', '--file',
        default=None,
        help='Path to a file containing SQL to execute.'
    )
    # Connection parameters
    parser.add_argument(
        '--db-file',
        default=None,
        help='Path to the SQLite database file. If not provided, an in-memory database will be used.'
    )
    # Execution options
    parser.add_argument(
        '--executescript',
        action='store_true',
        help='Execute the input as a multi-statement script. Use for files from dumps.'
    )
    # Output and logging options
    parser.add_argument(
        '--output',
        choices=['table', 'json', 'csv', 'tsv'],
        default='table',
        help='Output format. Defaults to "table" if rich is installed, otherwise "json".'
    )
    parser.add_argument('--log-level', default='INFO', help='Set logging level (e.g., DEBUG, INFO)')
    parser.add_argument('--rich-ascii', action='store_true', help='Use ASCII characters for rich table borders.')

    return parser.parse_args()


def get_provider(args):
    """Factory function to get the correct output provider."""
    output_format = args.output
    # Fallback to json if rich is not available and table is requested
    if output_format == 'table' and not RICH_AVAILABLE:
        output_format = 'json'

    if output_format == 'table':
        return RichOutputProvider(console=Console(), ascii_borders=args.rich_ascii)
    if output_format == 'json':
        return JsonOutputProvider()
    if output_format == 'csv':
        return CsvOutputProvider()
    if output_format == 'tsv':
        return TsvOutputProvider()
    
    # Default provider
    return JsonOutputProvider()


def execute_query(sql_query: str, backend: SQLiteBackend, provider: 'OutputProvider', **kwargs):
    try:
        backend.connect()
        # Since this backend is sync-only, is_async is always False
        provider.display_query(sql_query, is_async=False)
        
        # Determine statement type for the CLI tool
        stmt_type = guess_statement_type(sql_query)
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
        # is_async is always False here
        provider.display_unexpected_error(e, is_async=False)
        sys.exit(1)
    finally:
        if backend._connection:
            backend.disconnect()
            # is_async is always False here
            provider.display_disconnect(is_async=False)


def execute_script(sql_script: str, backend: SQLiteBackend, provider: 'OutputProvider'):
    try:
        backend.connect()
        provider.display_query(sql_script, is_async=False)
        start_time = time.perf_counter()
        backend.executescript(sql_script)
        duration = time.perf_counter() - start_time
        # Executescript doesn't return affected rows, so we pass 0.
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


def main():
    args = parse_args()

    # Setup logging
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    provider = get_provider(args)
    
    # Configure logging handlers based on provider
    # Force all logging to stderr to keep stdout clean for data piping
    if RICH_AVAILABLE and isinstance(provider, RichOutputProvider):
         logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, show_path=False, console=Console(stderr=True))]
        )
    else:
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )

    provider.display_greeting()

    # Determine input source
    sql_source = None
    if args.query:
        sql_source = args.query
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                sql_source = f.read()
        except FileNotFoundError:
            logger.error(f"Error: File not found at {args.file}")
            sys.exit(1)
    elif not sys.stdin.isatty():
        sql_source = sys.stdin.read()

    if not sql_source:
        print("Error: No SQL query provided. Use a positional argument, the --file flag, or pipe from stdin.", file=sys.stderr)
        sys.exit(1)

    # Setup backend config
    db_path = args.db_file if args.db_file else ":memory:"
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    # Execute as a script or a single query
    if args.executescript:
        execute_script(sql_source, backend, provider)
    else:
        execute_query(sql_source, backend, provider, use_ascii=args.rich_ascii)


if __name__ == "__main__":
    main()
