# src/rhosocial/activerecord/cli/commands/migrate.py
"""The ``migrate`` command group: run function migrations as one unit.

The group mechanics live in
``rhosocial.activerecord.backend.migration.group``; this module only resolves
names, record-store arguments, and prints the result.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, List, Optional, Sequence

from rhosocial.activerecord.backend.migration.core import MigrationDirection
from rhosocial.activerecord.backend.migration.functions import (
    MigrationFunctionError,
    MigrationFunctionRef,
    resolve_migration_function,
)
from rhosocial.activerecord.backend.migration.group import (
    run_migration_group,
    run_migration_group_async,
)
from rhosocial.activerecord.backend.migration.record import (
    JSONFileMigrationRecordStore,
    MigrationRecordStore,
)

#: The default output format. A signature default repeated under one name is a
#: value written in several places with nothing tying them together; naming it
#: once is what the constant-discipline rule asks for.
OUTPUT_FORMAT_TEXT = "text"

from ..errors import EXIT_USAGE, CLIError

#: How many rendered statements a dry run prints before summarising the rest.
DRY_RUN_DISPLAY_LIMIT = 100


def resolve_record_store(specification: Optional[str]) -> Optional[MigrationRecordStore]:
    """Resolve ``--record-store`` to a record store, or ``None``."""
    if not specification:
        return None
    if specification.endswith(".json") or "/" in specification or "\\" in specification:
        return JSONFileMigrationRecordStore(Path(specification))
    if ":" not in specification and "." not in specification:
        raise CLIError(
            f'Invalid --record-store "{specification}": use a .json path or ' "module:Class"
        )
    if ":" in specification:
        module_path, attribute = specification.rsplit(":", 1)
    else:
        module_path, attribute = specification.rsplit(".", 1)
    try:
        module = importlib.import_module(module_path)
        store_class = getattr(module, attribute)
        store = store_class()
    except Exception as exc:
        raise CLIError(f'Cannot resolve --record-store "{specification}": {exc}') from None
    if not isinstance(store, MigrationRecordStore):
        raise CLIError(
            f'--record-store "{specification}" produced {type(store).__name__}, '
            "not a MigrationRecordStore",
            exit_code=EXIT_USAGE,
        )
    return store


def load_functions(references: Sequence[str]) -> List[MigrationFunctionRef]:
    """Resolve every FQN, reporting the first bad reference as a CLI error."""
    if not references:
        raise CLIError(
            "migrate needs at least one migration function FQN",
            exit_code=EXIT_USAGE,
        )
    resolved: List[MigrationFunctionRef] = []
    for reference in references:
        try:
            resolved.append(resolve_migration_function(reference))
        except ImportError as exc:
            raise CLIError(f'Cannot import migration function "{reference}": {exc}') from None
        except MigrationFunctionError as exc:
            raise CLIError(str(exc), exit_code=EXIT_USAGE) from None
    return resolved


def _json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)


def _emit_json(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, default=_json_safe))


def print_functions(
    functions: Sequence[MigrationFunctionRef],
    direction: MigrationDirection,
    *,
    plan: bool,
    output: str = OUTPUT_FORMAT_TEXT,
) -> None:
    """Print the function list or execution order."""
    ordered = list(reversed(functions)) if direction == MigrationDirection.DOWN else list(functions)
    if output == "json":
        rows = [
            {
                "version": function.info.version,
                "fqn": function.fqn,
                "kind": "async" if function.is_async else "sync",
                "dependencies": list(function.info.dependencies),
            }
            for function in ordered
        ]
        if plan:
            _emit_json(
                {
                    "command": "migrate",
                    "mode": "plan",
                    "direction": direction.value,
                    "order": rows,
                }
            )
        else:
            _emit_json({"command": "migrate", "mode": "list", "functions": rows})
        return

    if plan:
        print(f"Execution order ({direction.value}):")
    else:
        print("Migration functions:")
    for function in ordered:
        info = function.info
        kind = "async" if function.is_async else "sync"
        if plan:
            print(f"  {info.version}  {function.fqn}  ({kind})")
            continue
        dependencies = ", ".join(info.dependencies) or "(none)"
        print(f"  {info.version}  {function.fqn}  [{kind}] " f"dependencies: {dependencies}")


def print_result(result, direction: MigrationDirection, output: str = OUTPUT_FORMAT_TEXT) -> None:
    """Print a group result."""
    if output == "json":
        _emit_json(
            {
                "command": "migrate",
                "success": True,
                "direction": direction.value,
                "dry_run": result.dry_run,
                "versions": result.versions,
                "applied": result.applied,
                "rolled_back": result.rolled_back,
                "records_written": result.records_written,
                "dry_run_total": result.dry_run_total,
                "statements": [
                    {"label": label, "sql": sql, "params": params}
                    for label, sql, params in result.dry_run_sql
                ],
            }
        )
        return

    if result.dry_run:
        print(f"-- would run {len(result.versions)} migration(s) ({direction.value})")
        for label, sql, params in result.dry_run_sql:
            if params:
                print(f"-- {label}: {sql}  params={params}")
            else:
                print(f"-- {label}: {sql}")
        remaining = result.dry_run_total - len(result.dry_run_sql)
        if remaining > 0:
            print(f"-- ... {remaining} more statement(s) not shown")
        print(f"-- {result.dry_run_total} statement(s) rendered; no changes written")
        return

    action = "applied" if direction == MigrationDirection.UP else "rolled back"
    for version in result.versions:
        print(f"{action} {version}")
    print(f"{action} {len(result.versions)} migration(s)")


def execute_sync(
    functions: Sequence[MigrationFunctionRef],
    direction: MigrationDirection,
    backend: Any,
    record_store: Optional[MigrationRecordStore],
    *,
    dry_run: bool = False,
    output: str = OUTPUT_FORMAT_TEXT,
) -> None:
    """Run a synchronous migration group and print the outcome."""
    result = run_migration_group(
        backend,
        functions,
        direction=direction,
        record_store=record_store,
        dry_run=dry_run,
    )
    print_result(result, direction, output)


async def execute_async(
    functions: Sequence[MigrationFunctionRef],
    direction: MigrationDirection,
    backend: Any,
    record_store: Optional[MigrationRecordStore],
    *,
    dry_run: bool = False,
    output: str = OUTPUT_FORMAT_TEXT,
) -> None:
    """Run an asynchronous migration group and print the outcome."""
    result = await run_migration_group_async(
        backend,
        functions,
        direction=direction,
        record_store=record_store,
        dry_run=dry_run,
    )
    print_result(result, direction, output)
