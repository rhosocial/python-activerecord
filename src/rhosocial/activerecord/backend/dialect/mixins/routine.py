# src/rhosocial/activerecord/backend/dialect/mixins/routine.py
"""Shared defaults for stored-routine (procedure / function) DDL groups.

Functional-group form: the expression classes live in each backend's
``expression/routine.py``; this mixin supplies the cross-backend default
for formatting routine parameter definitions.  Backends override
:meth:`format_param` only when their parameter grammar differs.
"""

from typing import Any  # noqa: F401 (reserved for subclass use)
class RoutineSupportMixin:
    """Shared defaults for stored-routine DDL rendering."""

    def format_param(self, param) -> str:
        """Format a stored-routine parameter definition.

        A param may be a plain string (``IN name TYPE``), a tuple
        ``(mode, name, type)``, or ``(name, type)``.
        """
        if isinstance(param, tuple):
            if len(param) == 3:
                mode, name, type_sql = param
                return f"{mode} {self.format_identifier(name)} {type_sql}"
            if len(param) == 2:
                name, type_sql = param
                return f"{self.format_identifier(name)} {type_sql}"
        if isinstance(param, str):
            return param
        raise ValueError(f"Invalid parameter definition: {param!r}")
