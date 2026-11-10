# src/rhosocial/activerecord/cli/__init__.py
"""Command-line interface for rhosocial-activerecord.

The command tree is split by responsibility:

* ``dml``: single-record and bulk ActiveRecord writes.
* ``dql``: ActiveQuery reads and user-defined query execution.
* ``set``: SetOperationQuery combinations.
* ``cte``: CTEQuery execution.

Example:
    rhosocial-activerecord dql list --model app.models:User \\
        --backend-class mypkg.backend:MyBackend \\
        --config-class mypkg.config:MyConnectionConfig \\
        --config database=app.db -o json
"""

import argparse
import logging
import sys
from typing import List, Optional

from ..logging import LoggingConfig, configure_logging
from .args import (
    aggregate_parent,
    confirm_parent,
    connection_parent,
    filter_parent,
    mode_parent,
    model_parent,
    optional_model_parent,
    output_parent,
    pagination_parent,
    pk_parent,
    query_parent,
    write_parent,
)
from .backends import resolve_connection
from .commands import cte, dml, dql, setop
from .errors import (
    CLIError,
    EXIT_BROKEN_PIPE,
    EXIT_ERROR,
    report_error,
    report_unexpected,
)
from .interaction import ensure_writable
from .model_loader import load_model, prepare_sys_path
from .runtime import RuntimeContext, run_coroutine


COMMAND_NAMES = {
    "dml": ("create", "update", "delete", "bulk"),
    "dql": ("get", "list", "count", "exists", "aggregate", "run"),
    "set": ("union", "union-all", "intersect", "except", "run"),
    "cte": ("run",),
}


def _add_set_arm_arguments(parser) -> None:
    parser.add_argument("--left-model", required=True, metavar="MODULE:CLASS")
    parser.add_argument("--right-model", required=True, metavar="MODULE:CLASS")
    parser.add_argument("--left-where", action="append", default=None, metavar="FIELD=VALUE")
    parser.add_argument("--right-where", action="append", default=None, metavar="FIELD=VALUE")


def _add_dry_run(parser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Report without writing")


def build_parser() -> argparse.ArgumentParser:
    """Build the full CLI parser."""
    parser = argparse.ArgumentParser(
        prog="rhosocial-activerecord",
        description="Operate on ActiveRecord models from the command line.",
    )
    groups = parser.add_subparsers(dest="section", help="Available command groups")

    # dml
    dml_parser = groups.add_parser("dml", help="Model data operations")
    dml_sub = dml_parser.add_subparsers(dest="command", help="Available DML commands")

    dml_sub.add_parser(
        "create",
        parents=[connection_parent, model_parent, output_parent, write_parent],
        help="Create one record",
    )
    dml_sub.add_parser(
        "update",
        parents=[connection_parent, model_parent, output_parent, write_parent, pk_parent],
        help="Update one record",
    )
    delete_parser = dml_sub.add_parser(
        "delete",
        parents=[connection_parent, model_parent, output_parent, pk_parent, confirm_parent],
        help="Delete one record",
    )
    _add_dry_run(delete_parser)

    bulk_parser = dml_sub.add_parser("bulk", help="Bulk model data operations")
    bulk_sub = bulk_parser.add_subparsers(dest="bulk_command", help="Available bulk commands")
    bulk_sub.add_parser(
        "create",
        parents=[connection_parent, model_parent, output_parent, write_parent],
        help="Create records from JSON/JSONL",
    )
    bulk_sub.add_parser(
        "update",
        parents=[connection_parent, model_parent, output_parent, write_parent],
        help="Update records from JSON/JSONL",
    )
    bulk_sub.add_parser(
        "delete",
        parents=[connection_parent, model_parent, output_parent, write_parent, confirm_parent],
        help="Delete records from JSON/JSONL primary keys",
    )

    # dql
    dql_parser = groups.add_parser("dql", help="Model query operations")
    dql_sub = dql_parser.add_subparsers(dest="command", help="Available DQL commands")
    dql_sub.add_parser(
        "get",
        parents=[connection_parent, model_parent, output_parent, pk_parent],
        help="Fetch one record by primary key",
    )
    dql_sub.add_parser(
        "list",
        parents=[connection_parent, model_parent, output_parent, filter_parent, pagination_parent],
        help="List records",
    )
    dql_sub.add_parser(
        "count",
        parents=[connection_parent, model_parent, output_parent, filter_parent],
        help="Count records",
    )
    dql_sub.add_parser(
        "exists",
        parents=[connection_parent, model_parent, output_parent, filter_parent],
        help="Check whether records exist",
    )
    dql_sub.add_parser(
        "aggregate",
        parents=[
            connection_parent,
            model_parent,
            output_parent,
            filter_parent,
            pagination_parent,
            aggregate_parent,
        ],
        help="Run an aggregate query",
    )
    dql_sub.add_parser(
        "run",
        parents=[connection_parent, model_parent, output_parent, query_parent, mode_parent, pagination_parent],
        help="Execute a user-supplied ActiveQuery",
    )

    # set
    set_parser = groups.add_parser("set", help="Set operation queries")
    set_sub = set_parser.add_subparsers(dest="set_operation", help="Available set operations")
    for name, help_text in (
        ("union", "UNION of two model queries"),
        ("union-all", "UNION ALL of two model queries"),
        ("intersect", "INTERSECT of two model queries"),
        ("except", "EXCEPT of two model queries"),
    ):
        arm_parser = set_sub.add_parser(
            name,
            parents=[connection_parent, output_parent, filter_parent, pagination_parent],
            help=help_text,
        )
        _add_set_arm_arguments(arm_parser)
    set_sub.add_parser(
        "run",
        parents=[connection_parent, optional_model_parent, output_parent, query_parent],
        help="Execute a user-supplied SetOperationQuery",
    )

    # cte
    cte_parser = groups.add_parser("cte", help="CTE queries")
    cte_sub = cte_parser.add_subparsers(dest="command", help="Available CTE commands")
    cte_sub.add_parser(
        "run",
        parents=[connection_parent, optional_model_parent, output_parent, query_parent],
        help="Execute a user-supplied CTEQuery",
    )

    return parser


def _configure_cli_logging(level: int) -> None:
    """Set the framework log level, including loggers created at import time."""
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


def _configure_sync(model, args, runner):
    config, backend_class = resolve_connection(model, False, args)
    logging_config = _prepare_model_logging(model, backend_class, args.log_level)
    model.configure(config, backend_class, logging_config=logging_config)
    try:
        return runner()
    finally:
        backend = model.backend()
        if backend is not None:
            try:
                backend.disconnect()
            except Exception:
                pass


def _configure_async(model, args, runner):
    config, backend_class = resolve_connection(model, True, args)
    logging_config = _prepare_model_logging(model, backend_class, args.log_level)

    async def execute():
        await model.configure(config, backend_class, logging_config=logging_config)
        try:
            return await runner()
        finally:
            backend = model.backend()
            if backend is not None:
                try:
                    await backend.disconnect()
                except Exception:
                    pass

    return run_coroutine(execute())


def _run_dml(model_ref, args, operation):
    ensure_writable(model_ref.model, f"dml {operation.replace('_', ' ')}")
    ctx = RuntimeContext(args, model_ref.model, model_ref.is_async)
    if model_ref.is_async:
        handler = dml.ASYNC_HANDLERS[operation]
        return _configure_async(model_ref.model, args, lambda: handler(ctx))
    handler = dml.SYNC_HANDLERS[operation]
    return _configure_sync(model_ref.model, args, lambda: handler(ctx))


def _run_dql(model_ref, args):
    ctx = RuntimeContext(args, model_ref.model, model_ref.is_async)
    if model_ref.is_async:
        handler = dql.ASYNC_HANDLERS[args.command]
        return _configure_async(model_ref.model, args, lambda: handler(ctx))
    handler = dql.SYNC_HANDLERS[args.command]
    return _configure_sync(model_ref.model, args, lambda: handler(ctx))


def _configure_pair(left_model, right_model, args, runner):
    config, backend_class = resolve_connection(left_model, False, args)
    left_config = _prepare_model_logging(left_model, backend_class, args.log_level)
    right_config = _prepare_model_logging(right_model, backend_class, args.log_level)
    left_model.configure(config, backend_class, logging_config=left_config)
    right_model.configure(config, backend_class, logging_config=right_config)
    try:
        return runner(left_model, right_model)
    finally:
        for model in (left_model, right_model):
            backend = model.backend()
            if backend is not None:
                try:
                    backend.disconnect()
                except Exception:
                    pass


async def _configure_pair_async(left_model, right_model, args, runner):
    config, backend_class = resolve_connection(left_model, True, args)
    left_config = _prepare_model_logging(left_model, backend_class, args.log_level)
    right_config = _prepare_model_logging(right_model, backend_class, args.log_level)
    await left_model.configure(config, backend_class, logging_config=left_config)
    await right_model.configure(config, backend_class, logging_config=right_config)
    try:
        return await runner(left_model, right_model)
    finally:
        for model in (left_model, right_model):
            backend = model.backend()
            if backend is not None:
                try:
                    await backend.disconnect()
                except Exception:
                    pass


def _run_set_simple(args):
    left_ref = load_model(args.left_model)
    right_ref = load_model(args.right_model)
    if left_ref.is_async != right_ref.is_async:
        raise CLIError("Set operands must both be synchronous or both be asynchronous")
    if not hasattr(args, "model"):
        args.model = None
    ctx = RuntimeContext(args, left_ref.model, left_ref.is_async)
    if left_ref.is_async:
        return run_coroutine(
            _configure_pair_async(
                left_ref.model,
                right_ref.model,
                args,
                lambda left, right: setop.execute_async(ctx, left, right),
            )
        )
    return _configure_pair(
        left_ref.model,
        right_ref.model,
        args,
        lambda left, right: setop.execute_sync(ctx, left, right),
    )


def _run_query_group(args, module):
    if getattr(args, "model", None):
        model_ref = load_model(args.model)
        ctx = RuntimeContext(args, model_ref.model, model_ref.is_async)
        if model_ref.is_async:
            return _configure_async(
                model_ref.model, args, lambda: module.execute_async(ctx)
            )
        return _configure_sync(
            model_ref.model, args, lambda: module.execute_sync(ctx)
        )
    ctx = RuntimeContext(args, None, False)
    return module.execute_auto(ctx)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the CLI and return its exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.section is None:
        print("Error: Please specify a command group: dml, dql, set, or cte", file=sys.stderr)
        print("Use --help for more information.", file=sys.stderr)
        return EXIT_ERROR

    if args.section == "dml" and args.command == "bulk":
        if args.bulk_command is None:
            print("Error: Please specify a bulk command: create, update, or delete", file=sys.stderr)
            return EXIT_ERROR
        operation = "bulk_" + args.bulk_command
    elif args.section == "dml":
        if args.command is None:
            print("Error: Please specify a DML command: create, update, delete, or bulk", file=sys.stderr)
            return EXIT_ERROR
        operation = args.command
    elif args.section == "dql" and args.command is None:
        print("Error: Please specify a DQL command", file=sys.stderr)
        return EXIT_ERROR
    elif args.section == "set" and args.set_operation is None:
        print("Error: Please specify a set operation", file=sys.stderr)
        return EXIT_ERROR
    elif args.section == "cte" and args.command is None:
        print("Error: Please specify the cte run command", file=sys.stderr)
        return EXIT_ERROR
    else:
        operation = None

    _configure_cli_logging(args.log_level)
    prepare_sys_path(getattr(args, "path", None))

    try:
        if args.section == "dml":
            if operation is None:
                print("Error: Please specify a DML command", file=sys.stderr)
                return EXIT_ERROR
            model_ref = load_model(args.model)
            return _run_dml(model_ref, args, operation)
        if args.section == "dql":
            model_ref = load_model(args.model)
            return _run_dql(model_ref, args)
        if args.section == "set":
            if args.set_operation is None:
                print("Error: Please specify a set operation", file=sys.stderr)
                return EXIT_ERROR
            if args.set_operation == "run":
                return _run_query_group(args, setop)
            return _run_set_simple(args)
        if args.section == "cte":
            if args.command != "run":
                print("Error: Please specify the cte run command", file=sys.stderr)
                return EXIT_ERROR
            return _run_query_group(args, cte)
        print("Error: Unknown command group", file=sys.stderr)
        return EXIT_ERROR
    except CLIError as exc:
        report_error(exc)
        return exc.exit_code
    except BrokenPipeError:
        return EXIT_BROKEN_PIPE
    except Exception as exc:  # Keep stdout clean for machine-readable formats.
        report_unexpected(exc)
        return EXIT_ERROR


__all__ = ["main", "build_parser", "COMMAND_NAMES"]
