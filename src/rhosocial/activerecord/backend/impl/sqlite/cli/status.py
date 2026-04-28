# src/rhosocial/activerecord/backend/impl/sqlite/cli/status.py
"""status subcommand - Display database status."""

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum

from rhosocial.activerecord.backend.introspection.status import StatusCategory

from .connection import add_connection_args, create_backend
from .output import create_provider, RICH_AVAILABLE

OUTPUT_CHOICES = ['table', 'json', 'csv', 'tsv']

STATUS_TYPES = ["all", "config", "performance", "storage", "databases"]


def create_parser(subparsers):
    """Create the status subcommand parser."""
    parser = subparsers.add_parser(
        'status',
        help='Display server status overview',
        epilog="""Examples:
  # Show complete status overview
  %(prog)s status all --db-file mydb.sqlite

  # Show configuration parameters only
  %(prog)s status config --db-file mydb.sqlite

  # Show performance metrics only
  %(prog)s status performance --db-file mydb.sqlite

  # Output as JSON
  %(prog)s status all --db-file mydb.sqlite -o json

  # Using in-memory database
  %(prog)s status all
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Output format (all, but 'all' type falls back to json for csv/tsv)
    parser.add_argument(
        '-o', '--output',
        choices=OUTPUT_CHOICES,
        default='table',
        help='Output format (default: table)',
    )

    # Connection arguments
    add_connection_args(parser)

    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity for additional columns.',
    )

    # Rich display options
    parser.add_argument(
        '--rich-ascii',
        action='store_true',
        help='Use ASCII characters for rich table borders.',
    )

    # status-specific arguments
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=STATUS_TYPES,
        help="Status type: all (default), config, performance, storage, databases",
    )

    return parser


def handle(args):
    """Handle the status subcommand."""
    provider = create_provider(args.output, ascii_borders=args.rich_ascii)
    backend = create_backend(args)

    try:
        status_introspector = backend.introspector.status
        status_type = args.type

        if status_type == "all":
            status = status_introspector.get_overview()
            # 'all' type outputs nested structure; csv/tsv not suitable, fall back to json
            effective_output = args.output
            if effective_output in ("csv", "tsv"):
                effective_output = "json"

            if effective_output == "json" or not RICH_AVAILABLE:
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


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------

def _serialize_for_output(obj):
    """Serialize object for JSON output."""
    if obj is None:
        return None
    if hasattr(obj, 'model_dump'):
        try:
            result = obj.model_dump(mode='json')
            return _serialize_for_output(result)
        except TypeError:
            result = obj.model_dump()
            return _serialize_for_output(result)
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize_for_output(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize_for_output(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize_for_output(item) for item in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def _format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _display_status_rich(status, verbose: int = 0):
    """Display status using rich console."""
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
