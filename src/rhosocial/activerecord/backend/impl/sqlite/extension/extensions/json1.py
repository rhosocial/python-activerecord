# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/json1.py
"""
SQLite JSON1 extension implementation.

The JSON1 extension provides functions for processing and manipulating
JSON data. It became a built-in extension in SQLite 3.38.0 (2022-02-22).

Note: JSON functions are built-in since SQLite 3.38.0.
Earlier versions may need to load the extension manually.

Reference: https://www.sqlite.org/json1.html
"""

from typing import Dict, List, Optional, Tuple, Any

from ..base import ExtensionType, SQLiteExtensionBase


class JSON1Extension(SQLiteExtensionBase):
    """JSON1 (JSON functions) extension.

    The JSON1 extension provides comprehensive JSON processing capabilities
    for SQLite, including extraction, modification, and querying of JSON data.

    Features:
        - json_extract() and -> / ->> operators
        - json_array() and json_object() constructors
        - json_each() and json_tree() for iterating JSON structures
        - json_patch() and json_remove() for modifications
        - json_type() and json_valid() for validation
        - json_group_array() and json_group_object() aggregates

    Example:
        >>> json1 = JSON1Extension()
        >>> json1.is_available((3, 38, 0))
        True
        >>> json1.check_feature('json_arrow_operators', (3, 38, 0))
        True
    """

    def __init__(self):
        """Initialize JSON1 extension."""
        super().__init__(
            name="json1",
            extension_type=ExtensionType.BUILTIN,
            min_version=(3, 38, 0),  # Built-in since 3.38.0
            deprecated=False,
            description="JSON functions - JSON processing and manipulation",
            features={
                "json_functions": {"min_version": (3, 38, 0)},
                "json_array": {"min_version": (3, 38, 0)},
                "json_object": {"min_version": (3, 38, 0)},
                "json_extract": {"min_version": (3, 38, 0)},
                "json_arrow_operators": {"min_version": (3, 38, 0)},
                "json_each": {"min_version": (3, 38, 0)},
                "json_tree": {"min_version": (3, 38, 0)},
                "json_patch": {"min_version": (3, 38, 0)},
                "json_remove": {"min_version": (3, 38, 0)},
                "json_type": {"min_version": (3, 38, 0)},
                "json_valid": {"min_version": (3, 38, 0)},
                "json_group_array": {"min_version": (3, 38, 0)},
                "json_group_object": {"min_version": (3, 38, 0)},
                "json_insert": {"min_version": (3, 38, 0)},
                "json_replace": {"min_version": (3, 38, 0)},
                "json_set": {"min_version": (3, 38, 0)},
                "json_quote": {"min_version": (3, 38, 0)},
            },
            documentation_url="https://www.sqlite.org/json1.html",
        )

    def format_json_extract(
        self,
        column: str,
        path: str,
        arrow_operator: bool = True,
    ) -> Tuple[str, tuple]:
        """Format JSON extract expression.

        Args:
            column: Column or expression containing JSON
            path: JSON path expression
            arrow_operator: Use -> operator instead of json_extract()

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if arrow_operator:
            sql = f'"{column}" -> ?'
            return sql, (path,)
        else:
            sql = f'json_extract("{column}", ?)'
            return sql, (path,)

    def format_json_extract_text(
        self,
        column: str,
        path: str,
    ) -> Tuple[str, tuple]:
        """Format JSON extract text expression (->> operator).

        Args:
            column: Column or expression containing JSON
            path: JSON path expression

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f'"{column}" ->> ?'
        return sql, (path,)

    def format_json_array(
        self,
        elements: List[str],
    ) -> Tuple[str, tuple]:
        """Format json_array() expression.

        Args:
            elements: List of element expressions

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        elem_str = ", ".join("?" for _ in elements)
        sql = f"json_array({elem_str})"
        return sql, tuple(elements)

    def format_json_object(
        self,
        key_values: Dict[str, Any],
    ) -> Tuple[str, tuple]:
        """Format json_object() expression.

        Args:
            key_values: Dictionary of key-value pairs

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        params = []
        pairs = []
        for key, value in key_values.items():
            pairs.append("?, ?")
            params.extend([key, value])

        sql = f"json_object({', '.join(pairs)})"
        return sql, tuple(params)


# Singleton instance
_json1_extension: Optional[JSON1Extension] = None


def get_json1_extension() -> JSON1Extension:
    """Get the JSON1 extension singleton.

    Returns:
        JSON1Extension instance
    """
    global _json1_extension
    if _json1_extension is None:
        _json1_extension = JSON1Extension()
    return _json1_extension
