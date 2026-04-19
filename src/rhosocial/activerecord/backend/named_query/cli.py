# src/rhosocial/activerecord/backend/named_query/cli.py
"""
CLI utilities for named query functionality.

This module provides reusable functions to add named-query subcommand
to various CLI tools (like sqlite backend CLI). It handles the complete
lifecycle of named query execution from the command line.

Features:
    - Execute named queries by qualified name
    - List all queries in a module
    - Show query description and parameters
    - Dry-run mode to preview SQL
    - EXPLAIN query plan execution

Named Query CLI Subcommand:
    The CLI provides a 'named-query' subcommand with the following options:

    positional arguments:
        qualified_name: Fully qualified Python name (module.path.callable)

    optional arguments:
        -e, --example: Show detailed info for specific query
        --param KEY=VALUE: Query parameter (repeatable)
        --describe: Show signature without executing
        --dry-run: Print SQL without executing
        --list: List all queries in module
        --force: Force non-SELECT execution
        --explain: Execute EXPLAIN plan

Usage Example:
    >>> # Execute a named query
    >>> prog run myapp.queries.active_users --db-file mydb.sqlite

    >>> # List available queries
    >>> prog run myapp.queries --list

    >>> # Show query details
    >>> prog run myapp.queries.user_by_status --example user_by_status

Note:
    This is a backend CLI feature. It is independent of ActiveRecord
    or ActiveQuery and is designed for CLI-based query execution.

Warning:
    This module is for backend CLI tools. For programmatic access
    to named queries, use NamedQueryResolver directly.
"""
import argparse
import importlib
import sys
from typing import Any, Callable, Optional

from rhosocial.activerecord.backend.expression.executable import Executable
from rhosocial.activerecord.backend.named_query import (
    NamedQueryError,
    NamedQueryResolver,
    list_named_queries_in_module,
)
from rhosocial.activerecord.backend.schema import StatementType


def _replace_prog_placeholder(docstring: str, prog: str = None) -> str:
    """Replace %(prog)s and %%%(prog)s placeholders with actual program name.

    This helper function replaces common argparse placeholder patterns
    with the actual program name for better help text display.

    Args:
        docstring: The docstring containing placeholders.
        prog: The program name to substitute. Defaults to the
            standard sqlite backend CLI path.

    Returns:
        str: The docstring with placeholders replaced.

    Example:
        >>> doc = "Usage: %(prog)s query <sql>"
        >>> replaced = _replace_prog_placeholder(doc, "myprog")
        >>> print(replaced)  # "Usage: myprog query <sql>"
    """
    if prog is None:
        prog = "python -m rhosocial.activerecord.backend.impl.sqlite"
    return docstring.replace("%(prog)s", prog).replace("%%(prog)s", prog)


def create_named_query_parser(
    subparsers: argparse._SubParsersAction,
    parent_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """Create the named-query subcommand parser.

    This function adds a 'named-query' subcommand to an argparse-based
    CLI tool. It provides a complete interface for executing named
    queries from the command line.

    Args:
        subparsers: The subparsers action from the main parser.
            Created via argparse.ArgumentParser().add_subparsers().
        parent_parser: Parent parser with common arguments (like --db-file,
            --rich-ascii, etc.). This allows sharing common options.

    Returns:
        argparse.ArgumentParser: The created parser for named-query
            subcommand. Can be used to add additional arguments.

    Raises:
        TypeError: If subparsers is not a valid _SubParsersAction.

    Example:
        >>> import argparse
        >>> parser = argparse.ArgumentParser()
        >>> subparsers = parser.add_subparsers()
        >>> parent = argparse.ArgumentParser(add_help=False)
        >>> parent.add_argument('--db-file', required=True)
        >>> nq_parser = create_named_query_parser(subparsers, parent)
    """
    nq_parser = subparsers.add_parser(
        "named-query",
        help="Execute a named query defined as a Python callable",
        parents=[parent_parser],
        epilog="""Examples:
  # Execute named query with default params
  %(prog)s myapp.queries.orders.high_value_pending --db-file mydb.sqlite

  # Override parameters
  %(prog)s myapp.queries.orders.high_value_pending --db-file mydb.sqlite \\
      --param threshold=5000 --param days=7

  # Show signature without executing
  %(prog)s myapp.queries.orders.high_value_pending --describe

  # Preview SQL without executing
  %(prog)s myapp.queries.orders.orders_by_status \\
      --db-file mydb.sqlite --param status=pending --dry-run

  # List all named queries in a module
  %(prog)s myapp.queries.orders --list

  # Show detailed info for a specific query (using --example)
  %(prog)s myapp.queries.orders --example high_value_pending
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    nq_parser.add_argument(
        "qualified_name",
        help="Fully qualified Python module path or name",
    )
    nq_parser.add_argument(
        "-e",
        "--example",
        dest="example",
        default=None,
        help="Show detailed info for a specific query in the module",
    )
    nq_parser.add_argument(
        "--param",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        dest="params",
        help="Query parameter. Can be specified multiple times.",
    )
    nq_parser.add_argument(
        "--describe",
        action="store_true",
        help="Show signature and docstring without executing.",
    )
    nq_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered SQL and params without executing.",
    )
    nq_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_queries",
        help="List all discoverable named queries in the given module. "
             "If a specific query name is given, show detailed info.",
    )
    nq_parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution even for non-SELECT statements (DML/DDL).",
    )
    nq_parser.add_argument(
        "--explain",
        action="store_true",
        help="Execute EXPLAIN and interpret execution plan.",
    )
    return nq_parser


def parse_params(params: list) -> dict:
    """Parse --param KEY=VALUE into a dictionary.

    This function converts CLI arguments (list of 'KEY=VALUE' strings)
    into a dictionary for passing to named query resolvers.

    Args:
        params: List of parameter strings in 'KEY=VALUE' format.
            Each string must contain exactly one '=' sign.

    Returns:
        Dict[str, str]: Dictionary mapping parameter names to values.

    Raises:
        No exceptions. Invalid format strings are printed to stderr as warnings.

    Warning:
        Values are parsed as strings. The resolver handles type conversion
        based on the callable's signature annotations.

    Example:
        >>> params = ["limit=100", "status=active"]
        >>> result = parse_params(params)
        >>> print(result)  # {'limit': '100', 'status': 'active'}
    """
    result = {}
    for param in params:
        if "=" in param:
            key, value = param.split("=", 1)
            result[key] = value
        else:
            print(
                f"Warning: Invalid parameter format: {param}. Use KEY=VALUE",
                file=sys.stderr,
            )
    return result


def handle_named_query(
    args: Any,
    provider: Any,
    backend_factory: Callable[[], Any],
    get_dialect: Callable[[Any], Any],
    execute_query: Callable[[str, tuple, StatementType], Any],
    disconnect: Optional[Callable[[], None]] = None,
) -> None:
    """Handle named-query subcommand execution.

    This is the main handler function for the named-query subcommand.
    It processes arguments and executes the query, handling all
    the different operation modes (list, describe, execute, dry-run, etc.).

    Args:
        args: Parsed command-line arguments namespace. Must contain:
            - qualified_name: The query to execute
            - example: Query name to show (for --example)
            - params: List of KEY=VALUE strings
            - describe: True to show description only
            - dry_run: True to preview SQL only
            - list_queries: True to list queries
            - force: True to force non-SELECT execution
            - explain: True to run EXPLAIN
        provider: Output provider for displaying results.
            Must have methods like display_success(),
            display_results(), display_no_result_object(), etc.
        backend_factory: Callable that returns a connected backend
            instance. This is called to get a database connection.
        get_dialect: Callable that receives backend and returns
            the dialect instance. The dialect is the first parameter
            to named queries.
        execute_query: Callable that executes (sql, params, stmt_type)
            and returns a result object with affected_rows, duration, data.
        disconnect: Optional callable to disconnect backend after
            execution. Called in finally block.

    Returns:
        None. This function handles all output and exit codes.

    Raises:
        SystemExit: With code 1 on error (query not found, invalid
            params, execution failure, etc.). Errors are printed
            to stderr before exit.

    Operation Modes:
        1. --list: Lists all queries in a module
        2. --example NAME: Shows detailed info for a query
        3. --describe: Shows query signature
        4. --dry-run: Previews SQL without execution
        5. Normal: Executes the query

    Example:
        >>> # Basic usage in a CLI tool
        >>> def main():
        ...     parser = argparse.ArgumentParser()
        ...     subparsers = parser.add_subparsers()
        ...     nq_parser = create_named_query_parser(subparsers, parent_parser)
        ...     args = parser.parse_args()
        ...     handle_named_query(
        ...         args,
        ...         provider,
        ...         lambda: SQLiteBackend.connect(db_file),
        ...         lambda b: b.get_dialect(),
        ...         lambda sql, params, t: backend.execute(...),
        ...     )
    """
    qualified_name = args.qualified_name

    if args.list_queries or args.example:
        try:
            importlib.invalidate_caches()

            module_name = qualified_name
            example_name = args.example

            if not example_name and "." in qualified_name:
                parts = qualified_name.rsplit(".", 1)
                potential_module = parts[0]
                potential_example = parts[1]
                try:
                    test_module = importlib.import_module(potential_module)
                    if hasattr(test_module, potential_example):
                        module_name = potential_module
                        example_name = potential_example
                except (ModuleNotFoundError, ImportError):
                    pass

            queries = list_named_queries_in_module(module_name)

            if example_name:
                matched = None
                for q in queries:
                    if q["name"] == example_name:
                        matched = q
                        break

                if matched:
                    print(f"Query: {module_name}.{example_name}")
                    print(f"Signature: {matched['signature']}")
                    print(f"Brief: {matched['brief']}")
                    print()
                    print("Full Docstring:")
                    print(_replace_prog_placeholder(matched['docstring']))
                else:
                    print(
                        f"Query '{example_name}' not found in module '{module_name}'",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                return

            if not queries:
                print(f"No named queries found in module: {module_name}")
                return

            print(f"Module: {module_name}")
            print(f"{'Name':<30} {'Parameters':<40} {'Brief':<30}")
            print("-" * 100)
            for q in queries:
                params = q["signature"].replace("dialect, ", "").replace("(dialect)", "")
                brief = q["brief"][:27] + "..." if len(q["brief"]) > 30 else q["brief"]
                print(f"{q['name']:<30} {params:<40} {brief:<30}")

        except NamedQueryError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.describe:
        try:
            resolver = NamedQueryResolver(qualified_name).load()
            info = resolver.describe()
            print(f"Query: {info['qualified_name']}")
            print(f"Docstring: {info['docstring']}")
            print(f"Signature: {info['signature']}")
            print("Parameters (excluding 'dialect'):")
            for name, param in info["parameters"].items():
                default_str = f" default={param['default']}" if param["has_default"] else ""
                print(f"  {name} {param['type']}{default_str}")
        except NamedQueryError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    user_params = parse_params(args.params)
    backend = None

    try:
        backend = backend_factory()
        dialect = get_dialect(backend)
        resolver = NamedQueryResolver(qualified_name).load()
        expression = resolver.execute(dialect, user_params)

        if not isinstance(expression, Executable):
            print(
                f"Error: Named query returned {type(expression).__name__}, "
                "which does not implement Executable protocol. "
                "Direct SQL strings are not allowed. Use 'query' subcommand for raw SQL.",
                file=sys.stderr,
            )
            sys.exit(1)

        stmt_type = expression.statement_type
        sql, params = expression.to_sql()

        if args.dry_run:
            print("[DRY RUN] SQL:")
            print(f"  {sql}")
            print(f"Params: {params}")
            return

        if stmt_type == StatementType.EXPLAIN and not args.explain:
            print(
                "Error: EXPLAIN queries require --dry-run or --explain for execution.",
                file=sys.stderr,
            )
            sys.exit(1)

        if stmt_type not in (StatementType.DQL, StatementType.SELECT) and not args.force:
            print(
                f"[WARN] {type(expression).__name__} is a {stmt_type.name} statement, not a SELECT query.",
                file=sys.stderr,
            )
            print("This may modify data. Use --force to proceed.", file=sys.stderr)
            sys.exit(1)

        result = execute_query(sql, params, stmt_type)

        if not result:
            provider.display_no_result_object()
        else:
            provider.display_success(result.affected_rows, result.duration)
            if result.data:
                provider.display_results(result.data, use_ascii=args.rich_ascii)
            else:
                provider.display_no_data()

    except NamedQueryError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        from rhosocial.activerecord.backend.errors import ConnectionError, QueryError

        if isinstance(e, ConnectionError):
            provider.display_connection_error(e)
        elif isinstance(e, QueryError):
            provider.display_query_error(e)
        else:
            provider.display_unexpected_error(e, is_async=False)
        sys.exit(1)
    finally:
        if disconnect and backend:
            disconnect()