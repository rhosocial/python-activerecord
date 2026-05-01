# src/rhosocial/activerecord/backend/impl/sqlite/cli/output.py
"""Output provider factory and rich display utilities."""

import json
from typing import Dict

from rhosocial.activerecord.backend.output import JsonOutputProvider, CsvOutputProvider, TsvOutputProvider

try:
    from rhosocial.activerecord.backend.output_rich import RichOutputProvider
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    RichOutputProvider = None  # type: ignore[misc,assignment]


def create_provider(output_format: str, ascii_borders: bool = False):
    """Create an output provider based on format.

    Args:
        output_format: Output format (table/json/csv/tsv)
        ascii_borders: Whether to use ASCII borders (table format only)

    Returns:
        OutputProvider instance
    """
    if output_format == "table" and not RICH_AVAILABLE:
        output_format = "json"

    if output_format == "table" and RICH_AVAILABLE:
        from rich.console import Console
        return RichOutputProvider(console=Console(), ascii_borders=ascii_borders)
    if output_format == "json":
        return JsonOutputProvider()
    if output_format == "csv":
        return CsvOutputProvider()
    if output_format == "tsv":
        return TsvOutputProvider()

    return JsonOutputProvider()


def display_nested_json(data: Dict, indent: int = 2):
    """Display nested structure as JSON (for info, status all, etc.)."""
    print(json.dumps(data, indent=indent))
