# src/rhosocial/activerecord/cli/args.py
"""Shared argparse parents for the ActiveRecord model CLI."""

import argparse
import logging

#: Output formats offered by every ``crud`` subcommand.
OUTPUT_FORMATS = ("table", "json", "csv", "tsv")

#: Default number of rows returned by ``crud list``.
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
        "--model",
        required=True,
        metavar="MODULE:CLASS",
        help="ActiveRecord model to operate on, for example app.models:User",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=None,
        metavar="DIR",
        help="Extra directory to add to sys.path; may be repeated",
    )
    parser.add_argument(
        "--backend",
        default=None,
        metavar="NAME",
        help="Database backend: sqlite, mysql, mariadb, postgres, sqlserver, "
        "oracle, firebird, snowflake, clickhouse, bigquery",
    )
    parser.add_argument(
        "--connection",
        default=None,
        metavar="MODULE:CALLABLE",
        help="Named connection callable returning a ConnectionConfig",
    )
    parser.add_argument("--database", default=None, help="Database name or SQLite file path")
    parser.add_argument("--host", default=None, help="Database host")
    parser.add_argument("--port", default=None, help="Database port")
    parser.add_argument("--user", default=None, help="Database user name")
    parser.add_argument("--password", default=None, help="Database password (not logged)")
    parser.add_argument(
        "--option",
        action="append",
        default=None,
        metavar="KEY=VALUE",
        help="Set a config field, or add KEY=VALUE to config.options",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="table",
        choices=OUTPUT_FORMATS,
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--rich-ascii",
        action="store_true",
        help="Use ASCII borders for table output",
    )
    parser.add_argument(
        "--log-level",
        type=log_level,
        default=logging.WARNING,
        help="Framework log level (default: WARNING); logs go to stderr",
    )


#: Parent parser carrying model, connection, and presentation options.
connection_parent = argparse.ArgumentParser(add_help=False)
_add_connection_arguments(connection_parent)

#: Parent parser for commands that may limit the output columns.
fields_parent = argparse.ArgumentParser(add_help=False)
fields_parent.add_argument(
    "--fields",
    default=None,
    metavar="A,B",
    help="Comma-separated field names to include in the output",
)
