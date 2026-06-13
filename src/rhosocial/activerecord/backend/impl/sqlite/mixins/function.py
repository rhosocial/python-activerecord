# src/rhosocial/activerecord/backend/impl/sqlite/mixins/function.py
"""
SQLite-specific Function implementation.

This module provides the SQLiteFunctionMixin class.
"""

from typing import Dict


class SQLiteFunctionMixin:
    """SQLite function version support detection."""

    _SQLITE_FUNCTION_VERSIONS = {
        "json_extract": ((3, 38, 0), None),
        "json_extract_text": ((3, 38, 0), None),
        "json_build_object": (None, (0, 0, 0)),
        "json_array_elements": (None, (0, 0, 0)),
        "json_objectagg": (None, (0, 0, 0)),
        "json_arrayagg": (None, (0, 0, 0)),
        "json": (None, None),
        "json_array": (None, None),
        "json_object": (None, None),
        "json_type": (None, None),
        "json_valid": (None, None),
        "json_quote": (None, None),
        "json_remove": (None, None),
        "json_set": (None, None),
        "json_insert": (None, None),
        "json_replace": (None, None),
        "json_patch": (None, None),
        "json_array_length": (None, None),
        "json_array_unpack": (None, None),
        "json_object_pack": (None, None),
        "json_object_retrieve": (None, None),
        "json_object_length": (None, None),
        "json_object_keys": (None, None),
        "json_tree": (None, None),
        "json_each": (None, None),
        "json_array_insert": ((3, 53, 0), None),
        "jsonb_array_insert": ((3, 53, 0), None),
        "substr": (None, None),
        "instr": (None, None),
        "printf": (None, None),
        "unicode": (None, None),
        "hex": (None, None),
        "unhex": ((3, 45, 0), None),
        "soundex": (None, None),
        "group_concat": (None, None),
        "trim_sqlite": (None, None),
        "ltrim": (None, None),
        "rtrim": (None, None),
        "date_func": (None, None),
        "time_func": (None, None),
        "datetime_func": (None, None),
        "julianday": (None, None),
        "strftime_func": (None, None),
        "random_func": (None, None),
        "abs_sql": (None, None),
        "sign": ((3, 21, 0), None),
        "total": (None, None),
        "round_": (None, None),
        "pow": ((3, 35, 0), None),
        "power": ((3, 35, 0), None),
        "sqrt": ((3, 35, 0), None),
        "mod": ((3, 35, 0), None),
        "ceil": ((3, 35, 0), None),
        "floor": ((3, 35, 0), None),
        "trunc": ((3, 35, 0), None),
        "max_": (None, None),
        "min_": (None, None),
        "avg": (None, None),
        "zeroblob": (None, None),
        "randomblob": (None, None),
        "typeof": (None, None),
        "quote": (None, None),
        "last_insert_rowid": (None, None),
        "changes": (None, None),
        "iif": ((3, 32, 0), None),
    }

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping."""
        from rhosocial.activerecord.backend.expression.functions import (
            __all__ as core_functions,
        )
        from rhosocial.activerecord.backend.impl.sqlite import functions as sqlite_functions

        expression_constructors = {
            "xmlagg", "xmlattributes", "xmlcomment", "xmlconcat", "xmlelement",
            "xmlexists", "xmlforest", "xmlparse", "xmlpi", "xmlquery",
            "xmlroot", "xmlserialize", "xmltable",
        }
        result = {}
        for func_name in core_functions:
            if func_name not in expression_constructors:
                result[func_name] = self._is_sqlite_function_supported(func_name)

        sqlite_funcs = getattr(sqlite_functions, "__all__", [])
        for func_name in sqlite_funcs:
            result[func_name] = self._is_sqlite_function_supported(func_name)

        return result

    def _is_sqlite_function_supported(self, func_name: str) -> bool:
        """Check if a SQLite-specific function is supported based on version."""
        version_range = self._SQLITE_FUNCTION_VERSIONS.get(func_name)
        if version_range is None:
            return True

        min_version, max_version = version_range

        if min_version is not None and self.version < min_version:
            return False

        if max_version is not None and self.version > max_version:
            return False

        return True

