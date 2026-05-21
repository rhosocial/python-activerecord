# src/rhosocial/activerecord/backend/named_expression/cli.py
"""
CLI utilities for named expression functionality.

This module provides reusable functions to add named-expression subcommand
to various CLI tools (like sqlite backend CLI). It handles the complete
lifecycle of named expression execution from the command line.

Features:
    - Execute named expressions by qualified name
    - List all expressions in a module
    - Show expression description and parameters
    - Dry-run mode to preview SQL
    - EXPLAIN query plan execution

Named Expression CLI Subcommand:
    The CLI provides a 'named-expression' subcommand with the following options:

    positional arguments:
        qualified_name: Fully qualified Python name (module.path.callable)

    optional arguments:
        -e, --example: Show detailed info for specific expression
        --param KEY=VALUE: Expression parameter (repeatable)
        --describe: Show signature without executing
        --dry-run: Print SQL without executing
        --list: List all expressions in module
        --force: Force non-SELECT execution
        --explain: Execute EXPLAIN plan
        --no-probe: Skip dry-probe when listing

Usage Example:
    >>> # Execute a named expression
    >>> prog run myapp.queries.active_users --db-file mydb.sqlite

    >>> # List available expressions
    >>> prog run myapp.queries --list

    >>> # Show expression details
    >>> prog run myapp.queries.user_by_status --example user_by_status

Note:
    This is a backend CLI feature. It is independent of ActiveRecord
    or ActiveQuery and is designed for CLI-based expression execution.

Warning:
    This module is for backend CLI tools. For programmatic access
    to named expressions, use NamedExpressionResolver directly.
"""
import argparse
import importlib
import sys
from typing import Any, Callable, Optional

from rhosocial.activerecord.backend.expression.executable import Executable
from rhosocial.activerecord.backend.named_expression import (
    NamedExpressionError,
    NamedExpressionResolver,
    list_named_expressions_in_module,
)
from rhosocial.activerecord.backend.schema import StatementType


FLAG_LEGEND = {
    "DQL": "Data Query Language (SELECT)",
    "DML": "Data Manipulation Language (INSERT/UPDATE/DELETE)",
    "DDL": "Data Definition Language (CREATE/ALTER/DROP)",
    "TCL": "Transaction Control Language",
    "CALL": "Stored Procedure Call",
    "EXPLAIN": "Execution Plan",
    "CLAUSE": "Sub-clause Fragment (not executable standalone)",
    "?": "Unknown (unable to probe)",
    "OTHER": "Other expression type",
}


def _replace_prog_placeholder(docstring: str, prog: str = None) -> str:
    """Replace %(prog)s and %%%(prog)s placeholders with actual program name."""
    if prog is None:
        prog = "python -m rhosocial.activerecord.backend.impl.sqlite"
    return docstring.replace("%(prog)s", prog).replace("%%(prog)s", prog)


def create_named_expression_parser(
    subparsers: argparse._SubParsersAction,
    parent_parser: argparse.ArgumentParser,
    epilog: str = None,
) -> argparse.ArgumentParser:
    """Create the named-expression subcommand parser.

    This function adds a 'named-expression' subcommand to an argparse-based
    CLI tool. It provides a complete interface for executing named
    expressions from the command line.

    Args:
        subparsers: The subparsers action from the main parser.
        parent_parser: Parent parser with common arguments (like --db-file,
            --rich-ascii, etc.).
        epilog: Custom examples text. If not provided, defaults to SQLite-style
            examples (--db-file). Pass empty string to omit examples.

    Returns:
        argparse.ArgumentParser: The created parser for named-expression subcommand.
    """
    if epilog is None:
        epilog = """Examples:
  # Execute named expression with default params
  %(prog)s myapp.queries.orders.high_value_pending --db-file mydb.sqlite

  # Override parameters
  %(prog)s myapp.queries.orders.high_value_pending --db-file mydb.sqlite \\
      --param threshold=5000 --param days=7

  # Show signature without executing
  %(prog)s myapp.queries.orders.high_value_pending --describe

  # Preview SQL without executing
  %(prog)s myapp.queries.orders.orders_by_status \\
      --db-file mydb.sqlite --param status=pending --dry-run

  # List all named expressions in a module
  %(prog)s myapp.queries.orders --list

  # Show detailed info for a specific expression (using --example)
  %(prog)s myapp.queries.orders --example high_value_pending
"""
    ne_parser = subparsers.add_parser(
        "named-expression",
        help="Execute a named expression defined as a Python callable",
        parents=[parent_parser],
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ne_parser.add_argument(
        "qualified_name",
        nargs="?",
        default=None,
        help="Fully qualified Python module path or name",
    )
    ne_parser.add_argument(
        "-e",
        "--example",
        dest="example",
        default=None,
        help="Show detailed info for a specific expression in the module",
    )
    ne_parser.add_argument(
        "--param",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        dest="params",
        help="Expression parameter. Can be specified multiple times.",
    )
    ne_parser.add_argument(
        "--describe",
        action="store_true",
        help="Show signature and docstring without executing.",
    )
    ne_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the rendered SQL and params without executing.",
    )
    ne_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_queries",
        help="List all discoverable named expressions in the given module. "
             "If a specific expression name is given, show detailed info.",
    )
    ne_parser.add_argument(
        "--force",
        action="store_true",
        help="Force execution even for non-SELECT statements (DML/DDL).",
    )
    ne_parser.add_argument(
        "--explain",
        action="store_true",
        help="Execute EXPLAIN and interpret execution plan.",
    )
    ne_parser.add_argument(
        "--async",
        dest="is_async",
        action="store_true",
        help="Use asynchronous execution (requires async database driver).",
    )
    ne_parser.add_argument(
        "--no-probe",
        action="store_true",
        help="Skip dry-probe when listing; show '?' for all tags. Does not require a DB connection.",
    )
    return ne_parser


def parse_params(params: list) -> dict:
    """Parse --param KEY=VALUE into a dictionary.

    Args:
        params: List of parameter strings in 'KEY=VALUE' format.

    Returns:
        Dict[str, str]: Dictionary mapping parameter names to values.
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


def _execute_expression(
    expression: Any,
    args: Any,
    execute_query: Callable,
    provider: Any,
) -> None:
    """Execute a resolved expression (with Executable check)."""
    if not isinstance(expression, Executable):
        print(
            f"Error: expression returned {type(expression).__name__}, "
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
            "Error: EXPLAIN expressions require --dry-run or --explain for execution.",
            file=sys.stderr,
        )
        sys.exit(1)

    if stmt_type not in (StatementType.DQL, StatementType.SELECT) and not args.force:
        print(
            f"[WARN] expression is a {stmt_type.name} statement, not a SELECT query.",
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


def handle_named_expression(
    args: Any,
    provider: Any,
    backend_factory: Callable[[], Any],
    get_dialect: Callable[[Any], Any],
    execute_query: Callable[[str, tuple, StatementType], Any],
    disconnect: Optional[Callable[[], None]] = None,
    backend_async_factory: Optional[Callable[[], Any]] = None,
    get_dialect_async: Optional[Callable[[Any], Any]] = None,
    execute_query_async: Optional[Callable[[str, tuple, StatementType], Any]] = None,
    disconnect_async: Optional[Callable[[], None]] = None,
) -> None:
    """Handle named-expression subcommand execution.

    This is the main handler function for the named-expression subcommand.
    It processes arguments and executes the expression, handling all
    the different operation modes (list, describe, execute, dry-run, etc.).

    Args:
        args: Parsed command-line arguments namespace.
        provider: Output provider for displaying results.
        backend_factory: Callable that returns a connected backend instance.
        get_dialect: Callable that receives backend and returns the dialect.
        execute_query: Callable that executes (sql, params, stmt_type).
        disconnect: Optional callable to disconnect backend after execution.
        backend_async_factory: Optional async backend factory.
        get_dialect_async: Optional async dialect getter.
        execute_query_async: Optional async query executor.
        disconnect_async: Optional async disconnect.

    Returns:
        None. This function handles all output and exit codes.

    Raises:
        SystemExit: With code 1 on error.
    """
    qualified_name = getattr(args, "qualified_name", None)

    # --list / --example mode (no DB connection required)
    if args.list_queries or args.example:
        try:
            importlib.invalidate_caches()

            module_name = qualified_name or ""
            example_name = args.example

            if not module_name and not example_name:
                print(
                    "Error: module name required for --list. "
                    "Usage: <module_name> --list",
                    file=sys.stderr,
                )
                sys.exit(1)

            if not example_name and qualified_name and "." in qualified_name:
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

            dialect = None
            if not args.no_probe:
                try:
                    backend = backend_factory()
                    dialect = get_dialect(backend)
                    if disconnect:
                        disconnect()
                except Exception:
                    dialect = None

            expressions = list_named_expressions_in_module(module_name, dialect)

            if example_name:
                matched = None
                for q in expressions:
                    if q["name"] == example_name:
                        matched = q
                        break

                if matched:
                    print(f"Expression: {module_name}.{example_name}")
                    print(f"Signature: {matched['signature']}")
                    print(f"Brief: {matched['brief']}")
                    print(f"Tags: {','.join(matched.get('tags', ['?']))}")
                    print()
                    print("Parameters:")
                    for ps in matched.get("param_specs", []):
                        required = "" if ps["has_default"] else " REQUIRED"
                        default_str = f" default={ps['default']}" if ps["has_default"] else ""
                        ann_warn = " ⚠" if not ps["annotated"] else ""
                        print(
                            f"  {ps['name']:20} {ps['kind']:12}"
                            f" {ps['annotation']:20}{default_str}{required}{ann_warn}"
                        )
                    print()
                    print("Full Docstring:")
                    print(_replace_prog_placeholder(matched['docstring']))
                else:
                    print(
                        f"Expression '{example_name}' not found in module '{module_name}'",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                return

            if not expressions:
                print(f"No named expressions found in module: {module_name}")
                return

            print(f"Module: {module_name}")
            print(f"{'Name':<30} {'Tags':<16} {'Parameters':<36} {'Brief':<30}")
            print("-" * 112)
            unannotated_count = 0
            for q in expressions:
                tags = ",".join(q.get("tags", ["?"]))
                params_str = q["signature"].replace("dialect, ", "").replace("(dialect)", "")
                brief = q["brief"][:27] + "..." if len(q["brief"]) > 30 else q["brief"]
                print(f"{q['name']:<30} [{tags:<12}] {params_str:<36} {brief:<30}")

                # Count unannotated params
                for ps in q.get("param_specs", []):
                    if not ps["annotated"]:
                        unannotated_count += 1

            # Print legend
            seen_tags = set()
            for q in expressions:
                for tag in q.get("tags", []):
                    seen_tags.add(tag)
            if seen_tags:
                print("---")
                legend_parts = []
                for tag in sorted(seen_tags):
                    if tag in FLAG_LEGEND:
                        legend_parts.append(f"{tag}={FLAG_LEGEND[tag]}")
                if legend_parts:
                    print("Tags: " + ", ".join(legend_parts))

            if unannotated_count > 0:
                print()
                print(f"Warning: {unannotated_count} parameter(s) without type annotations.")
                print("  Add type hints to suppress this warning.")

        except NamedExpressionError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # --describe mode
    if args.describe:
        if not qualified_name:
            print("Error: qualified name required for --describe.", file=sys.stderr)
            sys.exit(1)
        try:
            resolver = NamedExpressionResolver(qualified_name).load()
            info = resolver.describe()
            print(f"Expression: {info['qualified_name']}")
            print(f"Docstring: {info['docstring']}")
            print(f"Signature: {info['signature']}")
            print("Parameters (excluding 'dialect'):")
            param_specs = resolver.get_param_specs()
            for ps in param_specs:
                default_str = f" default={ps['default']}" if ps["has_default"] else ""
                required = "" if ps["has_default"] else " REQUIRED"
                ann_warn = " ⚠" if not ps["annotated"] else ""
                print(f"  {ps['name']:20} {ps['kind']:12} {ps['annotation']:20}{default_str}{required}{ann_warn}")
        except NamedExpressionError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Execute mode (requires qualified_name)
    if not qualified_name:
        print(
            "Error: qualified name required. Use --list to list available expressions.",
            file=sys.stderr,
        )
        sys.exit(1)

    user_params = parse_params(args.params)
    backend = None
    is_async = getattr(args, "is_async", False)

    if is_async and not backend_async_factory:
        print(
            "Error: --async requires asynchronous backend support. "
            "Please provide async backend factory.",
            file=sys.stderr,
        )
        sys.exit(1)

    async def run_async():
        backend = None
        try:
            backend = backend_async_factory()
            dialect = get_dialect_async(backend)
            resolver = NamedExpressionResolver(qualified_name).load()
            expression = resolver.execute(dialect, user_params)

            if args.dry_run:
                if not isinstance(expression, Executable):
                    print(f"[DRY RUN] Expression type: {type(expression).__name__} (not executable)")
                    print(f"Tags: {_classify_expression(expression)}")
                else:
                    sql, params = expression.to_sql()
                    print("[DRY RUN] SQL:")
                    print(f"  {sql}")
                    print(f"Params: {params}")
                return

            _execute_expression(
                expression,
                args,
                lambda sql, params, stmt_type: execute_query_async(sql, params, stmt_type),
                provider,
            )

        except NamedExpressionError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            from rhosocial.activerecord.backend.errors import ConnectionError, QueryError

            if isinstance(e, ConnectionError):
                provider.display_connection_error(e)
            elif isinstance(e, QueryError):
                provider.display_query_error(e)
            else:
                provider.display_unexpected_error(e, is_async=True)
            sys.exit(1)
        finally:
            if disconnect_async and backend:
                await disconnect_async()

    if is_async:
        import asyncio
        asyncio.run(run_async())
        return

    try:
        backend = backend_factory()
        dialect = get_dialect(backend)
        resolver = NamedExpressionResolver(qualified_name).load()
        expression = resolver.execute(dialect, user_params)

        if args.dry_run:
            if not isinstance(expression, Executable):
                print(f"[DRY RUN] Expression type: {type(expression).__name__} (not executable)")
            else:
                sql, params = expression.to_sql()
                print("[DRY RUN] SQL:")
                print(f"  {sql}")
                print(f"Params: {params}")
            return

        _execute_expression(expression, args, execute_query, provider)

    except NamedExpressionError as e:
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


def _classify_expression(expression: Any) -> str:
    """Classify an expression for display purposes."""
    if not isinstance(expression, Executable):
        return "CLAUSE"
    st = expression.statement_type
    tag_map = [
        ({StatementType.DQL, StatementType.SELECT}, "DQL"),
        ({StatementType.DML, StatementType.INSERT, StatementType.UPDATE,
          StatementType.DELETE, StatementType.MERGE, StatementType.TRUNCATE}, "DML"),
        ({StatementType.DDL}, "DDL"),
        ({StatementType.TCL}, "TCL"),
        ({StatementType.CALL, StatementType.EXECUTE}, "CALL"),
        ({StatementType.EXPLAIN}, "EXPLAIN"),
    ]
    return next((lbl for types, lbl in tag_map if st in types), "OTHER")
