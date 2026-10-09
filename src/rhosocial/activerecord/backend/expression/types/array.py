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
    (1 for ``T[]``, 2 for ``T[][]``, etc.).  Both are required — an array with
    no element type is not a type, so a missing one is rejected at construction
    rather than at render time.

    The element type may be any ``DataType``, core or backend-specific::

        PostgresArrayType(PostgresIntegerType())   # INTEGER[]
        PostgresArrayType(IntegerType())           # also INTEGER[]

    Nesting versus dimensionality
    ----------------------------
    ``dimensions`` and an array-valued ``element_type`` are **different types
    that render identically**.  PostgreSQL's ``int[][]`` is genuinely
    two-dimensional, so it is ``dimensions=2``; ClickHouse's
    ``Array(Array(Int32))`` is an array whose element is an array, so it is
    ``element_type=ArrayType(...)``.  Both render ``INTEGER[][]``, so writing
    the same PostgreSQL column the two ways produces two unequal instances of
    one column.  ``dimensions`` is the portable spelling — it is what the SQL
    standard's multi-dimensional array is — so prefer it and keep nesting for
    the backends that spell it that way.

    A dialect that forbids nesting must reject it while rendering; it cannot be
    refused here, because whether ``Array(Array(T))`` is legal is a fact about
    the backend, not about arrays.

    Not modelled
    ------------
    PostgreSQL also accepts explicit extent and lower bounds —
    ``int[3][3]``, ``[1:10]``, ``[1:]`` — and those are **silently dropped**:
    ``ArrayType(IntegerType(), 2)`` renders ``INTEGER[][]``, not
    ``INTEGER[3][3]``.  A lower bound need not be 1 at all, so this is
    information the type cannot currently carry.  Nothing is gained by
    pretending otherwise, but a caller who needs the bounds written must reach
    for :class:`~...types.custom.CustomType`.
    """

    name = "array"

    def __init__(self, dialect: Optional["SQLDialectBase"] = None,
                 element_type: Optional[DataType] = None, dimensions: int = 1,
                 ):
        super().__init__(dialect)
        if element_type is None:
            raise TypeError(
                "ArrayType requires an element_type: T[] is a property of T, "
                "and an array with no element type is not a type. For a type "
                "the framework does not model, use CustomType(raw)."
            )
        if not isinstance(element_type, DataType):
            raise TypeError(
                f"element_type must be a DataType instance, got "
                f"{type(element_type).__name__}."
            )
        if not isinstance(dimensions, int) or isinstance(dimensions, bool) \
                or dimensions < 1:
            raise ValueError(
                f"dimensions must be an int >= 1, got {dimensions!r}."
            )
        self.element_type = element_type
        self.dimensions = dimensions

    PARAMETERS = ("element_type", "dimensions",)

    def is_element_type_equivalent(self, other: DataType) -> bool:
        """Whether *other* names the same element type, ignoring dimensions.

          * Dimensions are ignored — the question is "what does this array
            store", not "how many axes does it have".
          * *other* does **not** need to be an ``ArrayType``; passing a plain
            ``IntegerType()`` directly also works.

        This is deliberately looser than ``==``: it answers a different
        question ("does this array column store the same kind of thing as X")
        rather than restating identity, which is what ``==`` already covers.
        """
        if isinstance(other, ArrayType):
            return self.element_type == other.element_type
        return self.element_type == other
