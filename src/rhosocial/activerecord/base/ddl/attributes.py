# src/rhosocial/activerecord/base/ddl/attributes.py
"""Dialect-free per-column attribute declarations.

A **column attribute** is a typed, dialect-free declaration of something that
should appear in a generated column definition (identity, collation, character
set, …). Attributes are collected by the AR layer into a list and handed to
the backend dialect, which **selects the ones it can render** and turns them
into SQL. This keeps the declaration surface uniform and lets the dialect own
ownership/capability decisions.
"""

from dataclasses import dataclass
from typing import ClassVar, Optional

__all__ = [
    "ColumnAttribute",
    "IdentityAttribute",
    "CollationAttribute",
    "CharacterSetAttribute",
]


class ColumnAttribute:
    """Base class for dialect-free column attribute declarations."""

    kind: ClassVar[str] = "attribute"


@dataclass(frozen=True)
class IdentityAttribute(ColumnAttribute):
    """``GENERATED {ALWAYS | BY DEFAULT} AS IDENTITY`` declaration."""

    kind: ClassVar[str] = "identity"

    generation: str = "BY DEFAULT"
    start: Optional[int] = None
    increment: Optional[int] = None
    minvalue: Optional[int] = None
    maxvalue: Optional[int] = None
    cycle: Optional[bool] = None

    def __post_init__(self) -> None:
        normalized = self.generation.upper()
        if normalized not in ("ALWAYS", "BY DEFAULT"):
            raise ValueError(
                f"identity generation must be 'ALWAYS' or 'BY DEFAULT', got {self.generation!r}"
            )


@dataclass(frozen=True)
class CollationAttribute(ColumnAttribute):
    """Column-level ``COLLATE <name>`` declaration."""

    kind: ClassVar[str] = "collation"

    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("collation attribute requires a non-empty name")


@dataclass(frozen=True)
class CharacterSetAttribute(ColumnAttribute):
    """Column-level ``CHARACTER SET <name>`` declaration."""

    kind: ClassVar[str] = "character_set"

    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("character set attribute requires a non-empty name")
