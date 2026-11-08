# src/rhosocial/activerecord/cli/output.py
"""Output rendering for the ActiveRecord model CLI.

Machine formats (``json``, ``csv``, ``tsv``) write only data to stdout.
Human ``table`` output uses Rich when available and falls back to JSON.
"""

import csv
import datetime
import decimal
import json
import sys
from typing import Any, Dict, Iterable, List, Optional

from .args import OUTPUT_FORMATS
from .errors import CLIError

try:
    import rich  # noqa: F401

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def _available_fields(model) -> List[str]:
    return list(model.model_fields.keys())


def selected_fields(model, fields_argument: Optional[str]) -> List[str]:
    """Return the field names to render, validating ``--fields``."""
    available = _available_fields(model)
    if not fields_argument:
        return available
    requested = [part.strip() for part in fields_argument.split(",") if part.strip()]
    if not requested:
        raise CLIError("--fields must name at least one field")
    unknown = [name for name in requested if name not in available]
    if unknown:
        raise CLIError(
            f"Unknown field(s) for {model.__name__}: {', '.join(unknown)}. "
            f"Available fields: {', '.join(available)}"
        )
    return requested


def record_to_dict(record, fields: List[str]) -> Dict[str, Any]:
    """Serialize a model instance to a JSON-compatible dict."""
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


def _write_delimited(rows: Iterable[Dict[str, Any]], fields: List[str], delimiter: str) -> None:
    writer = csv.writer(sys.stdout, delimiter=delimiter)
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
        from rich.panel import Panel
        from rich.table import Table

        return box, Console, Panel, Table
    except ImportError:
        return None


def _box(box_module, rich_ascii: bool):
    return box_module.ASCII if rich_ascii else box_module.ROUNDED


def render_list(records, model, fields: List[str], output_format: str, rich_ascii: bool) -> None:
    """Render a list of records."""
    rows = [record_to_dict(record, fields) for record in records]
    if output_format == "json":
        _write_json(rows)
        return
    if output_format == "csv":
        _write_delimited(rows, fields, ",")
        return
    if output_format == "tsv":
        _write_delimited(rows, fields, "\t")
        return

    rich_modules = _rich_modules()
    if rich_modules is None:
        _write_json(rows)
        return

    box_module, Console, _Panel, Table = rich_modules
    console = Console()
    table = Table(box=_box(box_module, rich_ascii), show_header=True, header_style="bold")
    for field in fields:
        table.add_column(field, overflow="fold")
    for row in rows:
        table.add_row(*[_format_cell(row.get(field)) for field in fields])
    console.print(table)
    if not rows:
        console.print(f"No records in {model.__name__}", style="dim")


def render_record(record, model, fields: List[str], output_format: str, rich_ascii: bool) -> None:
    """Render one record."""
    row = record_to_dict(record, fields)
    if output_format == "json":
        _write_json(row)
        return
    if output_format == "csv":
        _write_delimited([row], fields, ",")
        return
    if output_format == "tsv":
        _write_delimited([row], fields, "\t")
        return

    rich_modules = _rich_modules()
    if rich_modules is None:
        _write_json(row)
        return

    box_module, Console, _Panel, Table = rich_modules
    console = Console()
    table = Table(
        title=model.__name__,
        box=_box(box_module, rich_ascii),
        show_header=True,
        header_style="bold",
    )
    table.add_column("Field")
    table.add_column("Value", overflow="fold")
    for field in fields:
        table.add_row(field, _format_cell(row.get(field)))
    console.print(table)


def render_delete(pk: Any, affected: int, model, output_format: str, rich_ascii: bool) -> None:
    """Render a delete summary."""
    summary = {"deleted": affected, "pk": pk}
    if output_format == "json":
        _write_json(summary)
        return
    if output_format in ("csv", "tsv"):
        delimiter = "," if output_format == "csv" else "\t"
        _write_delimited([{"deleted": affected, "pk": _format_cell(pk)}], ["deleted", "pk"], delimiter)
        return

    rich_modules = _rich_modules()
    if rich_modules is None:
        _write_json(summary)
        return
    box_module, Console, Panel, _Table = rich_modules
    console = Console()
    console.print(
        Panel(
            f"Deleted {affected} record(s) from {model.__name__} with pk={pk!r}",
            title="Delete",
            box=_box(box_module, rich_ascii),
        )
    )


def validate_output_format(value: str) -> str:
    """Fail early when an unknown format reaches the renderer."""
    if value not in OUTPUT_FORMATS:
        raise CLIError(f"Unknown output format {value!r}")
    return value
