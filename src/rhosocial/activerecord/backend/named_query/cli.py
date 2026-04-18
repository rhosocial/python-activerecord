# src/rhosocial/activerecord/backend/named_query/cli.py
"""
CLI utilities for named query functionality.

Provides reusable functions to add named-query subcommand to various backends.
"""
import argparse
import sys
from typing import Any, Callable, Optional

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.named_query import (
    NamedQueryResolver,
    list_named_queries_in_module,
    NamedQueryError,
)
from rhosocial.activerecord.backend.schema import StatementType


def create_named_query_parser(
    subparsers: argparse._SubParsersAction,
    parent_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """Create the named-query subcommand parser.

    Args:
        subparsers: The subparsers action from the main parser
        parent_parser: Parent parser with common arguments

    Returns:
        The created parser for named-query subcommand
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
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    nq_parser.add_argument(
        "qualified_name",
        help="Fully qualified Python name: 'module.path.function_or_class[.method]'",
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
        help="List all discoverable named queries in the given module.",
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
    """Parse --param KEY=VALUE into a dictionary."""
    result = {}
    for param in params:
        if "=" in param:
            key, value = param.split("=", 1)
            result[key] = value
        else:
            print(f"Warning: Invalid parameter format: {param}. Use KEY=VALUE", file=sys.stderr)
    return result


def guess_statement_type(sql: str) -> StatementType:
    """Guess the statement type from SQL string."""
    sql_stripped = sql.strip().upper()
    if sql_stripped.startswith(("SELECT", "WITH", "EXPLAIN", "PRAGMA")):
        return StatementType.DQL
    elif sql_stripped.startswith(("INSERT", "UPDATE", "DELETE")):
        return StatementType.DML
    elif sql_stripped.startswith(("CREATE", "ALTER", "DROP")):
        return StatementType.DDL
    else:
        return StatementType.OTHER


def _is_explain_statement(sql: str) -> bool:
    """Check if SQL is an EXPLAIN statement."""
    return sql.strip().upper().startswith("EXPLAIN")


def handle_named_query(
    args: Any,
    provider: Any,
    backend_factory: Callable[[], Any],
    get_dialect: Callable[[Any], Any],
    execute_query: Callable[[str, tuple, StatementType], Any],
    disconnect: Optional[Callable[[], None]] = None,
) -> None:
    """Handle named-query subcommand.

    Args:
        args: Parsed command-line arguments
        provider: Output provider for displaying results
        backend_factory: Callable that returns a backend instance (connected)
        get_dialect: Callable that receives backend and returns dialect
        execute_query: Callable that executes (sql, params, stmt_type) -> result
        disconnect: Optional callable to disconnect backend
    """
    qualified_name = args.qualified_name

    if args.list_queries:
        try:
            queries = list_named_queries_in_module(qualified_name)
            if not queries:
                print(f"No named queries found in module: {qualified_name}")
                return
            print(f"Module: {qualified_name}")
            for q in queries:
                print(f"  {q['name']}{q['signature']}")
                if q['docstring']:
                    print(f"      {q['docstring']}")
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
            for name, param in info['parameters'].items():
                default_str = f" default={param['default']}" if param['has_default'] else ""
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

        if not isinstance(expression, BaseExpression):
            actual_type = type(expression).__name__
            print(
                f"Error: Named query returned {actual_type}, not BaseExpression. "
                "Direct SQL strings are not allowed.",
                file=sys.stderr,
            )
            sys.exit(1)

        sql, params = expression.to_sql()
        stmt_type = guess_statement_type(sql)

        if args.dry_run:
            print("[DRY RUN] SQL:")
            print(f"  {sql}")
            print(f"Params: {params}")
            return

        if _is_explain_statement(sql) and not args.explain:
            print(
                "Error: EXPLAIN queries not allowed for actual execution. "
                "Use --dry-run or --explain.",
                file=sys.stderr,
            )
            sys.exit(1)

        if stmt_type != StatementType.DQL and not args.force:
            print(
                f"[WARN] Query resolves to {stmt_type.name} statement, not a SELECT query.",
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