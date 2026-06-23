# src/rhosocial/activerecord/backend/expression/types/array.py
"""Array container type ``T[]`` / ``T[n]``."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ._base import DataType

if TYPE_CHECKING:
    from ...dialect import SQLDialectBase


class ArrayType(DataType):
    """T[] / T[n] — parameterised array container type.

    ``element_type`` holds the inner ``DataType`` instance (e.g. ``IntegerType()``
    for ``INTEGER[]``), and ``dimensions`` records the array dimensionality
    (1 for ``T[]``, 2 for ``T[][]``, etc.).

    .. note::

       The ``element_type`` must be an instance of a concrete backend-specific
       ``DataType`` (e.g. ``PostgresIntegerType``), **not** a generic base type
       (e.g. ``IntegerType``).  Using generic base types will cause a
       ``TypeError`` when the dialect tries to render the element type, because
       the dialect only registers formatters for its own concrete types.

       **Best practice**::

           # Good — backend-specific element type
           col_type = PostgresArrayType(PostgresIntegerType())

           # Avoid — generic element type; will raise TypeError at render time
           col_type = ArrayType(IntegerType())
    """

    def __init__(self, element_type: DataType, dimensions: int = 1,
                 dialect: Optional["SQLDialectBase"] = None):
        super().__init__(dialect)
        self.element_type = element_type
        self.dimensions = dimensions

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return (self.element_type == other.element_type
                and self.dimensions == other.dimensions)

    def __hash__(self) -> int:
        return hash((type(self), self.element_type, self.dimensions))

    def _type_params(self) -> tuple:
        return (self.element_type, self.dimensions)

    def is_equivalent(self, other: DataType) -> bool:
        if type(self) is not type(other):
            return False
        return (self.dimensions == other.dimensions
                and self.element_type.is_equivalent(other.element_type))

    def is_element_type_equivalent(self, other: DataType) -> bool:
        """Check whether *other* represents the same element type.

        Unlike ``is_equivalent``:
          * Dimensions are ignored.
          * *other* does **not** need to be an ``ArrayType`` — passing a plain
            ``IntegerType()`` directly also works.

        This is useful for schema comparison scenarios where the question is
        "does this array column store the same element type as X" without
        caring about dimensionality.
        """
        if isinstance(other, ArrayType):
            return self.element_type.is_equivalent(other.element_type)
        return self.element_type.is_equivalent(other)
