# src/rhosocial/activerecord/cli/__init__.py
"""Model CRUD command-line interface for rhosocial-activerecord.

The entry point is ``rhosocial-activerecord``. Commands live under the ``crud``
namespace so that future ``schema`` / ``migration`` groups can be added without
rearranging this one.

Example:
    rhosocial-activerecord crud list --model app.models:User \\
        --backend sqlite --database app.db -o json
"""

import argparse
import asyncio
import logging
import sys
from typing import List, Optional

from ..logging import LoggingConfig, configure_logging
from .args import DEFAULT_LIST_LIMIT, connection_parent, fields_parent
from .backends import resolve_connection
from .crud import execute_async, execute_sync
from .errors import (
    CLIError,
    EXIT_ERROR,
    report_error,
    report_unexpected,
)
from .model_loader import load_model, prepare_sys_path

COMMAND_NAMES = ("get", "list", "create", "update", "delete")


def _add_pk_arguments(parser) -> None:
    parser.add_argument("--pk", default=None, help="Primary key value or JSON object")
    parser.add_argument(
        "--pk-json",
        default=None,
        help="Primary key JSON object (alias for --pk with a JSON object)",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the full CLI parser."""
    parser = argparse.ArgumentParser(
        prog="rhosocial-activerecord",
        description="Perform one CRUD operation on an ActiveRecord model.",
    )
    subparsers = parser.add_subparsers(dest="section", help="Available command groups")

    crud_parser = subparsers.add_parser("crud", help="Model data operations")
    crud_subparsers = crud_parser.add_subparsers(dest="command", help="Available commands")

    get_parser = crud_subparsers.add_parser(
        "get", parents=[connection_parent, fields_parent], help="Fetch one record by primary key"
    )
    _add_pk_arguments(get_parser)

    list_parser = crud_subparsers.add_parser(
        "list", parents=[connection_parent, fields_parent], help="List records"
    )
    list_parser.add_argument(
        "--where", action="append", default=None, metavar="FIELD=VALUE", help="Equality filter; may be repeated"
    )
    list_parser.add_argument(
        "--order-by",
        action="append",
        default=None,
        metavar="FIELD [ASC|DESC]",
        help="Sort clause; may be repeated",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIST_LIMIT,
        help=f"Maximum rows (default: {DEFAULT_LIST_LIMIT}; 0 means no limit)",
    )
    list_parser.add_argument("--offset", type=int, default=0, help="Rows to skip")

    create_parser = crud_subparsers.add_parser(
        "create", parents=[connection_parent, fields_parent], help="Create a record from JSON"
    )
    create_parser.add_argument(
        "--data", required=True, metavar="JSON|@FILE|@-", help="JSON object, a file, or stdin"
    )

    update_parser = crud_subparsers.add_parser(
        "update", parents=[connection_parent, fields_parent], help="Update one record by primary key"
    )
    _add_pk_arguments(update_parser)
    update_parser.add_argument(
        "--data", required=True, metavar="JSON|@FILE|@-", help="JSON object, a file, or stdin"
    )

    delete_parser = crud_subparsers.add_parser(
        "delete", parents=[connection_parent], help="Delete one record by primary key"
    )
    _add_pk_arguments(delete_parser)

    return parser


def _configure_cli_logging(level: int) -> None:
    """Set the framework log level, including loggers created at import time.

    Importing backend modules creates loggers before ``main`` runs, so changing
    the default alone would leave those loggers at their original DEBUG level.
    """
    configure_logging(level=level)
    prefix = "rhosocial.activerecord"
    for name, logger in logging.Logger.manager.loggerDict.items():
        if name == prefix or name.startswith(prefix + "."):
            if isinstance(logger, logging.Logger):
                logger.setLevel(level)


def _prepare_model_logging(model, backend_class, level: int) -> LoggingConfig:
    """Give the model and backend a stderr/level-aware logging config."""
    config = LoggingConfig(default_level=level)
    model.__logging_config__ = config
    backend_class.__logging_config__ = config
    return config


def _configure_and_run_async(model, config, backend_class, args, log_level):
    logging_config = _prepare_model_logging(model, backend_class, log_level)

    async def runner():
        await model.configure(config, backend_class, logging_config=logging_config)
        try:
            return await execute_async(args, model)
        finally:
            backend = model.backend()
            if backend is not None:
                try:
                    await backend.disconnect()
                except Exception:
                    pass

    return asyncio.run(runner())


def _configure_and_run_sync(model, config, backend_class, args, log_level):
    logging_config = _prepare_model_logging(model, backend_class, log_level)
    model.configure(config, backend_class, logging_config=logging_config)
    try:
        return execute_sync(args, model)
    finally:
        backend = model.backend()
        if backend is not None:
            try:
                backend.disconnect()
            except Exception:
                pass


def main(argv: Optional[List[str]] = None) -> int:
    """Run the CLI and return its exit code.

    Args:
        argv: Argument list, or None to read ``sys.argv``. Tests call this
            in-process with an explicit list.

    Returns:
        Process exit code: 0 success, 1 business error, 3 not found, 4 backend
        unavailable. argparse itself exits with 2 for usage errors.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.section is None:
        print("Error: Please specify a command group: 'crud'", file=sys.stderr)
        print("Use --help for more information.", file=sys.stderr)
        return EXIT_ERROR

    if args.command is None:
        print(
            "Error: Please specify a command: " + ", ".join(f"'{name}'" for name in COMMAND_NAMES),
            file=sys.stderr,
        )
        print("Use --help for more information.", file=sys.stderr)
        return EXIT_ERROR

    _configure_cli_logging(args.log_level)
    prepare_sys_path(args.path)

    try:
        model_ref = load_model(args.model)
        config, backend_class, _spec = resolve_connection(model_ref.model, model_ref.is_async, args)
        if model_ref.is_async:
            return _configure_and_run_async(
                model_ref.model, config, backend_class, args, args.log_level
            )
        return _configure_and_run_sync(model_ref.model, config, backend_class, args, args.log_level)
    except CLIError as exc:
        report_error(exc)
        return exc.exit_code
    except Exception as exc:  # Keep stdout clean for machine-readable formats.
        report_unexpected(exc)
        return EXIT_ERROR


__all__ = ["main", "build_parser", "COMMAND_NAMES"]
