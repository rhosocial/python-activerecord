# src/rhosocial/activerecord/cli/input.py
"""Input parsing for the ActiveRecord model CLI.

The CLI accepts data as inline JSON, a file, stdin, or JSONL.  This module keeps
the parsing in one place so DML commands can share it without duplicating the
"object vs. array vs. JSONL" rules.
"""

import json
import sys
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter, ValidationError

from .errors import CLIError


def _read_text(argument: str) -> str:
    """Read ``--data`` as inline text, ``@FILE``, ``@-``, or ``-``."""
    if argument == "@-" or argument == "-":
        return sys.stdin.read()
    if argument.startswith("@"):
        filename = argument[1:]
        try:
            with open(filename, encoding="utf-8") as handle:
                return handle.read()
        except OSError as exc:
            raise CLIError(f'Cannot read data file "{filename}": {exc}') from None
    return argument


def _json_error(text: str, exc: Exception, label: str = "--data") -> CLIError:
    line = getattr(exc, "lineno", None)
    column = getattr(exc, "colno", None)
    location = f" at line {line}, column {column}" if line and column else ""
    return CLIError(f"{label} is not valid JSON{location}: {exc}")


def read_object(argument: str, label: str = "--data") -> Dict[str, Any]:
    """Read a single JSON object from inline, file, or stdin."""
    text = _read_text(argument)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise _json_error(text, exc, label) from None
    if not isinstance(data, dict):
        raise CLIError(f"{label} must be a JSON object")
    return data


def _parse_jsonl(text: str, label: str) -> List[Any]:
    values = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            values.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise CLIError(
                f"{label} line {number} is not valid JSON: {exc}"
            ) from None
    return values


def read_records(
    argument: str,
    input_format: Optional[str] = None,
    label: str = "--data",
) -> List[Dict[str, Any]]:
    """Read one or more JSON objects from inline, file, stdin, JSON array, or JSONL."""
    text = _read_text(argument)
    stripped = text.lstrip()
    if input_format == "jsonl":
        values = _parse_jsonl(text, label)
    elif input_format == "json":
        try:
            values = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _json_error(text, exc, label) from None
        if isinstance(values, dict):
            values = [values]
        if not isinstance(values, list):
            raise CLIError(f"{label} must be a JSON object or array")
    elif stripped.startswith("["):
        try:
            values = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _json_error(text, exc, label) from None
    elif stripped.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # A multi-line stream of objects (JSONL) commonly starts with ``{``.
            values = _parse_jsonl(text, label)
        else:
            values = [parsed]
    else:
        values = _parse_jsonl(text, label)

    if not isinstance(values, list):
        values = [values]
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise CLIError(f"{label} item {index + 1} must be a JSON object")
    if not values:
        raise CLIError(f"{label} contains no records")
    return values


def read_values(
    argument: str,
    input_format: Optional[str] = None,
    label: str = "--data",
) -> List[Any]:
    """Read values for bulk delete: scalars, arrays, objects, or JSONL."""
    text = _read_text(argument)
    stripped = text.lstrip()
    if input_format == "jsonl":
        values = _parse_jsonl(text, label)
    elif input_format == "json":
        try:
            values = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _json_error(text, exc, label) from None
    elif stripped.startswith("["):
        try:
            values = json.loads(text)
        except json.JSONDecodeError as exc:
            raise _json_error(text, exc, label) from None
    elif stripped.startswith("{"):
        try:
            values = json.loads(text)
        except json.JSONDecodeError:
            values = _parse_jsonl(text, label)
    else:
        values = _parse_jsonl(text, label)

    if not isinstance(values, list):
        values = [values]
    if not values:
        raise CLIError(f"{label} contains no values")
    return values


def check_fields(model, data: Dict[str, Any]) -> None:
    """Reject unknown model fields before constructing a record."""
    unknown = [key for key in data if key not in model.model_fields]
    if unknown:
        raise CLIError(
            f"Unknown field(s) for {model.__name__}: {', '.join(unknown)}. "
            f"Available fields: {', '.join(model.model_fields)}"
        )


def field_adapter(model, field_name: str):
    """Return the Pydantic adapter for one model field."""
    return TypeAdapter(model.model_fields[field_name].annotation)


def convert_field(model, field_name: str, value: Any) -> Any:
    """Convert a decoded JSON value to the field's declared Python type."""
    try:
        return field_adapter(model, field_name).validate_python(value)
    except ValidationError as exc:
        raise CLIError(f"Invalid value for {field_name}: {exc}") from None


def coerce_filter_value(model, field_name: str, value: Any) -> Any:
    """Best-effort conversion for ``--where`` values."""
    try:
        return field_adapter(model, field_name).validate_python(value)
    except ValidationError:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return value
            try:
                return field_adapter(model, field_name).validate_python(parsed)
            except ValidationError:
                return value
        return value


def coerce_pk_value(model, field_name: str, value: Any) -> Any:
    """Convert one primary-key component, with a precise CLI error."""
    try:
        return field_adapter(model, field_name).validate_python(value)
    except ValidationError as exc:
        raise CLIError(f"Invalid primary key value for {field_name}: {exc}") from None
