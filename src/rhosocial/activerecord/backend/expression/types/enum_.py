# src/rhosocial/activerecord/backend/expression/types/enum_.py
"""ENUM — enumerated string values."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ._base import DataType


class EnumType(DataType):
    """ENUM — enumerated string values (MySQL/MariaDB native; suggested as text elsewhere)."""

    name = "enum"

    values: Tuple[str, ...] = ()

    def __init__(self, dialect=None, values: Optional[List[str]] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        if values is None:
            raise ValueError("EnumType requires values")
        if not values:
            raise ValueError("EnumType requires at least one value")
        self.values = tuple(values)

    def _type_params(self) -> tuple:
        return (self.values,)
