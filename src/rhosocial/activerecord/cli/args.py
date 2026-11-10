# src/rhosocial/activerecord/cli/args.py
"""Shared argparse parents for the ActiveRecord model CLI."""

import argparse
import logging

#: Output formats offered by the CLI.
OUTPUT_FORMATS = ("table", "json", "jsonl", "csv", "tsv", "value")

#: Default number of rows returned by row-producing commands.
DEFAULT_LIST_LIMIT = 100


_LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


def log_level(value):
    """argparse type: accept a logging level name."""
    text = str(value).upper()
    if text in _LOG_LEVELS:
        return _LOG_LEVELS[text]
    raise argparse.ArgumentTypeError(
        f"unknown log level {value!r}; choose one of {', '.join(_LOG_LEVELS)}"
    )


def _add_connection_arguments(parser):
    parser.add_argument(
        "--path",
        action="append",
        default=None,
        metavar="DIR",
        help="Extra directory to add to sys.path; may be repeated",
    )
    parser.add_argument(
        "--backend-class",
        default=None,
        metavar="MODULE:CLASS",
        help="Fully qualified backend class to use, for example "
        "mypkg.backend:MyBackend. For an asynchronous model, name the "
        "asynchronous class.",
    )
    parser.add_argument(
        "--connection",
        default=None,
        metavar="MODULE:CALLABLE",
        help="Named connection callable returning a ConnectionConfig",
    )
    parser.add_argument(
        "--config-class",
        default=None,
        metavar="MODULE:CLASS",
        help="Fully qualified connection config class, for example "
        "mypkg.config:MyConnectionConfig",
    )
    parser.add_argument(
        "--config",
        action="append",
        default=None,
        metavar="KEY=VALUE",
        help="Set a connection config field; may be repeated. Unknown keys and "
        "options.KEY entries go into config.options",
    )
    parser.add_argument(
        "--log-level",
        type=log_level,
        default=logging.WARNING,
        help="Framework log level (default: WARNING); logs go to stderr",
    )


def _add_output_arguments(parser):
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        choices=OUTPUT_FORMATS,
        help="Output format; defaults to table on a TTY and json otherwise",
    )
    parser.add_argument(
        "--fields",
        default=None,
        metavar="A,B",
        help="Comma-separated field names to include in the output",
    )
    parser.add_argument(
        "--rich-ascii",
        action="store_true",
        help="Use ASCII borders for table output",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Omit the header row in csv/tsv output",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress informational stderr messages",
    )


def _add_filter_arguments(parser):
    parser.add_argument(
        "--where",
        action="append",
        default=None,
        metavar="FIELD=VALUE",
        help="Equality filter; may be repeated",
    )
    parser.add_argument(
        "--order-by",
        action="append",
        default=None,
        metavar="FIELD [ASC|DESC]",
        help="Sort clause; may be repeated",
    )
    parser.add_argument(
        "--select",
        default=None,
        metavar="A,B",
        help="Comma-separated columns to select",
    )
    parser.add_argument(
        "--include-deleted",
        action="store_true",
        help="Include soft-deleted rows when the model supports it",
    )
    parser.add_argument(
        "--only-deleted",
        action="store_true",
        help="Query only soft-deleted rows when the model supports it",
    )


def _add_pagination_arguments(parser):
    parser.add_argument("--limit", type=int, default=None, help="Maximum rows")
    parser.add_argument("--offset", type=int, default=None, help="Rows to skip")
    parser.add_argument(
        "--no-limit",
        action="store_true",
        help="Do not inject the default row limit",
    )
    parser.add_argument("--page", type=int, default=None, help="Page number (1-based)")
    parser.add_argument("--page-size", type=int, default=None, help="Rows per page")


def _add_write_arguments(parser):
    parser.add_argument(
        "--data",
        required=True,
        metavar="JSON|@FILE|@-|-",
        help="JSON object/array, a file, or stdin",
    )
    parser.add_argument(
        "--input-format",
        choices=("json", "jsonl"),
        default=None,
        help="Force the input format instead of auto-detecting it",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Split bulk create/update into batches of this size",
    )
    parser.add_argument(
        "--update-fields",
        default=None,
        metavar="A,B",
        help="Comma-separated fields applied by bulk update",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the planned operation without writing",
    )


def _add_confirm_arguments(parser):
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm a destructive command without prompting",
    )


def _add_pk_arguments(parser):
    parser.add_argument("--pk", default=None, help="Primary key value or JSON object")
    parser.add_argument(
        "--pk-json",
        default=None,
        help="Primary key JSON object (alias for --pk with a JSON object)",
    )


#: Parent parser carrying connection options, without ``--model``.
connection_parent = argparse.ArgumentParser(add_help=False)
_add_connection_arguments(connection_parent)

#: Parent parser carrying the required model reference.
model_parent = argparse.ArgumentParser(add_help=False)
model_parent.add_argument(
    "--model",
    required=True,
    metavar="MODULE:CLASS",
    help="ActiveRecord model to operate on, for example app.models:User",
)

#: Parent parser carrying an optional model reference (set/cte run).
optional_model_parent = argparse.ArgumentParser(add_help=False)
optional_model_parent.add_argument(
    "--model",
    default=None,
    metavar="MODULE:CLASS",
    help="Optional ActiveRecord model used to configure the connection",
)

#: Parent parser for presentation options.
output_parent = argparse.ArgumentParser(add_help=False)
_add_output_arguments(output_parent)

#: Parent parser for simple filters.
filter_parent = argparse.ArgumentParser(add_help=False)
_add_filter_arguments(filter_parent)

#: Parent parser for pagination.
pagination_parent = argparse.ArgumentParser(add_help=False)
_add_pagination_arguments(pagination_parent)

#: Parent parser for write data.
write_parent = argparse.ArgumentParser(add_help=False)
_add_write_arguments(write_parent)

#: Parent parser for destructive-command confirmation.
confirm_parent = argparse.ArgumentParser(add_help=False)
_add_confirm_arguments(confirm_parent)

#: Parent parser for primary-key arguments.
pk_parent = argparse.ArgumentParser(add_help=False)
_add_pk_arguments(pk_parent)

#: Parent parser for a user-supplied query factory.
query_parent = argparse.ArgumentParser(add_help=False)
query_parent.add_argument(
    "--query",
    required=True,
    metavar="MODULE:CALLABLE",
    help="Callable returning an existing Query object",
)

#: Parent parser for dql run execution mode.
mode_parent = argparse.ArgumentParser(add_help=False)
mode_parent.add_argument(
    "--mode",
    default="list",
    choices=("list", "one", "count", "exists", "aggregate"),
    help="How to execute the user-supplied query",
)

#: Parent parser for aggregate options.
aggregate_parent = argparse.ArgumentParser(add_help=False)
aggregate_parent.add_argument(
    "--fn",
    default="count",
    choices=("count", "sum", "avg", "min", "max"),
    help="Aggregate function",
)
aggregate_parent.add_argument(
    "--field",
    default="*",
    help="Column to aggregate; count accepts *",
)
aggregate_parent.add_argument(
    "--group-by",
    action="append",
    default=None,
    metavar="COLUMN",
    help="GROUP BY column; may be repeated",
)
aggregate_parent.add_argument(
    "--distinct",
    action="store_true",
    help="Use DISTINCT in the aggregate function",
)

#: Backwards-compatible alias used by older tests/imports.
fields_parent = output_parent
