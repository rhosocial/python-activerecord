# src/rhosocial/activerecord/backend/impl/sqlite/__main__.py
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against a SQLite backend.", formatter_class=argparse.RawTextHelpFormatter
    )

    # =========================================================================
    # Design Notes:
    # =========================================================================
    # Uses explicit subcommand mode: query and introspect are mutually exclusive.
    # This avoids argparse misidentifying SQL queries as subcommand names.
    #
    # Connection parameters (--db-file) and output parameters (--output, --log-level, --rich-ascii)
    # are shared between both subcommands, so they are placed in the parent parser.
    #
    # --info is a global option that doesn't require a subcommand, so subcommands are not required=True.
    # =========================================================================

    # Parent parser: shared arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--db-file",
        default=None,
        help=("Path to the SQLite database file. If not provided, an in-memory database will be used."),
    )
    parent_parser.add_argument(
        "-o", "--output",
        choices=["table", "json", "csv", "tsv"],
        default="table",
        help='Output format. Defaults to "table" if rich is installed.',
    )
    parent_parser.add_argument("--log-level", default="INFO", help="Set logging level (e.g., DEBUG, INFO)")
    parent_parser.add_argument("--rich-ascii", action="store_true", help="Use ASCII characters for rich table borders.")

    # Global options (no subcommand required)
    parser.add_argument("--info", action="store_true", help="Display SQLite environment information.")
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Increase verbosity. -v for families, -vv for details."
    )

    # Subcommands: query and introspect
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # query subcommand
    query_parser = subparsers.add_parser("query", help="Execute SQL query", parents=[parent_parser])
    query_parser.add_argument(
        "sql", nargs="?", default=None, help="SQL query to execute. If not provided, reads from --file."
    )
    query_parser.add_argument("-f", "--file", default=None, help="Path to a file containing SQL to execute.")
    query_parser.add_argument("--executescript", action="store_true", help="Execute the input as a multi-statement script.")

    # introspect subcommand
    introspect_parser = subparsers.add_parser("introspect", help="Database introspection", parents=[parent_parser])
    introspect_parser.add_argument(
        "type",
        choices=INTROSPECT_TYPES,
        help="Introspection type: tables, views, table, columns, indexes, foreign-keys, triggers, database"
    )
    introspect_parser.add_argument("name", nargs="?", help="Table/view name (required for some types)")
    introspect_parser.add_argument("--include-system", action="store_true", help="Include system tables")

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


def display_info(verbose: int = 0, output_format: str = "table"):
    """Display SQLite environment information."""
    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(connection_config=config)

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
            print(f"Error: Failed to connect to in-memory database: {e}")
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
        "protocols": _build_protocol_info(dialect, verbose),
    }

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
        _display_info_rich(info_legacy, verbose, sqlite_version)

    return info


def _display_info_rich(info: Dict, verbose: int, sqlite_version: str):
    """Display info using rich console."""
    from rich.console import Console

    console = Console(force_terminal=True)

    SYM_OK = "[OK]"
    SYM_PARTIAL = "[~]"
    SYM_FAIL = "[X]"

    console.print("\n[bold cyan]SQLite Environment Information[/bold cyan]\n")

    console.print(f"[bold]SQLite Version:[/bold] {sqlite_version}\n")

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


def main():
    args = parse_args()

    # Handle --info flag (global option, no subcommand needed)
    if args.info:
        output_format = args.output if args.output != "table" or RICH_AVAILABLE else "json"
        display_info(verbose=args.verbose, output_format=output_format)
        return

    # Require a subcommand if --info is not specified
    if args.command is None:
        print("Error: Please specify a command: 'query' or 'introspect'", file=sys.stderr)
        print("Use --help for more information.", file=sys.stderr)
        sys.exit(1)

    # Handle introspect subcommand
    if args.command == "introspect":
        provider = get_provider(args)
        handle_introspect(args, provider)
        return

    # Handle query subcommand
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    provider = get_provider(args)

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
