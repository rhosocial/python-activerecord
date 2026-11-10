# src/rhosocial/activerecord/cli/output.py
"""Output rendering for the ActiveRecord model CLI.

Machine formats (``json``, ``jsonl``, ``csv``, ``tsv``, ``value``) write only
data to stdout. Human ``table`` output uses Rich when available and falls back
to JSON.
"""

import csv
import datetime
import decimal
import json
import sys
from typing import Any, Dict, Iterable, List, Optional

from .errors import CLIError

try:
    import rich  # noqa: F401

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def _available_fields(model, rows=None) -> List[str]:
    if model is not None:
        return list(model.model_fields.keys())
    if rows:
        return list(rows[0].keys())
    return []


def selected_fields(model, fields_argument: Optional[str], rows=None) -> List[str]:
    """Return the field names to render, validating ``--fields``."""
    available = _available_fields(model, rows)
    if not available:
        if rows is not None:
            return []
        raise CLIError("Cannot determine output fields without a model or row data")
    if not fields_argument:
        return available
    requested = [part.strip() for part in fields_argument.split(",") if part.strip()]
    if not requested:
        raise CLIError("--fields must name at least one field")
    unknown = [name for name in requested if name not in available]
    if unknown:
        owner = model.__name__ if model is not None else "row data"
        raise CLIError(
            f"Unknown field(s) for {owner}: {', '.join(unknown)}. "
            f"Available fields: {', '.join(available)}"
        )
    return requested


def record_to_dict(record, fields: List[str]) -> Dict[str, Any]:
    """Serialize a model instance or dict row to a JSON-compatible dict."""
    if isinstance(record, dict):
        return {field: record.get(field) for field in fields}
    dumped = record.model_dump(mode="json")
    return {field: dumped.get(field) for field in fields}


def _json_default(value):
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    return str(value)


def _write_json(data: Any) -> None:
    sys.stdout.write(
        json.dumps(data, indent=2, ensure_ascii=False, default=_json_default) + "\n"
    )


def _write_jsonl(data: Any) -> None:
    sys.stdout.write(
        json.dumps(data, ensure_ascii=False, default=_json_default) + "\n"
    )


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=_json_default)
    return str(value)


def _scalar_text(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _write_delimited(rows: Iterable[Dict[str, Any]], fields: List[str], delimiter: str, no_header):
    writer = csv.writer(sys.stdout, delimiter=delimiter)
    if not no_header:
        writer.writerow(fields)
    for row in rows:
        writer.writerow([_format_cell(row.get(field)) for field in fields])


def _rich_modules():
    """Import the Rich pieces on demand, or return None when unavailable."""
    if not RICH_AVAILABLE:
        return None
    try:
        from rich import box
        from rich.console import Console
        from rich.table import Table

        return box, Console, Table
    except ImportError:
        return None


def _box(box_module, rich_ascii: bool):
    return box_module.ASCII if rich_ascii else box_module.ROUNDED


def render_list(
    records,
    model,
    fields: List[str],
    output_format: str,
    rich_ascii: bool,
    no_header: bool = False,
) -> None:
    """Render a list of model instances or dict rows."""
    rows = [record_to_dict(record, fields) for record in records]
    if output_format == "json":
        _write_json(rows)
        return
    if output_format == "jsonl":
        for row in rows:
            _write_jsonl(row)
        return
    if output_format == "csv":
        _write_delimited(rows, fields, ",", no_header)
        return
    if output_format == "tsv":
        _write_delimited(rows, fields, "\t", no_header)
        return
    if output_format == "value":
        raise CLIError("-o value is only valid for scalar results")

    rich_modules = _rich_modules()
    if rich_modules is None:
        _write_json(rows)
        return

    box_module, Console, Table = rich_modules
    console = Console()
    table = Table(box=_box(box_module, rich_ascii), show_header=True, header_style="bold")
    for field in fields:
        table.add_column(field, overflow="fold")
    for row in rows:
        table.add_row(*[_format_cell(row.get(field)) for field in fields])
    console.print(table)
    if not rows:
        owner = model.__name__ if model is not None else "result"
        console.print(f"No records in {owner}", style="dim")


def render_record(
    record,
    model,
    fields: List[str],
    output_format: str,
    rich_ascii: bool,
) -> None:
    """Render one model instance or dict row."""
    row = record_to_dict(record, fields)
    if output_format == "json":
        _write_json(row)
        return
    if output_format == "jsonl":
        _write_jsonl(row)
        return
    if output_format == "value":
        raise CLIError("-o value is only valid for scalar results")
    if output_format in ("csv", "tsv"):
        delimiter = "," if output_format == "csv" else "\t"
        _write_delimited([row], fields, delimiter, False)
        return

    rich_modules = _rich_modules()
    if rich_modules is None:
        _write_json(row)
        return
    box_module, Console, Table = rich_modules
    console = Console()
    table = Table(box=_box(box_module, rich_ascii), show_header=True, header_style="bold")
    table.add_column("Field")
    table.add_column("Value")
    for field in fields:
        table.add_row(field, _format_cell(row.get(field)))
    console.print(table)


def render_scalar(value: Any, output_format: str) -> None:
    """Render a scalar result (count, exists, non-grouped aggregate)."""
    if output_format in ("json", "table"):
        _write_json(value)
        return
    if output_format == "jsonl":
        _write_jsonl(value)
        return
    if output_format == "value":
        sys.stdout.write(_scalar_text(value) + "\n")
        return
    if output_format in ("csv", "tsv"):
        sys.stdout.write(_format_cell(value) + "\n")
        return
    raise CLIError(f"Unsupported output format: {output_format}")


def render_affected(action: str, affected: int, output_format: str, **extra) -> None:
    """Render the result of a bulk update/delete."""
    payload = {"action": action, "affected": affected}
    payload.update(extra)
    if output_format == "json":
        _write_json(payload)
        return
    if output_format == "jsonl":
        _write_jsonl(payload)
        return
    if output_format == "value":
        sys.stdout.write(f"{affected}\n")
        return
    if output_format in ("csv", "tsv"):
        _write_json(payload)
        return
    _write_json(payload)


def render_delete(
    pk: Any,
    affected: int,
    model,
    output_format: str,
    rich_ascii: bool,
    action: str = "delete",
    deleted_at_field: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """Render a single delete result or dry-run plan."""
    payload = {"action": action, "pk": pk, "affected": affected}
    if deleted_at_field:
        payload["deleted_at_field"] = deleted_at_field
    if dry_run:
        payload["dry_run"] = True
    if output_format == "value":
        sys.stdout.write(f"{affected}\n")
        return
    if output_format in ("json", "jsonl", "table"):
        _write_json(payload)
        return
    _write_json(payload)
