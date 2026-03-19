# src/rhosocial/activerecord/backend/impl/sqlite/__main__.py
import argparse
import inspect
import json
import logging
import sys
import time
from typing import Dict, List, Any

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import (
    SQLiteConnectionConfig
)
from rhosocial.activerecord.backend.errors import ConnectionError, QueryError
from rhosocial.activerecord.backend.output import (
    JsonOutputProvider, CsvOutputProvider, TsvOutputProvider
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.impl.sqlite.extension import get_registry
from rhosocial.activerecord.backend.impl.sqlite.pragma import (
    get_all_pragma_infos, PragmaCategory
)
from rhosocial.activerecord.backend.impl.sqlite.protocols import (
    SQLiteExtensionSupport, SQLitePragmaSupport
)
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport, CTESupport,
    ReturningSupport, UpsertSupport, LateralJoinSupport, JoinSupport,
    JSONSupport, ExplainSupport, GraphSupport, FilterClauseSupport,
    SetOperationSupport, ViewSupport,
    TableSupport, TruncateSupport, GeneratedColumnSupport,
    TriggerSupport, FunctionSupport,
    # Additional protocols for complete coverage
    AdvancedGroupingSupport, ArraySupport, ILIKESupport,
    IndexSupport, LockingSupport, MergeSupport,
    OrderedSetAggregationSupport, QualifyClauseSupport,
    SchemaSupport, SequenceSupport, TemporalTableSupport,
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
        WindowFunctionSupport, CTESupport, FilterClauseSupport,
        SetOperationSupport, AdvancedGroupingSupport,
    ],
    "JOIN Support": [JoinSupport, LateralJoinSupport],
    "Data Types": [JSONSupport, ArraySupport],
    "DML Features": [
        ReturningSupport, UpsertSupport, MergeSupport,
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
        SQLiteExtensionSupport, SQLitePragmaSupport,
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Execute SQL queries against a SQLite backend.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'query',
        nargs='?',
        default=None,
        help='SQL query to execute. If not provided, reads from --file.'
    )
    parser.add_argument(
        '-f', '--file',
        default=None,
        help='Path to a file containing SQL to execute.'
    )
    parser.add_argument(
        '--db-file',
        default=None,
        help=('Path to the SQLite database file. '
              'If not provided, an in-memory database will be used.')
    )
    parser.add_argument(
        '--executescript',
        action='store_true',
        help='Execute the input as a multi-statement script.'
    )
    parser.add_argument(
        '--output',
        choices=['table', 'json', 'csv', 'tsv'],
        default='table',
        help='Output format. Defaults to "table" if rich is installed.'
    )
    parser.add_argument(
        '--log-level',
        default='INFO',
        help='Set logging level (e.g., DEBUG, INFO)'
    )
    parser.add_argument(
        '--rich-ascii',
        action='store_true',
        help='Use ASCII characters for rich table borders.'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Display SQLite environment information.'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity. -v for families, -vv for details.'
    )

    return parser.parse_args()


def get_provider(args):
    """Factory function to get the correct output provider."""
    output_format = args.output
    if output_format == 'table' and not RICH_AVAILABLE:
        output_format = 'json'

    if output_format == 'table' and RICH_AVAILABLE:
        from rich.console import Console
        return RichOutputProvider(
            console=Console(), ascii_borders=args.rich_ascii
        )
    if output_format == 'json':
        return JsonOutputProvider()
    if output_format == 'csv':
        return CsvOutputProvider()
    if output_format == 'tsv':
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
        if callable(member) and (name.startswith('supports_') or
                                 name.startswith('is_') and name.endswith('_available')):
            methods.append(name)
    return sorted(methods)


# All possible test arguments for methods that require parameters
# This allows detailed display of which specific arguments are supported
SUPPORT_METHOD_ALL_ARGS: Dict[str, List[str]] = {
    # ExplainSupport: all possible format types
    'supports_explain_format': ['TEXT', 'JSON', 'XML', 'YAML', 'TREE', 'DOT'],
    # SQLiteExtensionSupport: common extensions
    'is_extension_available': [
        'fts5', 'fts4', 'fts3', 'fts2', 'fts1',
        'json1', 'rtree', 'geopoly', 'dbstat', 'fts5tokenize'
    ],
    # SQLitePragmaSupport: sample pragmas from each category
    'is_pragma_available': [
        'journal_mode', 'synchronous', 'cache_size', 'temp_store',
        'foreign_keys', 'busy_timeout', 'wal_autocheckpoint'
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
                params = [p for p in sig.parameters.values()
                          if p.default == inspect.Parameter.empty]
                required_params = [p for p in params if p.name != 'self']

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
                    results[method_name] = {
                        'supported': supported_count,
                        'total': len(all_args),
                        'args': arg_results
                    }
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
    pragma_info = {
        "total_count": len(get_all_pragma_infos()),
        "categories": {}
    }

    for category in PragmaCategory:
        pragmas_in_category = [
            name for name, p in get_all_pragma_infos().items()
            if p.category == category
        ]
        pragma_info["categories"][category.name] = {
            "count": len(pragmas_in_category),
            "names": pragmas_in_category
        }

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
            supported_count += value['supported']
            total_count += value['total']
        else:
            total_count += 1
            if value:
                supported_count += 1

    return supported_count, total_count


def _build_protocol_info(dialect: Any, verbose: int) -> Dict[str, Any]:
    """Build protocol support information structure."""
    protocol_info = {}

    for group_name, protocols in PROTOCOL_FAMILY_GROUPS.items():
        protocol_info[group_name] = _build_protocol_group_info(
            dialect, protocols, verbose
        )

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


def display_info(verbose: int = 0, output_format: str = 'table'):
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
        if output_format == 'json' or not RICH_AVAILABLE:
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
    if output_format == 'json' or not RICH_AVAILABLE:
        print(json.dumps(info, indent=2))
    else:
        # Use legacy structure for rich display
        info_legacy = {
            "sqlite": info["database"],
            "extensions": info["features"]["extensions"],
            "pragmas": info["features"]["pragmas"],
            "protocols": info["protocols"]
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

    label = 'Detailed' if verbose >= 2 else 'Family Overview'
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

            sup = stats['supported']
            tot = stats['total']
            console.print(
                f"    [{color}]{symbol}[/{color}] {protocol_name}: "
                f"[{color}]{bar}[/{color}] {pct:.0f}% ({sup}/{tot})"
            )

            if verbose >= 2 and "methods" in stats:
                for method, value in stats["methods"].items():
                    method_display = (method.replace("supports_", "").replace("_", " ")
                                      .replace("is_", "").replace("_available", ""))
                    if isinstance(value, dict):
                        # Method with parameters - show each arg's support
                        console.print(f"        [dim]{method_display}:[/dim]")
                        for arg, supported in value.get('args', {}).items():
                            m_status = "[green][OK][/green]" if supported else "[red][X][/red]"
                            console.print(f"            {m_status} {arg}")
                    else:
                        # No-arg method
                        m_status = "[green][OK][/green]" if value else "[red][X][/red]"
                        console.print(f"        {m_status} {method_display}")

    console.print()


def main():
    args = parse_args()

    if args.info:
        output_format = args.output if args.output != 'table' or RICH_AVAILABLE else 'json'
        display_info(verbose=args.verbose, output_format=output_format)
        return

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    provider = get_provider(args)

    if RICH_AVAILABLE and isinstance(provider, RichOutputProvider):
        from rich.console import Console
        handler = RichHandler(
            rich_tracebacks=True,
            show_path=False,
            console=Console(stderr=True)
        )
        logging.basicConfig(
            level=numeric_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[handler]
        )
    else:
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )

    provider.display_greeting()

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
        msg = ("Error: No SQL query provided. "
               "Use a positional argument, the --file flag, or pipe from stdin.")
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
