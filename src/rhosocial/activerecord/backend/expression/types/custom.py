# src/rhosocial/activerecord/backend/expression/types/custom.py
"""CustomType fallback for unrecognised or dialect-specific types."""

from __future__ import annotations


from ._base import DataType


class CustomType(DataType):
    """A type name the framework has no class for.

    Kept because a backend may have types and extensions the framework does not
    model, and refusing them would make those unreachable. The raw name is
    validated rather than preserved verbatim: a type name lands in a position
    that cannot take a bound parameter, so an unvalidated string here is an
    injection. The grammar permits any identifier-shaped name, so a user-defined
    type still passes without being registered.

    For a type used often enough to deserve a class, subclass DataType instead —
    then the name is rendered through the dialect and cannot be wrong.
    """

    name = "custom"

    raw: str

    def __init__(self, dialect=None, raw: str = "",
                 ):
        super().__init__(dialect)
        # Validated here rather than in each dialect's formatter: six of the
        # ten backends rendered data_type.raw unchecked, and the four that
        # refused did so only because they happened to lack the formatter.
        from ..type_name import validate_type_name

        self.raw = validate_type_name(raw)

    PARAMETERS = ("raw",)
