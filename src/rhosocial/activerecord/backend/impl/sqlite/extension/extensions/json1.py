# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/json1.py
"""
SQLite JSON1 extension implementation.

The JSON1 extension provides functions for processing and manipulating
JSON data. It became a built-in extension in SQLite 3.38.0 (2022-02-22).

Note: JSON functions are built-in since SQLite 3.38.0.
Earlier versions may need to load the extension manually.

Reference: https://www.sqlite.org/json1.html
"""

from ..base import ExtensionType, SQLiteExtensionBase


class JSON1Extension(SQLiteExtensionBase):
    """JSON1 (JSON functions) extension.

    Provides metadata and version detection for JSON1.
    JSON SQL generation is handled by the core expression system
    (JSONExpression, FunctionCall) and sqlite/functions/json.py.

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
            min_version=(3, 38, 0),
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
