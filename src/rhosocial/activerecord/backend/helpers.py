# src/rhosocial/activerecord/backend/helpers.py
from typing import Any, Dict


def format_with_length(base_type: str, params: Dict[str, Any]) -> str:
    """Process type with length parameter

    Args:
        base_type: Base type name
        params: Type parameters

    Returns:
        str: Formatted type string with length if specified
    """
    length = params.get('length')
    return f"{base_type}({length})" if length else base_type