# src/rhosocial/activerecord/backend/named_query/cli_procedure.py
"""
CLI utilities for named procedure functionality.

This module provides reusable functions to add named-procedure subcommand
to various CLI tools (like sqlite backend CLI). It handles the complete
lifecycle of named procedure execution from the command line.

Features:
    - Execute named procedures by qualified name
    - List all procedures in a module
    - Show procedure description and parameters
    - Dry-run mode to preview execution plan
    - Transaction mode configuration (auto/step/none)
    - Async execution support

Named Procedure CLI Subcommand:
    The CLI provides a 'named-procedure' subcommand with the following options:

    positional arguments:
        qualified_name: Fully qualified Python name (module.path.ClassName)

    optional arguments:
        --param KEY=VALUE: Procedure parameter (repeatable)
        --describe: Show signature without executing
        --dry-run: Print execution plan without executing
        --list: List all procedures in module
        --transaction: Transaction mode (auto/step/none)

Usage Example:
    >>> # Execute a named procedure
    >>> %(prog)s myapp.procedures.monthly_report --db-file mydb.sqlite --param month=2026-03

    >>> # List available procedures
    >>> %(prog)s myapp.procedures --list

    >>> # Show procedure details
    >>> %(prog)s myapp.procedures.monthly_report --describe

    >>> # Dry-run
    >>> %(prog)s myapp.procedures.monthly_report --db-file mydb.sqlite --dry-run --param month=2026-03

Note:
    This is a backend CLI feature. It is independent of ActiveRecord
    or ActiveQuery and is designed for CLI-based procedure execution.
"""
import argparse
import importlib
import inspect
import sys
from typing import Any, Callable, List, Optional

from .exceptions import NamedQueryError
from .procedure import LogEntry, ProcedureRunner, TransactionMode


def _replace_prog_placeholder(docstring: str, prog: str = None) -> str:
    """Replace %(prog)s and %%(prog)s placeholders with actual program name."""
    if prog is None:
        prog = "python -m rhosocial.activerecord.backend.impl.sqlite"
    return docstring.replace("%(prog)s", prog).replace("%%(prog)s", prog)


def list_named_procedures_in_module(module_name: str) -> List[dict]:
    """List all classes in a module that inherit from Procedure.

    Args:
        module_name: The module name to scan.

    Returns:
        List of procedure info dicts.
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise NamedQueryError(f"Module not found: {module_name}. {e}")

    from .procedure import Procedure

    results = []
    for name in dir(module):
        if name.startswith("_"):
            continue

        obj = getattr(module, name, None)
        if obj is None:
            continue

        if isinstance(obj, type) and issubclass(obj, Procedure) and obj is not Procedure:
            doc = inspect.getdoc(obj) or ""
            brief = doc.split("\n")[0].strip() if doc else ""

            params = obj.get_parameters()
            param_lines = []
            for pname, pinfo in params.items():
                ann = pinfo["annotation"]
                default = pinfo.get("default")
                if pinfo["has_default"]:
                    param_lines.append(f"{pname}: {ann} = {default}")
                else:
                    param_lines.append(f"{pname}: {ann} (required)")

            results.append(
                {
                    "name": name,
                    "class_name": name,
                    "signature": f"({', '.join(param_lines)})",
                    "docstring": doc,
                    "brief": brief,
                }
            )

    return results


def create_named_procedure_parser(
    subparsers: argparse._SubParsersAction,
    parent_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """Create the named-procedure subcommand parser.

    Args:
        subparsers: The subparsers action from the main parser.
        parent_parser: Parent parser with common arguments.

    Returns:
        The created parser for named-procedure subcommand.
    """
    np_parser = subparsers.add_parser(
        "named-procedure",
        help="Execute a named procedure defined as a Python class",
        parents=[parent_parser],
        epilog="""Examples:
  # Execute named procedure with params
  %(prog)s myapp.procedures.monthly_report --db-file mydb.sqlite --param month=2026-03

  # Show signature without executing
  %(prog)s myapp.procedures.monthly_report --describe

  # Preview execution plan
  %(prog)s myapp.procedures.monthly_report --db-file mydb.sqlite --dry-run --param month=2026-03

  # List all procedures in a module
  %(prog)s myapp.procedures --list

  # Execute with step transaction mode
  %(prog)s myapp.procedures.monthly_report --db-file mydb.sqlite --param month=2026-03 --transaction step

  # Async execution
  %(prog)s myapp.procedures.monthly_report --db-file mydb.sqlite --param month=2026-03 --async
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    np_parser.add_argument(
        "qualified_name",
        help="Fully qualified Python module path or name",
    )
    np_parser.add_argument(
        "--param",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        dest="params",
        help="Procedure parameter. Can be specified multiple times.",
    )
    np_parser.add_argument(
        "--describe",
        action="store_true",
        help="Show signature and docstring without executing.",
    )
    np_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the execution plan without executing.",
    )
    np_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_procedures",
        help="List all discoverable named procedures in the given module.",
    )
    np_parser.add_argument(
        "--transaction",
        dest="transaction",
        default="auto",
        choices=["auto", "step", "none"],
        help="Transaction mode: auto (default), step (commit each step), none (no transaction)",
    )
    np_parser.add_argument(
        "--async",
        dest="is_async",
        action="store_true",
        help="Use asynchronous execution (requires aiosqlite package).",
    )
    return np_parser


def handle_named_procedure(
    args: Any,
    provider: Any,
    backend_factory: Callable[[], Any],
    get_dialect: Callable[[Any], Any],
    execute_query: Callable[[str, tuple, Any], Any],
    disconnect: Optional[Callable[[], None]] = None,
    backend_async_factory: Optional[Callable[[], Any]] = None,
    get_dialect_async: Optional[Callable[[Any], Any]] = None,
    execute_query_async: Optional[Callable[[str, tuple, Any], Any]] = None,
    disconnect_async: Optional[Callable[[], None]] = None,
) -> None:
    """Handle named-procedure subcommand execution.

    Args:
        args: Parsed command-line arguments namespace.
        provider: Output provider for displaying results.
        backend_factory: Callable that returns a connected backend.
        get_dialect: Callable that receives backend and returns dialect.
        execute_query: Callable that executes (sql, params, stmt_type).
        disconnect: Optional callable to disconnect backend.
        backend_async_factory: Optional async backend factory.
        get_dialect_async: Optional async dialect getter.
        execute_query_async: Optional async query executor.
        disconnect_async: Optional async disconnect.

    Returns:
        None. Handles all output and exit codes.

    Raises:
        SystemExit: With code 1 on error.
    """
    qualified_name = args.qualified_name

    if args.list_procedures:
        try:
            importlib.invalidate_caches()

            module_name = qualified_name

            if "." in qualified_name:
                parts = qualified_name.rsplit(".", 1)
                potential_module = parts[0]
                potential_class = parts[1]
                try:
                    test_module = importlib.import_module(potential_module)
                    if hasattr(test_module, potential_class):
                        module_name = potential_module
                except (ModuleNotFoundError, ImportError):
                    pass

            procedures = list_named_procedures_in_module(module_name)

            if not procedures:
                print(f"No named procedures found in module: {module_name}")
                return

            print(f"Module: {module_name}")
            print(f"{'Name':<30} {'Parameters':<50} {'Brief':<20}")
            print("-" * 100)
            for p in procedures:
                params = p["signature"][:47] + "..." if len(p["signature"]) > 50 else p["signature"]
                brief = p["brief"][:17] + "..." if len(p["brief"]) > 20 else p["brief"]
                print(f"{p['name']:<30} {params:<50} {brief:<20}")

        except NamedQueryError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.describe:
        try:
            runner = ProcedureRunner(qualified_name).load()
            info = runner.describe()
            print(f"Procedure: {info['qualified_name']}")
            print(f"Class: {info['class_name']}")
            print(f"Docstring: {info['docstring']}")
            print("Parameters:")
            for pname, pinfo in info["parameters"].items():
                default_str = f" = {pinfo['default']}" if pinfo["has_default"] else " (required)"
                print(f"  {pname} {pinfo['annotation']}{default_str}")
        except NamedQueryError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    user_params = {}
    for param in args.params:
        if "=" in param:
            key, value = param.split("=", 1)
            user_params[key] = value

    is_async = getattr(args, "is_async", False)
    transaction_mode = TransactionMode(args.transaction)

    if is_async and not backend_async_factory:
        print(
            "Error: --async requires asynchronous backend support.",
            file=sys.stderr,
        )
        sys.exit(1)

    async def run_async():
        backend = None
        try:
            backend = backend_async_factory()
            dialect = get_dialect_async(backend)
            runner = ProcedureRunner(qualified_name).load()

            if args.dry_run:
                info = runner.describe()
                print("[DRY RUN] Procedure:")
                print(f"  {info['qualified_name']}")
                print("Parameters:")
                for pname, value in user_params.items():
                    print(f"  {pname} = {value}")
                print(f"Transaction mode: {transaction_mode.value}")
                return

            from .procedure import ProcedureResult

            result: ProcedureResult = runner.run(
                dialect, user_params, transaction_mode
            )

            if result.logs:
                print("Logs:")
                for log in result.logs:
                    print(f"  [{log.level}] {log.message}")

            for output in result.outputs:
                print(f"\nOutput: {output.get('qualified_name', 'unknown')}")
                if output.get("data"):
                    provider.display_results(output["data"], use_ascii=args.rich_ascii)

            if result.aborted:
                print(f"[ERROR] Procedure aborted: {result.abort_reason}", file=sys.stderr)
                sys.exit(1)

            print(f"[OK] Procedure completed. Outputs: {len(result.outputs)}, Logs: {len(result.logs)}")

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
                provider.display_unexpected_error(e, is_async=True)
            sys.exit(1)
        finally:
            if disconnect_async and backend:
                await disconnect_async()

    if is_async:
        import asyncio
        asyncio.run(run_async())
        return

    backend = None
    try:
        backend = backend_factory()
        dialect = get_dialect(backend)
        runner = ProcedureRunner(qualified_name).load()

        if args.dry_run:
            info = runner.describe()
            print("[DRY RUN] Procedure:")
            print(f"  {info['qualified_name']}")
            print("Parameters:")
            for pname, value in user_params.items():
                print(f"  {pname} = {value}")
            print(f"Transaction mode: {transaction_mode.value}")
            return

        from .procedure import ProcedureResult

        result: ProcedureResult = runner.run(dialect, user_params, transaction_mode)

        if result.logs:
            print("Logs:")
            for log in result.logs:
                print(f"  [{log.level}] {log.message}")

        for output in result.outputs:
            print(f"\nOutput: {output.get('qualified_name', 'unknown')}")
            if output.get("data"):
                provider.display_results(output["data"], use_ascii=args.rich_ascii)

        if result.aborted:
            print(f"[ERROR] Procedure aborted: {result.abort_reason}", file=sys.stderr)
            sys.exit(1)

        print(f"[OK] Procedure completed. Outputs: {len(result.outputs)}, Logs: {len(result.logs)}")

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