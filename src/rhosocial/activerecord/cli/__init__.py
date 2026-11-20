# src/rhosocial/activerecord/cli/__init__.py
"""Command-line interface for rhosocial-activerecord.

The command tree is split by responsibility:

* ``dml``: single-record and bulk ActiveRecord writes.
* ``dql``: ActiveQuery reads and user-defined query execution.
* ``set``: SetOperationQuery combinations.
* ``cte``: CTEQuery execution.
* ``migrate``: ``@migration`` functions run as one transactional group.

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
from .commands import cte, dml, dql, migrate, setop
from .error_mapping import operation_label, translate_error
from .errors import (
    EXIT_BROKEN_PIPE,
    EXIT_ERROR,
    EXIT_USAGE,
    CLIError,
    report_error,
    report_unexpected,
)
from .interaction import ensure_writable
from .model_loader import ModelRef, load_model, prepare_sys_path
from .runtime import RuntimeContext, run_coroutine

COMMAND_NAMES = {
    "dml": ("create", "update", "delete", "bulk"),
    "dql": ("get", "list", "count", "exists", "aggregate", "run"),
    "set": ("union", "union-all", "intersect", "except", "run"),
    "cte": ("run",),
    "migrate": (),
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
        parents=[
            connection_parent,
            model_parent,
            output_parent,
            query_parent,
            mode_parent,
            pagination_parent,
        ],
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

    # migrate
    migrate_parser = groups.add_parser(
        "migrate",
        parents=[connection_parent],
        help="Run @migration functions as one transactional group",
    )
    migrate_parser.add_argument(
        "functions",
        nargs="+",
        metavar="FQN",
        help="Migration function FQNs, in the order they should run",
    )
    migrate_parser.add_argument(
        "--direction",
        choices=("up", "down"),
        default="up",
        help="Run forwards (up) or reverse the order and run backwards (down)",
    )
    migrate_parser.add_argument(
        "--record-store",
        default=None,
        metavar="PATH|MODULE:CLASS",
        help="JSON file or MigrationRecordStore class for version records",
    )
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and report the statements without writing",
    )
    migrate_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_functions",
        help="List the migration functions, versions and dependencies, then stop",
    )
    migrate_parser.add_argument(
        "--plan",
        action="store_true",
        dest="plan_functions",
        help="Show the execution order for the selected direction, then stop",
    )
    migrate_parser.add_argument(
        "--async",
        action="store_true",
        dest="force_async",
        help="Use the async variant declared by each function",
    )
    migrate_parser.add_argument(
        "-o",
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    migrate_parser.add_argument(
        "--model",
        default=None,
        metavar="MODULE:CLASS",
        help="Optional model supplying the connection; module-level functions "
        "may use explicit backend/config options instead",
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
            return _configure_async(model_ref.model, args, lambda: module.execute_async(ctx))
        return _configure_sync(model_ref.model, args, lambda: module.execute_sync(ctx))
    ctx = RuntimeContext(args, None, False)
    return module.execute_auto(ctx)


def _model_kind(model) -> bool:
    """Return True when *model* is an asynchronous ActiveRecord model."""
    from ..interface import IAsyncActiveRecord

    return issubclass(model, IAsyncActiveRecord)


def _run_migrate(args):
    """Resolve migration functions, configure the connection, then run."""
    from ..backend.migration.core import MigrationDirection
    from ..logging import LoggingConfig
    from .backends import resolve_connection_without_model

    functions = migrate.load_functions(args.functions)
    if getattr(args, "force_async", False):
        from ..backend.migration.group import select_async_functions

        functions = select_async_functions(functions)
    direction = MigrationDirection(args.direction)

    if getattr(args, "list_functions", False) or getattr(args, "plan_functions", False):
        migrate.print_functions(
            functions,
            direction,
            plan=bool(getattr(args, "plan_functions", False)),
            output=args.output,
        )
        return 0

    record_store = migrate.resolve_record_store(args.record_store)

    is_async = functions[0].is_async
    owner_models = {function.owner for function in functions if function.owner}
    for model in owner_models:
        if _model_kind(model) != is_async:
            raise CLIError(
                f"{model.__name__} is an asynchronous model but the migration "
                "functions are synchronous, or the reverse; align the function "
                "kind with its model"
            )

    model_ref = load_model(args.model) if args.model else None
    if model_ref is not None and model_ref.is_async != is_async:
        raise CLIError(
            "The --model must be asynchronous when the migration functions "
            "are asynchronous, and synchronous otherwise",
            exit_code=EXIT_USAGE,
        )
    if model_ref is None and owner_models:
        model_ref = ModelRef(next(iter(owner_models)), is_async)

    if model_ref is None:
        # Module-level functions never touch a model.  Accept an explicit
        # backend/config instead of asking for a model that has no role.
        if not getattr(args, "backend_class", None):
            raise CLIError(
                "Module-level migration functions have no model to supply a "
                "connection; pass --backend-class with --config-class/--config "
                "or --connection, or pass --model MODULE:CLASS",
                exit_code=EXIT_USAGE,
            )
        config, backend_class = resolve_connection_without_model(is_async, args)
        logging_config = LoggingConfig(default_level=args.log_level)
        backend_class.__logging_config__ = logging_config

        if is_async:

            async def execute():
                backend = backend_class(connection_config=config, logging_config=logging_config)
                try:
                    await backend.introspect_and_adapt()
                    await migrate.execute_async(
                        functions,
                        direction,
                        backend,
                        record_store,
                        dry_run=args.dry_run,
                        output=args.output,
                    )
                finally:
                    try:
                        await backend.disconnect()
                    except Exception:
                        pass
                return 0

            return run_coroutine(execute())

        backend = backend_class(connection_config=config, logging_config=logging_config)
        try:
            backend.introspect_and_adapt()
            migrate.execute_sync(
                functions,
                direction,
                backend,
                record_store,
                dry_run=args.dry_run,
                output=args.output,
            )
        finally:
            try:
                backend.disconnect()
            except Exception:
                pass
        return 0

    models = list(owner_models | {model_ref.model})
    for model in models:
        if _model_kind(model) != is_async:
            raise CLIError(
                f"{model.__name__} is not an {('async' if is_async else 'sync')} "
                "ActiveRecord model"
            )

    config, backend_class = resolve_connection(model_ref.model, is_async, args)
    logging_config = _prepare_model_logging(model_ref.model, backend_class, args.log_level)

    if is_async:

        async def execute():
            for model in models:
                await model.configure(config, backend_class, logging_config=logging_config)
            try:
                await migrate.execute_async(
                    functions,
                    direction,
                    model_ref.model.backend(),
                    record_store,
                    dry_run=args.dry_run,
                    output=args.output,
                )
            finally:
                for model in models:
                    backend = model.backend()
                    if backend is not None:
                        try:
                            await backend.disconnect()
                        except Exception:
                            pass
            return 0

        return run_coroutine(execute())

    for model in models:
        model.configure(config, backend_class, logging_config=logging_config)
    try:
        migrate.execute_sync(
            functions,
            direction,
            model_ref.model.backend(),
            record_store,
            dry_run=args.dry_run,
            output=args.output,
        )
    finally:
        for model in models:
            backend = model.backend()
            if backend is not None:
                try:
                    backend.disconnect()
                except Exception:
                    pass
    return 0


def _emit_migrate_error(error, exit_code: int, *, unexpected: bool = False) -> None:
    """Write a migration failure as one JSON object on stdout."""
    payload = {
        "command": "migrate",
        "success": False,
        "exit_code": exit_code,
        "error": getattr(error, "message", None) or str(error),
    }
    if unexpected:
        payload["error_type"] = type(error).__name__
    for attribute in (
        "migration_version",
        "migration_fqn",
        "executed",
        "transactional_ddl",
        "rolled_back",
    ):
        value = getattr(error, attribute, None)
        if value is not None:
            payload[attribute] = value
    from .commands.migrate import _emit_json

    _emit_json(payload)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the CLI and return its exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.section is None:
        print(
            "Error: Please specify a command group: dml, dql, set, cte, or migrate", file=sys.stderr
        )
        print("Use --help for more information.", file=sys.stderr)
        return EXIT_ERROR

    if args.section == "dml" and args.command == "bulk":
        if args.bulk_command is None:
            print(
                "Error: Please specify a bulk command: create, update, or delete", file=sys.stderr
            )
            return EXIT_ERROR
        operation = "bulk_" + args.bulk_command
    elif args.section == "dml":
        if args.command is None:
            print(
                "Error: Please specify a DML command: create, update, delete, or bulk",
                file=sys.stderr,
            )
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
        if args.section == "migrate":
            return _run_migrate(args)
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
        if args.section == "migrate" and getattr(args, "output", "text") == "json":
            _emit_migrate_error(exc, exc.exit_code)
        else:
            report_error(exc)
        return exc.exit_code
    except BrokenPipeError:
        return EXIT_BROKEN_PIPE
    except Exception as exc:  # Keep stdout clean for machine-readable formats.
        translated = translate_error(exc, operation=operation_label(args))
        if translated is not None:
            if args.section == "migrate" and getattr(args, "output", "text") == "json":
                _emit_migrate_error(translated, translated.exit_code)
            else:
                report_error(translated)
            return translated.exit_code
        if args.section == "migrate" and getattr(args, "output", "text") == "json":
            _emit_migrate_error(exc, EXIT_ERROR, unexpected=True)
        else:
            report_unexpected(exc)
        return EXIT_ERROR


__all__ = ["main", "build_parser", "COMMAND_NAMES"]
