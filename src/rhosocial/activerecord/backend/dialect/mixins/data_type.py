# src/rhosocial/activerecord/backend/dialect/mixins/data_type.py
"""Data type formatting dispatch for SQL dialects."""

from __future__ import annotations

import re
from typing import cast, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ...expression.types._base import DataType


SQLQueryAndParams = Tuple[str, tuple]
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class DataTypeMixin:
    """Mixin providing naming-convention ``format_data_type`` dispatch."""

    def format_data_type(self, data_type: DataType) -> SQLQueryAndParams:
        """Render a :class:`DataType` through the dialect's type family."""
        from ...expression.types._base import DataType

        if not isinstance(data_type, DataType):
            raise TypeError(
                f"{type(self).__name__}.format_data_type() expects a "
                f"DataType instance, got {type(data_type).__name__}."
            )
        name = getattr(data_type, "name", None)
        if not name or not _NAME_RE.match(name):
            raise TypeError(
                f"{type(data_type).__name__} does not declare a valid generic "
                f"type name (name={name!r}); cannot dispatch."
            )
        formatter = getattr(self, f"format_data_type_{name}", None)
        if formatter is None:
            raise TypeError(
                f"{type(self).__name__} does not support the generic type "
                f"{name!r} (no format_data_type_{name}). Use a type this "
                f"backend supports."
            )
        return cast(SQLQueryAndParams, formatter(data_type))

    def supports_data_types(self) -> Dict[str, type]:
        """Return the generic type names and concrete classes this dialect renders."""
        result = {}
        for member_name in dir(type(self)):
            match = re.match(r"^format_data_type_([a-z][a-z0-9_]*)$", member_name)
            if not match:
                continue
            name = match.group(1)
            supports = getattr(self, f"supports_data_type_{name}", None)
            if supports is not None and supports():
                data_type_class = self._type_class_for(name)
                if data_type_class is not None:
                    result[name] = data_type_class
        return result

    def _type_class_for(self, name: str) -> Optional[type]:
        """Resolve the concrete ``DataType`` class for a generic name."""
        from ...expression.types._base import DataType

        seen = set()
        stack = [DataType]
        while stack:
            klass = stack.pop()
            if klass in seen:
                continue
            seen.add(klass)
            stack.extend(klass.__subclasses__())
            if isinstance(klass, type) and getattr(klass, "name", None) == name:
                return klass
        return None

    def suggested_data_types(self) -> Dict[str, type]:
        """Return cross-backend type suggestions, empty by default."""
        return {}


__all__ = ["DataTypeMixin"]
