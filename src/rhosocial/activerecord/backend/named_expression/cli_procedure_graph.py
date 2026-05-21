# src/rhosocial/activerecord/backend/named_expression/cli_procedure_graph.py
"""
CLI utilities for named procedure-graph functionality.

This module provides reusable functions to add named-procedure-graph subcommand
to various CLI tools (like sqlite backend CLI).

Features:
    - Execute named procedure graphs by qualified name
    - List all procedure graphs in a module
    - Show graph structure (waves and dependencies)
    - Validate graph (check for cycles, unknown deps)
    - Dry-run mode to preview execution plan
    - Async execution support
    - Rich table output

Named Procedure Graph CLI Subcommand:
    The CLI provides a 'named-procedure-graph' subcommand:

    positional arguments:
        qualified_name: Fully qualified Python name (module.path.func)

    optional arguments:
        --params JSON: Graph parameters as JSON
        --describe: Show graph structure without executing
        --dry-run: Print execution plan without executing
        --list: List all procedure graphs in module
        --validate: Validate graph (check errors)
        --waves: Show wave decomposition
        --format: Output format (json/table/text)
        --async: Use asynchronous execution

Usage Example:
    >>> # Execute a named procedure graph
    >>> %(prog)s myapp.procedures.monthly_report --db-file mydb.sqlite --params '{"month": "2026-03"}'

    >>> # List available procedure graphs
    >>> %(prog)s myapp.procedures --list

    >>> # Show graph structure
    >>> %(prog)s myapp.procedures.monthly_report --describe

    >>> # Validate graph
    >>> %(prog)s myapp.procedures.monthly_report --validate

    >>> # Dry-run
    >>> %(prog)s myapp.procedures.monthly_report --db-file mydb.sqlite --dry-run --params '{"month": "2026-03"}'

Note:
    This is a backend CLI feature.
"""
import argparse
import importlib
import inspect
import json
import sys
from typing import Any, Callable, List, Optional

from .exceptions import NamedExpressionError
from .graph_resolver import (
    NamedProcedureGraphResolver,
    list_procedure_graphs_in_module,
)
from .graph_runner import (
    AsyncProcedureGraphRunner,
    ProcedureGraphRunner,
)
from .procedure_graph import TransactionMode


def _replace_prog_placeholder(docstring: str, prog: str = None) -> str:
    """Replace %(prog)s and %%prog) placeholders with actual program name."""
    if prog is None:
        prog = "python -m rhosocial.activerecord.backend.impl.sqlite"
    return docstring.replace("%(prog)s", prog).replace("%%(prog)s", prog)


def create_named_procedure_graph_parser(
    subparsers: argparse._SubParsersAction,
    parent_parser: argparse.ArgumentParser,
    epilog: str = None,
) -> argparse.ArgumentParser:
    """Create the named-procedure-graph subcommand parser.

    Args:
        subparsers: The subparsers action from the main parser.
        parent_parser: Parent parser with common arguments.
        epilog: Custom examples text.

    Returns:
        The created parser for named-procedure-graph subcommand.
    """
    if epilog is None:
        epilog = """Examples:
  # Execute named procedure graph with params
  %(prog)s myapp.npg.monthly_report --db-file mydb.sqlite --params '{"month": "2026-03"}'

  # Show graph structure (waves)
  %(prog)s myapp.npg.monthly_report --describe

  # Validate graph
  %(prog)s myapp.npg.monthly_report --validate

  # Preview execution plan
  %(prog)s myapp.npg.monthly_report --db-file mydb.sqlite --dry-run --params '{"month": "2026-03"}'

  # List all procedure graphs in a module
  %(prog)s myapp.npg --list
"""
    npg_parser = subparsers.add_parser(
        "named-procedure-graph",
        help="Execute a named procedure graph",
        parents=[parent_parser],
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_named_procedure_graph_arguments(npg_parser)
    return npg_parser


def _add_named_procedure_graph_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for named-procedure-graph parser."""
    parser.add_argument(
        "qualified_name",
        help="Fully qualified Python module path or name",
    )
    parser.add_argument(
        "--params",
        dest="params_json",
        default="{}",
        help="Graph parameters as JSON string. Example: '{\"month\": \"2026-04\"}'",
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        dest="describe",
        help="Show graph structure (waves, dependencies) without executing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print execution plan without executing.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_procedure_graphs",
        help="List all procedure graphs in module.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        dest="validate",
        help="Validate graph (check for cycles, unknown deps).",
    )
    parser.add_argument(
        "--waves",
        action="store_true",
        dest="show_waves",
        help="Show wave decomposition (debug).",
    )
    parser.add_argument(
        "--format",
        dest="format",
        default="text",
        choices=["json", "table", "text"],
        help="Output format.",
    )
    parser.add_argument(
        "--async",
        dest="is_async",
        action="store_true",
        help="Use asynchronous execution.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        dest="trace",
        help="Output execution trace.",
    )


def handle_named_procedure_graph(
    args: Any,
    provider: Any,
    backend_factory: Callable[[], Any],
    disconnect: Optional[Callable[[], None]] = None,
    backend_async_factory: Optional[Callable[[], Any]] = None,
    disconnect_async: Optional[Callable[[], None]] = None,
) -> None:
    """Handle named-procedure-graph subcommand execution.

    Args:
        args: Parsed command-line arguments.
        provider: Output provider (rich table).
        backend_factory: Callable returning connected backend.
        disconnect: Optional callable to disconnect backend.
        backend_async_factory: Optional async backend factory.
        disconnect_async: Optional async disconnect.

    Returns:
        None. Handles all output and exit codes.
    """
    qualified_name = args.qualified_name

    if args.list_procedure_graphs:
        _handle_list(qualified_name, provider)
        return

    if args.validate:
        _handle_validate(qualified_name, provider)
        return

    if args.describe or args.show_waves:
        _handle_describe(qualified_name, provider, args.show_waves)
        return

    params = _parse_json_arg(args.params_json)
    backend = None

    try:
        backend = backend_factory()
        dialect = backend.dialect

        resolver = NamedProcedureGraphResolver(qualified_name)
        resolver.load()

        if args.describe:
            _show_graph_structure(resolver, dialect, params, provider)
            return

        if args.dry_run:
            runner = ProcedureGraphRunner(backend, dialect=dialect, dry_run=True)
        elif args.is_async:
            if not backend_async_factory:
                print("Error: Async backend not available", file=sys.stderr)
                sys.exit(1)
            async_backend = backend_async_factory()
            runner = AsyncProcedureGraphRunner(
                async_backend,
                dialect=dialect,
                dry_run=args.dry_run,
                trace=args.trace,
            )
            try:
                import asyncio
                graph = resolver.build(dialect, params)
                result = asyncio.run(runner.run(graph, params))
            finally:
                if disconnect_async:
                    disconnect_async()
            _print_result(result, provider, args.format)
            return
        else:
            runner = ProcedureGraphRunner(
                backend,
                dialect=dialect,
                dry_run=args.dry_run,
                trace=args.trace,
            )

        graph = resolver.build(dialect, params)
        result = runner.run(graph, params)
        _print_result(result, provider, args.format)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if backend and disconnect:
            disconnect()


def _handle_list(qualified_name: str, provider: Any) -> None:
    """Handle --list subcommand."""
    importlib.invalidate_caches()

    module_name = qualified_name

    if "." in qualified_name:
        parts = qualified_name.rsplit(".", 1)
        potential_module = parts[0]
        try:
            test_module = importlib.import_module(potential_module)
            if hasattr(test_module, parts[1]):
                module_name = potential_module
        except (ModuleNotFoundError, ImportError):
            pass

    try:
        graphs = list_procedure_graphs_in_module(module_name)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not graphs:
        print(f"No procedure graphs found in module: {module_name}")
        return

    rows = [
        {
            "name": g["name"],
            "signature": g["signature"],
            "brief": g["brief"],
        }
        for g in graphs
    ]

    provider.print_table(
        rows=rows,
        title="Procedure Graphs",
        columns=["name", "signature", "brief"],
    )


def _handle_validate(qualified_name: str, provider: Any) -> None:
    """Handle --validate subcommand."""
    try:
        resolver = NamedProcedureGraphResolver(qualified_name).load()
    except Exception as e:
        print(f"Error loading: {e}", file=sys.stderr)
        sys.exit(1)

    from rhosocial.activerecord.backend.dialect.base import SQLDialectBase

    class DummyDialect(SQLDialectBase):
        pass

    graph = resolver.build(DummyDialect(), None)
    errors = graph.validate()

    if not errors:
        print("Graph validation passed: No errors found.")
    else:
        print("Validation errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)


def _handle_describe(qualified_name: str, provider: Any, show_waves: bool = False) -> None:
    """Handle --describe subcommand."""
    try:
        resolver = NamedProcedureGraphResolver(qualified_name).load()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    desc = resolver.describe()
    print(f"Procedure Graph: {desc['qualified_name']}")
    print(f"Docstring: {desc['docstring'] or '(no docstring)'}")
    print(f"Signature: {desc['signature']}")

    if show_waves:
        from rhosocial.activerecord.backend.dialect.base import SQLDialectBase

        class DummyDialect(SQLDialectBase):
            pass

        graph = resolver.build(DummyDialect(), None)
        print(f"\nWaves (topological layers):")
        for i, wave in enumerate(graph.waves()):
            wave_names = [n.name for n in wave]
            print(f"  Wave {i}: {wave_names}")


def _show_graph_structure(
    resolver: NamedProcedureGraphResolver,
    dialect: Any,
    params: dict,
    provider: Any,
) -> None:
    """Show graph structure details."""
    graph = resolver.build(dialect, params)
    desc = resolver.describe()

    print(f"Procedure Graph: {desc['qualified_name']}")

    if desc["docstring"]:
        print(f"Description: {desc['docstring']}")

    print(f"\nTransaction mode: {graph.transaction_mode.name}")
    print(f"Strict: {graph.strict}")

    waves = graph.waves()
    print(f"\nWaves ({len(waves)}):")

    for i, wave in enumerate(waves):
        is_parallel = len(wave) > 1
        parallel_str = " (parallel)" if is_parallel else ""
        print(f"  Wave {i}{parallel_str}:")

        for node in wave:
            deps = f" depends_on={node.depends_on}" if node.depends_on else ""
            print(f"    [{node.name}] {node.label or node.named_query}{deps}")

            if node.condition:
                print(f"           condition: {node.condition}")


def _print_result(result: Any, provider: Any, format: str) -> None:
    """Print execution result."""
    if format == "json":
        print(result.to_json())
        return

    print(result.to_table())


def _parse_json_arg(json_str: str) -> dict:
    """Parse JSON string argument."""
    try:
        return json.loads(json_str) if json_str else {}
    except json.JSONDecodeError as e:
        print(f"Error parsing --params: {e}", file=sys.stderr)
        sys.exit(1)