# src/rhosocial/activerecord/backend/impl/sqlite/cli/introspect.py
"""introspect subcommand - Database introspection."""

import argparse
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum

from .connection import add_connection_args, create_backend
from .output import create_provider

OUTPUT_CHOICES = ["table", "json", "csv", "tsv"]

#: The single place a type name maps to the dialect capability that decides
#: whether this backend can answer it. ``INTROSPECT_TYPES`` is derived from it,
#: so a family cannot be offered without a switch saying it may be, and the
#: order below is the order the parser and ``--help`` print.
_TYPE_CAPABILITIES = {
    "tables": "supports_table_introspection",
    "views": "supports_view_introspection",
    "columns": "supports_column_introspection",
    "indexes": "supports_index_introspection",
    "foreign-keys": "supports_foreign_key_introspection",
    "triggers": "supports_trigger_introspection",
    "database": "supports_database_info",
}

INTROSPECT_TYPES = list(_TYPE_CAPABILITIES)

#: What the optional NAME positional means for each type.
#:
#: ``required`` -- the type asks about one table and cannot be answered without
#: it. ``optional`` -- a family that can also answer for one member, so a given
#: name narrows it (and a name that matches nothing is an error, not an empty
#: list). ``forbidden`` -- the family has no single-member question here.
#: ``tables`` must stay one: answering for one table would fill in its columns,
#: indexes and foreign keys, which is the aggregate this command dropped.
_NAME_RULE = {
    "tables": "forbidden",
    "views": "optional",
    "columns": "required",
    "indexes": "required",
    "foreign-keys": "required",
    "triggers": "optional",
    "database": "forbidden",
}


def create_parser(subparsers):
    """Create the introspect subcommand parser."""
    parser = subparsers.add_parser(
        "introspect",
        help="Database introspection",
        epilog="""Examples:
  # List all tables in database
  %(prog)s introspect tables --db-file mydb.sqlite

  # List all views, or describe one of them
  %(prog)s introspect views --db-file mydb.sqlite
  %(prog)s introspect views active_users --db-file mydb.sqlite

  # Get column details for a table, including generated columns
  %(prog)s introspect columns users --db-file mydb.sqlite

  # The triggers of one table
  %(prog)s introspect triggers posts --db-file mydb.sqlite

  # Output as JSON
  %(prog)s introspect tables --db-file mydb.sqlite -o json

  # NAME is a table for columns/indexes/foreign-keys, the view itself for
  # views, a table for triggers, and is refused for tables/database -- those
  # answer for the whole database.

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
        help="Introspection type: " + ", ".join(INTROSPECT_TYPES),
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help=(
            "Object name: a table for columns/indexes/foreign-keys and "
            "triggers, the view itself for views. Refused for tables/database."
        ),
    )
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="Include system tables",
    )

    return parser


def handle(args):
    """Handle the introspect subcommand."""
    provider = create_provider(args.output, ascii_borders=args.rich_ascii)

    # Both checks run before any real work: a NAME the type cannot use is a
    # malformed request, and a family this dialect cannot answer is one this
    # build does not offer. ``create_backend`` adapts the dialect, so the
    # capability switch below answers for the SQLite in front of us.
    _validate_name(args)

    backend = create_backend(args)

    try:
        _require_capability(args, backend)
        introspector = backend.introspector

        if args.type == "tables":
            tables = introspector.list_tables(include_system=args.include_system)
            data = [_serialize_for_output(t) for t in tables]
            provider.display_results(data, title="Tables")

        elif args.type == "views":
            if args.name:
                view = introspector.get_view_info(args.name)
                if view is None:
                    print(f"Error: View '{args.name}' not found", file=sys.stderr)
                    sys.exit(1)
                data = [_serialize_for_output(view)]
                provider.display_results(data, title=f"View {args.name}")
            else:
                views = introspector.list_views()
                data = [_serialize_for_output(v) for v in views]
                provider.display_results(data, title="Views")

        elif args.type == "columns":
            columns = introspector.list_columns(args.name)
            data = [_serialize_for_output(c) for c in columns]
            provider.display_results(data, title=f"Columns of {args.name}")

        elif args.type == "indexes":
            indexes = introspector.list_indexes(args.name)
            data = [_serialize_for_output(i) for i in indexes]
            provider.display_results(data, title=f"Indexes of {args.name}")

        elif args.type == "foreign-keys":
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


def _validate_name(args) -> None:
    """Refuse a NAME the type cannot use, before anything opens a database.

    A silently ignored argument is the worst of the three outcomes: the run
    succeeds, prints a full listing, and reads as though it had been narrowed.
    So the rule table above is applied here, once, instead of being left to
    each branch to remember.
    """
    rule = _NAME_RULE.get(args.type)
    if rule is None:
        return
    if rule == "required" and not args.name:
        # The same code a missing connection argument gets: the run never
        # became a question. 2 is reserved for a request this command refuses
        # to serve, below.
        print(
            f"Error: Table name is required for '{args.type}' introspection",
            file=sys.stderr,
        )
        sys.exit(1)
    if rule == "forbidden" and args.name:
        print(
            f"Error: '{args.type}' introspection answers for the whole database "
            f"and takes no name",
            file=sys.stderr,
        )
        sys.exit(2)


def _require_capability(args, backend) -> None:
    """Refuse a family the connected dialect says it cannot answer.

    ``create_backend`` adapts the dialect before this runs, so the switch
    answers for the SQLite in front of us. A stub standing in for the backend
    (the offline CLI tests) may carry no dialect at all; a real one always does.
    """
    switch = _TYPE_CAPABILITIES.get(args.type)
    if switch is None:
        return
    dialect = getattr(backend, "dialect", None)
    if dialect is None:
        return
    supported = getattr(dialect, switch, None)
    if supported is None or supported():
        return
    print(
        f"Error: {args.type} introspection is not supported by this server",
        file=sys.stderr,
    )
    sys.exit(2)


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
