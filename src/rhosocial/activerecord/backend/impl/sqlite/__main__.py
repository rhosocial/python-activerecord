# src/rhosocial/activerecord/backend/impl/sqlite/__main__.py
"""
SQLite backend command-line interface.

Provides SQL execution and database introspection capabilities.
"""
import argparse
import inspect
import json
import logging
import sys
import time
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Dict, List, Any

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.output import JsonOutputProvider, CsvOutputProvider, TsvOutputProvider
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.impl.sqlite.extension import get_registry
from rhosocial.activerecord.backend.impl.sqlite.pragma import get_all_pragma_infos, PragmaCategory
from rhosocial.activerecord.backend.impl.sqlite.protocols import SQLiteExtensionSupport, SQLitePragmaSupport
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport,
    CTESupport,
    ReturningSupport,
    UpsertSupport,
    LateralJoinSupport,
    JoinSupport,
    JSONSupport,
    ExplainSupport,
    GraphSupport,
    FilterClauseSupport,
    SetOperationSupport,
    ViewSupport,
    TableSupport,
    TruncateSupport,
    GeneratedColumnSupport,
    TriggerSupport,
    FunctionSupport,
    # Additional protocols for complete coverage
    AdvancedGroupingSupport,
    ArraySupport,
    ILIKESupport,
    IndexSupport,
    LockingSupport,
    MergeSupport,
    OrderedSetAggregationSupport,
    QualifyClauseSupport,
    SchemaSupport,
    SequenceSupport,
    TemporalTableSupport,
)
from rhosocial.activerecord.backend.introspection.status import StatusCategory

try:
    from rich.logging import RichHandler
    from rhosocial.activerecord.backend.output_rich import RichOutputProvider

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    RichOutputProvider = None  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)

# Groups that are specific to SQLite dialect
DIALECT_SPECIFIC_GROUPS = {"SQLite-specific"}

PROTOCOL_FAMILY_GROUPS: Dict[str, list] = {
    "Query Features": [
        WindowFunctionSupport,
        CTESupport,
        FilterClauseSupport,
        SetOperationSupport,
        AdvancedGroupingSupport,
    ],
    "JOIN Support": [JoinSupport, LateralJoinSupport],
    "Data Types": [JSONSupport, ArraySupport],
    "DML Features": [
        ReturningSupport,
        UpsertSupport,
        MergeSupport,
        OrderedSetAggregationSupport,
    ],
    "Transaction & Locking": [LockingSupport, TemporalTableSupport],
    "Query Analysis": [ExplainSupport, GraphSupport, QualifyClauseSupport],
    "DDL - Table": [TableSupport, TruncateSupport, GeneratedColumnSupport],
    "DDL - View": [ViewSupport],
    "DDL - Schema & Index": [SchemaSupport, IndexSupport],
    "DDL - Sequence & Trigger": [SequenceSupport, TriggerSupport, FunctionSupport],
    "String Matching": [ILIKESupport],
    "SQLite-specific": [
        SQLiteExtensionSupport,
        SQLitePragmaSupport,
    ],
}


def guess_statement_type(sql: str) -> StatementType:
    sql_stripped = sql.strip().upper()
    if sql_stripped.startswith(("SELECT", "WITH", "EXPLAIN", "PRAGMA")):
        return StatementType.DQL
    elif sql_stripped.startswith(("INSERT", "UPDATE", "DELETE")):
        return StatementType.DML
    elif sql_stripped.startswith(("CREATE", "ALTER", "DROP")):
        return StatementType.DDL
    else:
        return StatementType.OTHER


INTROSPECT_TYPES = [
    "tables", "views", "table", "columns",
    "indexes", "foreign-keys", "triggers", "database"
]

STATUS_TYPES = ["all", "config", "performance", "storage", "databases"]


def parse_args():
    # =========================================================================
    # Design Notes:
    # =========================================================================
    # Uses explicit subcommand mode: info, query, and introspect are subcommands.
    # This avoids argparse misidentifying SQL queries as subcommand names.
    #
    # Structure:
    # - Main parser: contains only global options (-v/--verbose)
    # - parent_parser: shared arguments for all subcommands
    # - Each subcommand parser inherits from parent_parser
    #
    # Usage: python -m backend.impl.sqlite <subcommand> [subcommand-options]
    # Example: python -m backend.impl.sqlite query --db-file test.db "SELECT 1"
    # =========================================================================

    # Parent parser: shared arguments for all subcommands
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--db-file",
        default=None,
        help="Path to the SQLite database file. If not provided, an in-memory database will be used.",
    )
    parent_parser.add_argument(
        "-o", "--output",
        choices=["table", "json", "csv", "tsv"],
        default="table",
        help='Output format. Defaults to "table" if rich is installed.',
    )
    parent_parser.add_argument(
        "--log-level",
        default="INFO",
        help="Set logging level (e.g., DEBUG, INFO)",
    )
    parent_parser.add_argument(
        "--rich-ascii",
        action="store_true",
        help="Use ASCII characters for rich table borders.",
    )

    # Main parser: global options only
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against a SQLite backend.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity. -v for families, -vv for details.",
    )

    # Subcommands: info, query, and introspect
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # info subcommand
    subparsers.add_parser(
        "info",
        help="Display SQLite environment information",
        parents=[parent_parser],
    )

    # query subcommand
    query_parser = subparsers.add_parser(
        "query",
        help="Execute SQL query",
        parents=[parent_parser],
    )
    query_parser.add_argument(
        "sql",
        nargs="?",
        default=None,
        help="SQL query to execute. If not provided, reads from --file.",
    )
    query_parser.add_argument(
        "-f", "--file",
        default=None,
        help="Path to a file containing SQL to execute.",
    )
    query_parser.add_argument(
        "--executescript",
        action="store_true",
        help="Execute the input as a multi-statement script.",
    )

    # introspect subcommand
    introspect_parser = subparsers.add_parser(
        "introspect",
        help="Database introspection",
        parents=[parent_parser],
        epilog="""Examples:
  # List all tables in database
  %(prog)s tables --db-file mydb.sqlite

  # List all views
  %(prog)s views --db-file mydb.sqlite

  # Get detailed table info (columns, indexes, foreign keys)
  %(prog)s table users --db-file mydb.sqlite

  # Get column details for a table
  %(prog)s columns users --db-file mydb.sqlite

  # Get index information
  %(prog)s indexes users --db-file mydb.sqlite

  # Get foreign key relationships
  %(prog)s foreign-keys users --db-file mydb.sqlite

  # List triggers
  %(prog)s triggers --db-file mydb.sqlite

  # Get database information
  %(prog)s database --db-file mydb.sqlite

  # Output as JSON
  %(prog)s tables --db-file mydb.sqlite -o json

  # Using in-memory database
  %(prog)s tables
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    introspect_parser.add_argument(
        "type",
        choices=INTROSPECT_TYPES,
        help="Introspection type: tables, views, table, columns, indexes, foreign-keys, triggers, database",
    )
    introspect_parser.add_argument(
        "name",
        nargs="?",
        help="Table/view name (required for some types)",
    )
    introspect_parser.add_argument(
        "--include-system",
        action="store_true",
        help="Include system tables",
    )

    # status subcommand
    status_parser = subparsers.add_parser(
        "status",
        help="Display server status overview",
        parents=[parent_parser],
        epilog="""Examples:
  # Show complete status overview
  %(prog)s all --db-file mydb.sqlite

  # Show configuration parameters only
  %(prog)s config --db-file mydb.sqlite

  # Show performance metrics only
  %(prog)s performance --db-file mydb.sqlite

  # Show storage information
  %(prog)s storage --db-file mydb.sqlite

  # Show attached databases
  %(prog)s databases --db-file mydb.sqlite

  # Output as JSON
  %(prog)s all --db-file mydb.sqlite -o json

  # Using in-memory database
  %(prog)s all
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    status_parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=STATUS_TYPES,
        help="Status type: all (default), config, performance, storage, databases",
    )

    return parser.parse_args()


def get_provider(args):
    """Factory function to get the correct output provider."""
    output_format = args.output
    if output_format == "table" and not RICH_AVAILABLE:
        output_format = "json"

    if output_format == "table" and RICH_AVAILABLE:
        from rich.console import Console

        return RichOutputProvider(console=Console(), ascii_borders=args.rich_ascii)
    if output_format == "json":
        return JsonOutputProvider()
    if output_format == "csv":
        return CsvOutputProvider()
    if output_format == "tsv":
        return TsvOutputProvider()

    return JsonOutputProvider()


def execute_query(sql_query: str, backend: SQLiteBackend, provider, **kwargs):
    try:
        backend.connect()
        provider.display_query(sql_query, is_async=False)

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
        provider.display_unexpected_error(e, is_async=False)
        sys.exit(1)
    finally:
        if backend._connection:
            backend.disconnect()
        provider.display_disconnect(is_async=False)


def execute_script(sql_script: str, backend: SQLiteBackend, provider):
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


def get_protocol_support_methods(protocol_class: type) -> List[str]:
    """Get all support check methods from a protocol class.

    Supports both 'supports_*' and 'is_*_available' naming patterns.
    """
    methods = []
    for name, member in inspect.getmembers(protocol_class):
        if callable(member) and (
            name.startswith("supports_") or name.startswith("is_") and name.endswith("_available")
        ):
            methods.append(name)
    return sorted(methods)


# All possible test arguments for methods that require parameters
# This allows detailed display of which specific arguments are supported
SUPPORT_METHOD_ALL_ARGS: Dict[str, List[str]] = {
    # ExplainSupport: all possible format types
    "supports_explain_format": ["TEXT", "JSON", "XML", "YAML", "TREE", "DOT"],
    # SQLiteExtensionSupport: common extensions
    "is_extension_available": [
        "fts5",
        "fts4",
        "fts3",
        "fts2",
        "fts1",
        "json1",
        "rtree",
        "geopoly",
        "dbstat",
        "fts5tokenize",
    ],
    # SQLitePragmaSupport: sample pragmas from each category
    "is_pragma_available": [
        "journal_mode",
        "synchronous",
        "cache_size",
        "temp_store",
        "foreign_keys",
        "busy_timeout",
        "wal_autocheckpoint",
    ],
}


def check_protocol_support(dialect: Any, protocol_class: type) -> Dict[str, Any]:
    """Check all support methods for a protocol against the dialect.

    Supports both 'supports_*' and 'is_*_available' naming patterns.
    For methods requiring parameters, tests all possible arguments.

    Returns:
        Dict with method names as keys. For no-arg methods: bool value.
        For methods with parameters: dict with 'supported', 'total', 'args' keys.
    """
    results = {}
    methods = get_protocol_support_methods(protocol_class)
    for method_name in methods:
        if hasattr(dialect, method_name):
            try:
                method = getattr(dialect, method_name)
                # Check if method requires arguments (beyond self)
                sig = inspect.signature(method)
                params = [p for p in sig.parameters.values() if p.default == inspect.Parameter.empty]
                required_params = [p for p in params if p.name != "self"]

                if len(required_params) == 0:
                    # No required parameters, call directly
                    result = method()
                    results[method_name] = bool(result)
                elif method_name in SUPPORT_METHOD_ALL_ARGS:
                    # Test all possible arguments
                    all_args = SUPPORT_METHOD_ALL_ARGS[method_name]
                    arg_results = {}
                    for arg in all_args:
                        try:
                            arg_results[arg] = bool(method(arg))
                        except Exception:
                            arg_results[arg] = False
                    supported_count = sum(1 for v in arg_results.values() if v)
                    results[method_name] = {"supported": supported_count, "total": len(all_args), "args": arg_results}
                else:
                    # Unknown method requiring parameters, skip
                    results[method_name] = False
            except Exception:
                results[method_name] = False
        else:
            results[method_name] = False
    return results


def _build_database_info(version_tuple: tuple) -> Dict[str, Any]:
    """Build database basic information structure."""
    return {
        "type": "sqlite",
        "version": ".".join(map(str, version_tuple)),
        "version_tuple": list(version_tuple),
    }


def _build_extension_info(version_tuple: tuple) -> Dict[str, Any]:
    """Build extension information structure."""
    registry = get_registry()
    extensions = registry.detect_extensions(version_tuple)
    ext_info = {}

    for name, ext in extensions.items():
        ext_info[name] = {
            "type": ext.extension_type.name,
            "available": ext.installed,
            "min_version": ".".join(map(str, ext.min_version)),
            "deprecated": ext.deprecated,
            "description": ext.description,
        }
        if ext.successor:
            ext_info[name]["successor"] = ext.successor
        if ext.installed:
            features = registry.get_supported_features(name, version_tuple)
            if features:
                ext_info[name]["features"] = features

    return ext_info


def _build_pragma_info() -> Dict[str, Any]:
    """Build pragma information structure."""
    pragma_info = {"total_count": len(get_all_pragma_infos()), "categories": {}}

    for category in PragmaCategory:
        pragmas_in_category = [name for name, p in get_all_pragma_infos().items() if p.category == category]
        pragma_info["categories"][category.name] = {"count": len(pragmas_in_category), "names": pragmas_in_category}

    return pragma_info


def _calculate_support_stats(support_methods: Dict[str, Any]) -> tuple:
    """Calculate supported/total counts from support methods.

    For no-arg methods: value is bool
    For methods with parameters: value is dict with 'supported', 'total', 'args'
    """
    supported_count = 0
    total_count = 0

    for value in support_methods.values():
        if isinstance(value, dict):
            supported_count += value["supported"]
            total_count += value["total"]
        else:
            total_count += 1
            if value:
                supported_count += 1

    return supported_count, total_count


def _build_protocol_info(dialect: Any, verbose: int) -> Dict[str, Any]:
    """Build protocol support information structure."""
    protocol_info = {}

    for group_name, protocols in PROTOCOL_FAMILY_GROUPS.items():
        protocol_info[group_name] = _build_protocol_group_info(dialect, protocols, verbose)

    return protocol_info


def _build_protocol_group_info(dialect: Any, protocols: list, verbose: int) -> Dict[str, Any]:
    """Build information for a single protocol group."""
    group_info = {}

    for protocol in protocols:
        protocol_name = protocol.__name__
        support_methods = check_protocol_support(dialect, protocol)
        supported_count, total_count = _calculate_support_stats(support_methods)

        percentage = round(supported_count / total_count * 100, 1) if total_count > 0 else 0

        group_info[protocol_name] = {
            "supported": supported_count,
            "total": total_count,
            "percentage": percentage,
        }

        if verbose >= 2:
            group_info[protocol_name]["methods"] = support_methods

    return group_info


def handle_info(args, provider):
    """Handle info subcommand.

    Display SQLite environment information based on actual database connection.
    SQLite always connects - either to a file database or in-memory database.
    """
    db_path = args.db_file if args.db_file else ":memory:"
    is_file_database = db_path != ":memory:"
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    output_format = args.output if args.output != "table" or RICH_AVAILABLE else "json"

    try:
        backend.connect()
        backend.introspect_and_adapt()
        dialect = backend.dialect
        version_tuple = dialect.version
        sqlite_version = ".".join(map(str, version_tuple))
    except Exception as e:
        if output_format == "json" or not RICH_AVAILABLE:
            print(json.dumps({"error": f"Failed to connect: {e}"}))
        else:
            print(f"Error: Failed to connect to database: {e}")
        return None
    finally:
        backend.disconnect()

    # Build info structure using helper functions
    info = {
        "database": _build_database_info(version_tuple),
        "features": {
            "extensions": _build_extension_info(version_tuple),
            "pragmas": _build_pragma_info(),
        },
        "protocols": _build_protocol_info(dialect, args.verbose),
    }

    # Add connection info
    info["database"]["database_type"] = "file" if is_file_database else "memory"
    info["database"]["database_path"] = db_path

    # Output result
    if output_format == "json" or not RICH_AVAILABLE:
        print(json.dumps(info, indent=2))
    else:
        # Use legacy structure for rich display
        info_legacy = {
            "sqlite": info["database"],
            "extensions": info["features"]["extensions"],
            "pragmas": info["features"]["pragmas"],
            "protocols": info["protocols"],
        }
        _display_info_rich(info_legacy, args.verbose, sqlite_version, is_file_database, db_path)

    return info


def _display_info_rich(
    info: Dict, verbose: int, sqlite_version: str, is_file_database: bool = True, db_path: str = ":memory:"
):
    """Display info using rich console.

    Args:
        info: Information dictionary containing database and protocol info
        verbose: Verbosity level for output detail
        sqlite_version: SQLite version string
        is_file_database: Whether using a file database (vs in-memory)
        db_path: Path to database file or ":memory:"
    """
    from rich.console import Console

    console = Console(force_terminal=True)

    SYM_OK = "[OK]"
    SYM_PARTIAL = "[~]"
    SYM_FAIL = "[X]"

    console.print("\n[bold cyan]SQLite Environment Information[/bold cyan]\n")

    # Show database type and version
    if is_file_database:
        console.print(f"[bold]SQLite Version:[/bold] {sqlite_version} [dim](file: {db_path})[/dim]\n")
    else:
        console.print(f"[bold]SQLite Version:[/bold] {sqlite_version} [yellow](in-memory database)[/yellow]\n")

    console.print("[bold green]Extension Support:[/bold green]")
    for name, ext in info["extensions"].items():
        status = "[green][OK][/green]" if ext["available"] else "[red][X][/red]"
        deprecated = " [yellow](deprecated)[/yellow]" if ext["deprecated"] else ""
        console.print(f"  {status} [bold]{name}[/bold]{deprecated}: {ext['description']}")
        if ext["available"] and "features" in ext:
            console.print(f"      [dim]Features: {', '.join(ext['features'])}[/dim]")

    console.print("\n[bold green]Pragma System:[/bold green]")
    console.print(f"  Total pragmas documented: {info['pragmas']['total_count']}")
    for cat_name, cat_info in info["pragmas"]["categories"].items():
        console.print(f"  [bold]{cat_name}:[/bold] {cat_info['count']} pragmas")

    label = "Detailed" if verbose >= 2 else "Family Overview"
    console.print(f"\n[bold green]Protocol Support ({label}):[/bold green]")

    for group_name, protocols in info["protocols"].items():
        # Mark dialect-specific groups
        if group_name in DIALECT_SPECIFIC_GROUPS:
            console.print(f"\n  [bold underline]{group_name}:[/bold underline] [dim](dialect-specific)[/dim]")
        else:
            console.print(f"\n  [bold underline]{group_name}:[/bold underline]")
        for protocol_name, stats in protocols.items():
            pct = stats["percentage"]
            if pct == 100:
                color = "green"
                symbol = SYM_OK
            elif pct >= 50:
                color = "yellow"
                symbol = SYM_PARTIAL
            elif pct > 0:
                color = "red"
                symbol = SYM_PARTIAL
            else:
                color = "red"
                symbol = SYM_FAIL

            bar_len = 20
            filled = int(pct / 100 * bar_len)
            bar = "#" * filled + "-" * (bar_len - filled)

            sup = stats["supported"]
            tot = stats["total"]
            console.print(
                f"    [{color}]{symbol}[/{color}] {protocol_name}: [{color}]{bar}[/{color}] {pct:.0f}% ({sup}/{tot})"
            )

            if verbose >= 2 and "methods" in stats:
                for method, value in stats["methods"].items():
                    method_display = (
                        method.replace("supports_", "").replace("_", " ").replace("is_", "").replace("_available", "")
                    )
                    if isinstance(value, dict):
                        # Method with parameters - show each arg's support
                        console.print(f"        [dim]{method_display}:[/dim]")
                        for arg, supported in value.get("args", {}).items():
                            m_status = "[green][OK][/green]" if supported else "[red][X][/red]"
                            console.print(f"            {m_status} {arg}")
                    else:
                        # No-arg method
                        m_status = "[green][OK][/green]" if value else "[red][X][/red]"
                        console.print(f"        {m_status} {method_display}")

    console.print()


def _serialize_for_output(obj):
    """Serialize object for JSON output, handling non-serializable types.

    Recursively converts dataclasses, Pydantic models, and Enums to
    JSON-serializable types.
    """
    # Handle None
    if obj is None:
        return None
    # Handle Pydantic models
    if hasattr(obj, 'model_dump'):
        try:
            result = obj.model_dump(mode='json')
            return _serialize_for_output(result)  # Recursively process the result
        except TypeError:
            result = obj.model_dump()
            return _serialize_for_output(result)
    # Handle dataclasses
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize_for_output(v) for k, v in asdict(obj).items()}
    # Handle Enums
    if isinstance(obj, Enum):
        return obj.value
    # Handle dicts
    if isinstance(obj, dict):
        return {k: _serialize_for_output(v) for k, v in obj.items()}
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_output(item) for item in obj]
    # Handle basic types
    if isinstance(obj, (str, int, float, bool)):
        return obj
    # Fallback: convert to string
    return str(obj)


def handle_introspect(args, provider):
    """Handle introspect subcommand."""
    db_path = args.db_file if args.db_file else ":memory:"
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    try:
        backend.connect()
        introspector = backend.introspector

        if args.type == "tables":
            tables = introspector.list_tables(include_system=args.include_system)
            data = [_serialize_for_output(t) for t in tables]
            provider.display_results(data, title="Tables")

        elif args.type == "views":
            views = introspector.list_views()
            data = [_serialize_for_output(v) for v in views]
            provider.display_results(data, title="Views")

        elif args.type == "table":
            if not args.name:
                print("Error: Table name is required for 'table' introspection", file=sys.stderr)
                sys.exit(1)
            info = introspector.get_table_info(args.name)
            if info:
                # Display columns
                columns_data = [_serialize_for_output(c) for c in info.columns]
                provider.display_results(columns_data, title=f"Columns of {args.name}")
                # Display indexes
                if info.indexes:
                    indexes_data = [_serialize_for_output(i) for i in info.indexes]
                    provider.display_results(indexes_data, title=f"Indexes of {args.name}")
                # Display foreign keys
                if info.foreign_keys:
                    fks_data = [_serialize_for_output(f) for f in info.foreign_keys]
                    provider.display_results(fks_data, title=f"Foreign Keys of {args.name}")
            else:
                print(f"Error: Table '{args.name}' not found", file=sys.stderr)
                sys.exit(1)

        elif args.type == "columns":
            if not args.name:
                print("Error: Table name is required for 'columns' introspection", file=sys.stderr)
                sys.exit(1)
            columns = introspector.list_columns(args.name)
            data = [_serialize_for_output(c) for c in columns]
            provider.display_results(data, title=f"Columns of {args.name}")

        elif args.type == "indexes":
            if not args.name:
                print("Error: Table name is required for 'indexes' introspection", file=sys.stderr)
                sys.exit(1)
            indexes = introspector.list_indexes(args.name)
            data = [_serialize_for_output(i) for i in indexes]
            provider.display_results(data, title=f"Indexes of {args.name}")

        elif args.type == "foreign-keys":
            if not args.name:
                print("Error: Table name is required for 'foreign-keys' introspection", file=sys.stderr)
                sys.exit(1)
            fks = introspector.list_foreign_keys(args.name)
            data = [_serialize_for_output(f) for f in fks]
            provider.display_results(data, title=f"Foreign Keys of {args.name}")

        elif args.type == "triggers":
            triggers = introspector.list_triggers(table_name=args.name)
            data = [_serialize_for_output(t) for t in triggers]
            provider.display_results(data, title="Triggers")

        elif args.type == "database":
            info = introspector.get_database_info()
            data = [_serialize_for_output(info)]
            provider.display_results(data, title="Database Info")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        backend.disconnect()


def handle_status(args, provider):
    """Handle status subcommand.

    Display SQLite server status overview.
    """
    db_path = args.db_file if args.db_file else ":memory:"
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    try:
        backend.connect()
        backend.introspect_and_adapt()

        status_introspector = backend.introspector.status
        status_type = args.type

        if status_type == "all":
            # Get complete overview
            status = status_introspector.get_overview()
            # Display complete overview
            if args.output == "json" or not RICH_AVAILABLE:
                print(json.dumps(status.to_dict(), indent=2))
            else:
                _display_status_rich(status, args.verbose)
        elif status_type == "config":
            config_items = status_introspector.list_configuration(StatusCategory.CONFIGURATION)
            data = [_serialize_for_output(item) for item in config_items]
            provider.display_results(data, title="Configuration")
        elif status_type == "performance":
            perf_items = status_introspector.list_configuration(StatusCategory.PERFORMANCE)
            data = [_serialize_for_output(item) for item in perf_items]
            provider.display_results(data, title="Performance")
        elif status_type == "storage":
            storage_info = status_introspector.get_storage_info()
            data = [_serialize_for_output(storage_info)]
            provider.display_results(data, title="Storage")
        elif status_type == "databases":
            databases = status_introspector.list_databases()
            data = [_serialize_for_output(db) for db in databases]
            provider.display_results(data, title="Databases")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        backend.disconnect()


def _display_status_rich(status, verbose: int = 0):
    """Display status using rich console.

    Args:
        status: ServerOverview object
        verbose: Verbosity level for output detail
    """
    from rich.console import Console
    from rich.table import Table

    console = Console(force_terminal=True)

    # Header
    console.print("\n[bold cyan]SQLite Server Status[/bold cyan]\n")
    console.print(f"[bold]Version:[/bold] {status.server_version}")
    console.print(f"[bold]Vendor:[/bold] {status.server_vendor}")

    # Storage info
    if status.storage.total_size_bytes is not None:
        size_str = _format_size(status.storage.total_size_bytes)
        console.print(f"[bold]Database Size:[/bold] {size_str}")

    console.print()

    # Configuration section
    config_items = [item for item in status.configuration
                    if item.category == StatusCategory.CONFIGURATION]
    if config_items:
        console.print("[bold green]Configuration[/bold green]")
        config_table = Table(show_header=True, header_style="bold")
        config_table.add_column("Parameter")
        config_table.add_column("Value")
        if verbose >= 1:
            config_table.add_column("Description")
            config_table.add_column("Readonly")

        for item in config_items:
            row = [item.name, str(item.value)]
            if verbose >= 1:
                row.extend([
                    item.description or "",
                    "Yes" if item.is_readonly else "No"
                ])
            config_table.add_row(*row)

        console.print(config_table)
        console.print()

    # Performance section
    perf_items = [item for item in status.configuration
                  if item.category == StatusCategory.PERFORMANCE]
    if perf_items:
        console.print("[bold green]Performance[/bold green]")
        perf_table = Table(show_header=True, header_style="bold")
        perf_table.add_column("Parameter")
        perf_table.add_column("Value")
        if verbose >= 1:
            perf_table.add_column("Unit")

        for item in perf_items:
            row = [item.name, str(item.value)]
            if verbose >= 1:
                row.append(item.unit or "")
            perf_table.add_row(*row)

        console.print(perf_table)
        console.print()

    # Storage section
    if status.storage.total_size_bytes is not None:
        console.print("[bold green]Storage[/bold green]")
        storage_table = Table(show_header=True, header_style="bold")
        storage_table.add_column("Metric")
        storage_table.add_column("Value")

        storage_table.add_row("Total Size", _format_size(status.storage.total_size_bytes))
        if status.storage.data_size_bytes is not None:
            storage_table.add_row("Data Size", _format_size(status.storage.data_size_bytes))

        console.print(storage_table)
        console.print()

    # Databases section
    if status.databases:
        console.print("[bold green]Databases[/bold green]")
        db_table = Table(show_header=True, header_style="bold")
        db_table.add_column("Name")
        db_table.add_column("Tables")
        if verbose >= 1:
            db_table.add_column("Path")

        for db in status.databases:
            row = [db.name, str(db.table_count or "N/A")]
            if verbose >= 1:
                row.append(db.extra.get("path", "N/A"))
            db_table.add_row(*row)

        console.print(db_table)
        console.print()


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def main():
    args = parse_args()

    # Require a subcommand
    if args.command is None:
        print("Error: Please specify a command: 'info', 'query', 'introspect', or 'status'", file=sys.stderr)
        print("Use --help for more information.", file=sys.stderr)
        sys.exit(1)

    provider = get_provider(args)

    # Handle info subcommand
    if args.command == "info":
        handle_info(args, provider)
        return

    # Handle introspect subcommand
    if args.command == "introspect":
        handle_introspect(args, provider)
        return

    # Handle status subcommand
    if args.command == "status":
        handle_status(args, provider)
        return

    # Handle query subcommand
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    if RICH_AVAILABLE and isinstance(provider, RichOutputProvider):
        from rich.console import Console

        handler = RichHandler(rich_tracebacks=True, show_path=False, console=Console(stderr=True))
        logging.basicConfig(level=numeric_level, format="%(message)s", datefmt="[%X]", handlers=[handler])
    else:
        logging.basicConfig(level=numeric_level, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stderr)

    provider.display_greeting()

    sql_source = None
    if args.sql:
        sql_source = args.sql
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                sql_source = f.read()
        except FileNotFoundError:
            logger.error(f"Error: File not found at {args.file}")
            sys.exit(1)
    elif not sys.stdin.isatty():
        sql_source = sys.stdin.read()

    if not sql_source:
        msg = "Error: No SQL query provided. Use a positional argument, the --file flag, or pipe from stdin."
        print(msg, file=sys.stderr)
        sys.exit(1)

    db_path = args.db_file if args.db_file else ":memory:"
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    if args.executescript:
        execute_script(sql_source, backend, provider)
    else:
        execute_query(sql_source, backend, provider, use_ascii=args.rich_ascii)


if __name__ == "__main__":
    main()
