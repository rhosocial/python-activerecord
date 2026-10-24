# src/rhosocial/activerecord/backend/impl/sqlite/cli/introspect.py
"""introspect subcommand - Database introspection."""

import argparse
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum

from .connection import add_connection_args, create_backend
from .output import create_provider

OUTPUT_CHOICES = ["table", "json", "csv", "tsv"]

INTROSPECT_TYPES = ["tables", "views", "table", "columns", "indexes", "foreign-keys", "triggers", "database"]


def create_parser(subparsers):
    """Create the introspect subcommand parser."""
    parser = subparsers.add_parser(
        "introspect",
        help="Database introspection",
        epilog="""Examples:
  # List all tables in database
  %(prog)s introspect tables --db-file mydb.sqlite

  # List all views
  %(prog)s introspect views --db-file mydb.sqlite

  # Get detailed table info (columns, indexes, foreign keys)
  %(prog)s introspect table users --db-file mydb.sqlite

  # Get column details for a table
  %(prog)s introspect columns users --db-file mydb.sqlite

  # Output as JSON
  %(prog)s introspect tables --db-file mydb.sqlite -o json

  # Using in-memory database
  %(prog)s introspect tables
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Output format (all)
    parser.add_argument(
        "-o",
        "--output",
        choices=OUTPUT_CHOICES,
        default="table",
        help="Output format (default: table)",
    )

    # Connection arguments
    add_connection_args(parser)

    # Rich display options
    parser.add_argument(
        "--rich-ascii",
        action="store_true",
        help="Use ASCII characters for rich table borders.",
    )

    # introspect-specific arguments
    parser.add_argument(
        "type",
        choices=INTROSPECT_TYPES,
        help="Introspection type: tables, views, table, columns, indexes, foreign-keys, triggers, database",
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Table/view name (required for some types)",
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="Include system tables",
    )

    return parser


#: Formats that are parsed by a machine, and so have to be a single document.
#: ``csv`` and ``tsv`` are deliberately not in this set: a CSV file with one
#: header row cannot carry three different record shapes, so those formats
#: stay sectioned, each with its own header, which is the only shape they can
#: have. ``json`` is the one that must be one document, and currently was not.
_SINGLE_DOCUMENT_FORMATS = frozenset({"json"})


def display_table_detail(provider, output_format, table_name, *, columns, indexes, foreign_keys):
    """Print one table's columns, indexes and foreign keys as one answer.

    Three questions, one table. The rendered (table) format prints them as
    three sections because a person reads them differently; ``json`` prints
    them as a single object, because a parser reading three concatenated
    arrays gets ``Extra data`` and nothing at all.

    Empty sections are dropped rather than emitted as ``[]``: an absent
    foreign-key list is the same fact as an empty one, and a caller checking
    ``"foreign_keys" in result`` would otherwise have to handle both.
    """
    sections = {}
    if columns:
        sections["columns"] = columns
    if indexes:
        sections["indexes"] = indexes
    if foreign_keys:
        sections["foreign_keys"] = foreign_keys

    if output_format in _SINGLE_DOCUMENT_FORMATS:
        provider.display_results(sections, title=table_name)
        return

    if columns:
        provider.display_results(columns, title=f"Columns of {table_name}")
    if indexes:
        provider.display_results(indexes, title=f"Indexes of {table_name}")
    if foreign_keys:
        provider.display_results(foreign_keys, title=f"Foreign Keys of {table_name}")


def handle(args):
    """Handle the introspect subcommand."""
    provider = create_provider(args.output, ascii_borders=args.rich_ascii)
    backend = create_backend(args)

    try:
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
                display_table_detail(
                    provider,
                    args.output,
                    args.name,
                    columns=[_serialize_for_output(c) for c in info.columns],
                    indexes=[_serialize_for_output(i) for i in info.indexes],
                    foreign_keys=[_serialize_for_output(f) for f in info.foreign_keys],
                )
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


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------


def _serialize_for_output(obj):
    """Serialize object for JSON output, handling non-serializable types."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        try:
            result = obj.model_dump(mode="json")
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
