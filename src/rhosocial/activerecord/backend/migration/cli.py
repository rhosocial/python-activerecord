# src/rhosocial/activerecord/backend/migration/cli.py
"""CLI utilities for named migration functionality.

This module provides reusable functions to add the ``named-migration``
subcommand to backend CLI tools (e.g. SQLite).  It mirrors the pattern
established by ``cli_procedure.py`` for named procedures.

Features:
    - Execute a named migration (UP / DOWN)
    - List migrations in a module
    - Describe a migration (version, dependencies, parameters)
    - Dry-run support
    - Dialect validation hook
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from .core import MigrationDirection, NamedMigration
from .runner import MigrationRunner


def _replace_prog_placeholder(docstring: str, prog: str = None) -> str:
    """Replace ``%(prog)s`` placeholders with the actual program name."""
    if prog is None:
        prog = "python -m rhosocial.activerecord.backend.impl.sqlite"
    return docstring.replace("%(prog)s", prog).replace("%%(prog)s", prog)


def list_named_migrations_in_module(
    module_name: str,
) -> list[dict[str, Any]]:
    """List all ``NamedMigration`` subclasses found in a module.

    Returns:
        List of migration info dicts with keys:
        ``name``, ``version``, ``dependencies``, ``brief``.
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        print(f"Error: Module not found: {module_name}. {e}", file=sys.stderr)
        sys.exit(1)


    results: list[dict[str, Any]] = []
    for name in dir(module):
        if name.startswith("_"):
            continue
        obj = getattr(module, name, None)
        if obj is None:
            continue
        if (
            isinstance(obj, type)
            and issubclass(obj, NamedMigration)
            and obj is not NamedMigration
        ):
            doc = inspect.getdoc(obj) or ""
            brief = doc.split("\n")[0].strip() if doc else ""
            results.append(
                {
                    "name": name,
                    "version": getattr(obj, "version", ""),
                    "dependencies": getattr(obj, "dependencies", []),
                    "brief": brief,
                }
            )
    return results


def _resolve_record_store(
    record_store_arg: str,
) -> Any:
    """Resolve ``--record-store`` argument.

    Supports:
    - A JSON file path (ending with ``.json`` or containing a path separator)
    - A Python class FQN (e.g. ``myapp.stores.MyRecordStore``)

    Falls back to ``None`` when the argument is empty.
    """
    if not record_store_arg:
        return None

    path = Path(record_store_arg)
    if record_store_arg.endswith(".json") or "/" in record_store_arg:
        from .record import JSONFileMigrationRecordStore

        return JSONFileMigrationRecordStore(path)

    # Treat as a class FQN
    try:
        module_path, class_name = record_store_arg.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls()
    except (ImportError, AttributeError, ValueError) as e:
        print(
            f"Error: Cannot resolve record store '{record_store_arg}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def _parse_params(params: list[str]) -> dict[str, str]:
    """Parse ``--param KEY=VALUE`` list into a dict."""
    result: dict[str, str] = {}
    for param in params:
        if "=" in param:
            key, value = param.split("=", 1)
            result[key] = value
        else:
            print(
                f"Warning: Invalid parameter format: {param}. Use KEY=VALUE",
                file=sys.stderr,
            )
    return result


def create_named_migration_parser(
    subparsers: argparse._SubParsersAction,
    parent_parser: argparse.ArgumentParser,
    epilog: str = None,
) -> argparse.ArgumentParser:
    """Create the ``named-migration`` subcommand parser.

    Args:
        subparsers: The subparsers action from the main parser.
        parent_parser: Parent parser with common connection & output args.
        epilog: Custom examples text.  Defaults to SQLite-style examples.

    Returns:
        The created subcommand parser.
    """
    if epilog is None:
        epilog = """Examples:
  # Apply a single migration
  %(prog)s myapp.migrations.v001.CreateUsersTable --db-file mydb.sqlite --direction up

  # Rollback a single migration
  %(prog)s myapp.migrations.v001.CreateUsersTable --db-file mydb.sqlite --direction down

  # Apply with record store (dependency checks & duplicate protection)
  %(prog)s myapp.migrations.v001.CreateUsersTable --db-file mydb.sqlite --record-store ./migrations.json

  # Dry-run (preview without changes)
  %(prog)s myapp.migrations.v001.CreateUsersTable --db-file mydb.sqlite --direction up --dry-run

  # Apply asynchronously
  %(prog)s myapp.migrations.v001.CreateUsersTable --db-file mydb.sqlite --direction up --async

  # Pass parameters to the migration
  %(prog)s myapp.migrations.v001.CreateUsersTable --param table_name=custom_table

  # List available migrations in a module
  %(prog)s myapp.migrations --list

  # Describe a migration (version, dependencies, parameters)
  %(prog)s myapp.migrations.v001.CreateUsersTable --describe

  # Batch: apply all pending migrations in a module
  %(prog)s myapp.migrations --all --record-store ./migrations.json

  # Batch: dry-run all pending migrations
  %(prog)s myapp.migrations --all --record-store ./migrations.json --dry-run

  # Batch: rollback all applied migrations
  %(prog)s myapp.migrations --all --record-store ./migrations.json --direction down

  # Batch: wrap all migrations in a single transaction
  %(prog)s myapp.migrations --all --record-store ./migrations.json --single-transaction

End-to-end demo scripts with UP/DOWN round-trip verification:
  https://github.com/rhosocial/python-activerecord/tree/main/src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations
  PYTHONPATH=src bash demo_basic.sh
  PYTHONPATH=src bash demo_chain.sh
  PYTHONPATH=src bash demo_all.sh
"""

    nm_parser = subparsers.add_parser(
        "named-migration",
        help="Execute a named migration (UP/DOWN)",
        parents=[parent_parser],
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    nm_parser.add_argument(
        "qualified_name",
        help="Fully qualified Python name of the migration class "
        "(e.g. myapp.migrations.v001.CreateUsersTable)",
    )
    nm_parser.add_argument(
        "--direction",
        choices=["up", "down"],
        default="up",
        help="Migration direction (default: up)",
    )
    nm_parser.add_argument(
        "--record-store",
        default=None,
        help="Path to a JSON file or FQN of a MigrationRecordStore class. "
        "When provided, enables dependency checks, duplicate protection, "
        "and execution recording.",
    )
    nm_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the migration without making actual changes.",
    )
    nm_parser.add_argument(
        "--describe",
        action="store_true",
        help="Show migration details without executing.",
    )
    nm_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_migrations",
        help="List all discoverable named migrations in the given module.",
    )
    nm_parser.add_argument(
        "--param",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        dest="params",
        help="Migration parameter. Can be specified multiple times.",
    )
    nm_parser.add_argument(
        "--async",
        action="store_true",
        dest="is_async",
        help="Use async backend for migration execution.",
    )
    nm_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_migrations",
        help="Run all pending migrations in the given module in dependency order. "
        "qualified_name must be a module FQN.  Requires --record-store. "
        "Mutually exclusive with --list and --describe.",
    )
    nm_parser.add_argument(
        "--single-transaction",
        action="store_true",
        dest="single_transaction",
        help="When used with --all, wrap all migrations in a single database "
        "transaction.  On failure the entire batch is rolled back.",
    )
    return nm_parser


def handle_named_migration(
    args: Any,
    provider: Any,
    backend_factory: Callable[[], Any],
    disconnect: Optional[Callable[[], None]] = None,
    backend_async_factory: Optional[Callable[[], Any]] = None,
    disconnect_async: Optional[Callable[[Any], Any]] = None,
) -> None:
    """Handle the ``named-migration`` subcommand.

    Args:
        args: Parsed command-line arguments.
        provider: Output provider for displaying messages.
        backend_factory: Callable that returns a connected backend.
        disconnect: Optional callable to disconnect the backend.
        backend_async_factory: Optional callable that returns an unconnected
            async backend.  Required if ``--async`` is used.
        disconnect_async: Optional coroutine to disconnect the async backend.
    """
    import asyncio

    is_async = getattr(args, "is_async", False)
    if is_async and not backend_async_factory:
        print("Error: --async requires an async backend factory.", file=sys.stderr)
        sys.exit(1)
    if is_async:
        return asyncio.run(
            _handle_named_migration_async(
                args, provider, backend_async_factory, disconnect_async
            )
        )

    _handle_named_migration_sync(args, provider, backend_factory, disconnect)


def _handle_named_migration_sync(
    args: Any,
    provider: Any,
    backend_factory: Callable[[], Any],
    disconnect: Optional[Callable[[], None]] = None,
) -> None:
    qualified_name = args.qualified_name

    # ── --list mode ──────────────────────────────────────────────────
    if args.list_migrations:
        _handle_list_mode(qualified_name, provider)
        return

    # ── --describe mode ──────────────────────────────────────────────
    if args.describe:
        _handle_describe_mode(qualified_name)
        return

    # ── --all mode ───────────────────────────────────────────────────
    if getattr(args, "all_migrations", False):
        _handle_all_mode_sync(
            args, qualified_name, provider, backend_factory, disconnect
        )
        return

    # ── resolve record store ─────────────────────────────────────────
    record_store = _resolve_record_store(args.record_store)

    # ── resolve direction ────────────────────────────────────────────
    direction = MigrationDirection(args.direction)

    # ── parse user params ────────────────────────────────────────────
    user_params = _parse_params(args.params)

    # ── execute ──────────────────────────────────────────────────────
    backend = None
    try:
        runner = MigrationRunner(qualified_name)

        if args.dry_run:
            _print_dry_run_info(runner.migration, direction, record_store, user_params)

        backend = backend_factory()

        from .record import MigrationResult

        result: MigrationResult = runner.run(
            backend=backend,
            direction=direction,
            user_params=user_params,
            record_store=record_store,
            dry_run=args.dry_run,
        )

        _print_result(result, direction)

    except Exception as e:
        _handle_exception(e, provider, is_async=False)
    finally:
        if disconnect and backend:
            disconnect()


# ── shared helper functions ──────────────────────────────────────────────────


def _handle_list_mode(qualified_name: str, provider: Any) -> None:
    try:
        importlib.invalidate_caches()
        module_name = qualified_name
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            if "." in qualified_name:
                parts = qualified_name.rsplit(".", 1)
                module_name = parts[0]
                try:
                    importlib.import_module(module_name)
                except ModuleNotFoundError:
                    print(f"Error: Module not found: {module_name}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(f"Error: Module not found: {module_name}", file=sys.stderr)
                sys.exit(1)

        migrations = list_named_migrations_in_module(module_name)
        if not migrations:
            print(f"No named migrations found in module: {module_name}")
            return

        rows = []
        for m in migrations:
            deps = ", ".join(m["dependencies"]) if m["dependencies"] else "none"
            brief = (m["brief"][:27] + "...") if len(m["brief"]) > 30 else m["brief"]
            rows.append({
                "Name": m["name"],
                "Version": m["version"],
                "Dependencies": deps,
                "Brief": brief,
            })
        provider.print_table(rows, f"Module: {module_name}", ["Name", "Version", "Dependencies", "Brief"])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _handle_describe_mode(qualified_name: str) -> None:
    try:
        from .resolver import NamedMigrationResolver

        cls = NamedMigrationResolver.resolve(qualified_name)
        doc = inspect.getdoc(cls) or "(no docstring)"
        version = getattr(cls, "version", "")
        dependencies = getattr(cls, "dependencies", [])
        params = cls.get_parameters()

        print(f"Migration: {qualified_name}")
        print(f"Version: {version}")
        print(f"Dependencies: {', '.join(dependencies) if dependencies else 'none'}")
        print(f"Docstring: {doc}")
        print("Parameters:")
        if params:
            for pname, pinfo in params.items():
                default_str = f" = {pinfo['default']}" if pinfo["has_default"] else " (required)"
                print(f"  {pname}: {pinfo['annotation']}{default_str}")
        else:
            print("  (none)")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _print_dry_run_info(
    migration: Any, direction: Any, record_store: Any, user_params: dict[str, str]
) -> None:
    print("[DRY RUN] Migration:")
    print(f"  Version: {migration.version}")
    print(f"  Direction: {direction.value}")
    if migration.dependencies:
        print(f"  Dependencies: {', '.join(migration.dependencies)}")
    if record_store:
        print(f"  Record store: {type(record_store).__name__}")
    if user_params:
        print(f"  Parameters: {user_params}")


def _print_result(result: Any, direction: Any) -> None:
    if result.dry_run:
        print(f"[DRY RUN] Migration '{result.version}' ({direction.value})")
        if result.dry_run_sql:
            for fqn, sql, params_sql in result.dry_run_sql:
                print(f"  {fqn}  →  {sql}")
        else:
            print("  (no SQL generated)")
    elif result.success:
        print(f"[OK] Migration '{result.version}' applied ({direction.value})")
    if result.snapshot_diff:
        diff = result.snapshot_diff
        if hasattr(diff, "added_tables") and diff.added_tables:
            print(f"  Tables added: {diff.added_tables}")
        if hasattr(diff, "removed_tables") and diff.removed_tables:
            print(f"  Tables removed: {diff.removed_tables}")


def _handle_exception(e: Exception, provider: Any, is_async: bool = False) -> None:
    from rhosocial.activerecord.backend.errors import ConnectionError
    from rhosocial.activerecord.backend.migration import (
        MigrationDependencyError,
        MigrationAlreadyAppliedError,
        MigrationNotAppliedError,
        MigrationDialectError,
    )

    if isinstance(e, MigrationDependencyError):
        print(f"Error: {e}", file=sys.stderr)
    elif isinstance(e, MigrationAlreadyAppliedError):
        print(f"Warning: {e}", file=sys.stderr)
    elif isinstance(e, MigrationNotAppliedError):
        print(f"Error: {e}", file=sys.stderr)
    elif isinstance(e, MigrationDialectError):
        print(f"Dialect Error: {e}", file=sys.stderr)
    elif isinstance(e, ConnectionError):
        provider.display_connection_error(e)
    else:
        provider.display_unexpected_error(e, is_async=is_async)
    sys.exit(1)


async def _handle_named_migration_async(
    args: Any,
    provider: Any,
    backend_async_factory: Callable[[], Any],
    disconnect_async: Optional[Callable[[Any], Any]] = None,
) -> None:
    """Async execution path for ``handle_named_migration``."""
    qualified_name = args.qualified_name

    # ── --list mode ──────────────────────────────────────────────────
    if args.list_migrations:
        _handle_list_mode(qualified_name, provider)
        return

    # ── --describe mode ──────────────────────────────────────────────
    if args.describe:
        _handle_describe_mode(qualified_name)
        return

    # ── --all mode ───────────────────────────────────────────────────
    if getattr(args, "all_migrations", False):
        await _handle_all_mode_async(
            args, qualified_name, provider, backend_async_factory, disconnect_async,
        )
        return

    # ── resolve record store ─────────────────────────────────────────
    record_store = _resolve_record_store(args.record_store)

    # ── resolve direction ────────────────────────────────────────────
    direction = MigrationDirection(args.direction)

    # ── parse user params ────────────────────────────────────────────
    user_params = _parse_params(args.params)

    # ── execute ──────────────────────────────────────────────────────
    backend = None
    try:
        from .async_runner import AsyncMigrationRunner

        runner = AsyncMigrationRunner(qualified_name)

        if args.dry_run:
            _print_dry_run_info(runner.migration, direction, record_store, user_params)

        backend = await backend_async_factory()

        from .record import MigrationResult

        result: MigrationResult = await runner.run(
            backend=backend,
            direction=direction,
            user_params=user_params,
            record_store=record_store,
            dry_run=args.dry_run,
        )

        _print_result(result, direction)

    except Exception as e:
        _handle_exception(e, provider, is_async=True)
    finally:
        if disconnect_async and backend:
            await disconnect_async(backend)


# ── --all mode helpers ───────────────────────────────────────────────────────


def _handle_all_mode_sync(
    args: Any,
    module_name: str,
    provider: Any,
    backend_factory: Callable[[], Any],
    disconnect: Optional[Callable[[], None]],
) -> None:
    from .batch_runner import BatchMigrationRunner

    record_store = _require_record_store(args)
    direction = MigrationDirection(args.direction)
    user_params = _parse_params(args.params)
    single_transaction = getattr(args, "single_transaction", False)

    batch = BatchMigrationRunner(module_name)

    backend = None
    try:
        if args.dry_run:
            _print_batch_dry_run(batch, direction, record_store)

        backend = backend_factory()

        if direction == MigrationDirection.UP:
            results = batch.migrate_up(
                backend, record_store=record_store, user_params=user_params,
                dry_run=args.dry_run, single_transaction=single_transaction,
            )
        else:
            results = batch.migrate_down(
                backend, record_store=record_store, user_params=user_params,
                dry_run=args.dry_run, single_transaction=single_transaction,
            )

        _print_batch_result(results, batch, direction)
    except Exception as e:
        _handle_exception(e, provider, is_async=False)
    finally:
        if disconnect and backend:
            disconnect()


async def _handle_all_mode_async(
    args: Any,
    module_name: str,
    provider: Any,
    backend_async_factory: Callable[[], Any],
    disconnect_async: Optional[Callable[[Any], Any]],
) -> None:
    from .batch_runner import BatchMigrationRunner
    from .async_runner import AsyncMigrationRunner
    from .core import MigrationDirection

    record_store = _require_record_store(args)
    direction = MigrationDirection(args.direction)
    user_params = _parse_params(args.params)
    single_transaction = getattr(args, "single_transaction", False)

    batch = BatchMigrationRunner(module_name)

    backend = None
    try:
        if args.dry_run:
            _print_batch_dry_run(batch, direction, record_store)

        backend = await backend_async_factory()

        ordered = batch._topological_order()
        if direction == MigrationDirection.DOWN:
            ordered = list(reversed(ordered))

        results: list[Any] = []
        in_outer_transaction = False

        def begin_outer():
            nonlocal in_outer_transaction
            if not single_transaction or args.dry_run or in_outer_transaction:
                return
            backend.begin_transaction()
            in_outer_transaction = True

        def commit_outer():
            nonlocal in_outer_transaction
            if in_outer_transaction:
                backend.commit_transaction()
                in_outer_transaction = False

        def rollback_outer():
            nonlocal in_outer_transaction
            if in_outer_transaction:
                try:
                    backend.rollback_transaction()
                except Exception:
                    pass
                in_outer_transaction = False

        try:
            begin_outer()
            for _version, fqn, _ in ordered:
                runner = AsyncMigrationRunner(fqn)
                result = await runner.run(
                    backend=backend,
                    direction=direction,
                    user_params=user_params,
                    record_store=record_store,
                    dry_run=args.dry_run,
                    manage_transaction=not single_transaction,
                )
                results.append(result)
            commit_outer()
        except Exception:
            rollback_outer()
            raise

        _print_batch_results_summary(results, batch, direction)
    except Exception as e:
        _handle_exception(e, provider, is_async=True)
    finally:
        if disconnect_async and backend:
            await disconnect_async(backend)


def _require_record_store(args: Any) -> Any:
    if not args.record_store:
        print("Error: --record-store is required with --all.", file=sys.stderr)
        sys.exit(1)
    return _resolve_record_store(args.record_store)


def _print_batch_dry_run(
    batch: Any, direction: Any, record_store: Any,
) -> None:
    print(f"[DRY RUN] Module: {batch._module_name}")
    print(f"  Direction: {direction.value}")
    print(f"  Migrations discovered: {len(batch.discovered)}")
    if record_store:
        print(f"  Record store: {type(record_store).__name__}")


def _print_batch_result(
    results: list[Any], batch: Any, direction: Any,
) -> None:
    applied_count = sum(1 for r in results if r.success)
    print(f"[OK] {applied_count}/{len(results)} migrations applied ({direction.value})")
    rows = []
    for r in results:
        rows.append({
            "Version": r.version,
            "Status": "OK" if r.success else "FAIL",
        })
    _print_simple_table(["Version", "Status"], rows)


def _print_batch_results_summary(
    results: list[Any], batch: Any, direction: Any,
) -> None:
    applied_count = sum(1 for r in results if r.success)
    print(f"[OK] {applied_count}/{len(results)} migrations applied ({direction.value})")
    rows = []
    for r in results:
        rows.append({
            "Version": r.version,
            "Status": "OK" if r.success else "FAIL",
        })
    _print_simple_table(["Version", "Status"], rows)


def _print_simple_table(columns: list[str], rows: list[dict[str, str]]) -> None:
    col_widths = {c: len(c) for c in columns}
    for row in rows:
        for c in columns:
            col_widths[c] = max(col_widths[c], len(str(row.get(c, ""))))
    header = "  " + " | ".join(c.ljust(col_widths[c]) for c in columns)
    sep = "  " + "-+-".join("-" * col_widths[c] for c in columns)
    print(header)
    print(sep)
    for row in rows:
        line = "  " + " | ".join(str(row.get(c, "")).ljust(col_widths[c]) for c in columns)
        print(line)
