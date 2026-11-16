# src/rhosocial/activerecord/backend/dialect/mixins/storage_type.py
"""Baseline plumbing for the StorageTypeSupport protocol.

The same division as :mod:`...column_type`: the mixin supplies the part that is
identical everywhere and deliberately withholds the part that is not.

There is **no inherited suggested table**. A table in core would be a guess
about a server core has never seen -- and worse here than in the column-class
case, because the guess would become a column width in someone's schema. A
dialect that does not answer is told so when a field with no declaration is
derived, by an error naming the model, the column and the Python type.
"""

from __future__ import annotations

import copy

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.types import DataType


class StorageTypeMixin:
    """Default implementation of the suggested-storage half of the protocol.

    ``suggested_extra_storage_types()`` defaults to no extras, which is the
    honest answer for most backends. ``suggested_storage_types()`` has no
    default and must be overridden.
    """

    @staticmethod
    def storage_type_copies(table: Dict[Any, Any]) -> Dict[Any, Any]:
        """Return a fresh dict of **copies** for a storage table.

        A ``DataType`` is a value object whose ``dialect`` is a mutable
        rendering attribute: a caller binds the dialect on what it receives,
        so handing out the table's own instances would let one derivation
        rebind the object the next lookup reads. Copies also keep the table's
        own returns fresh, like ``suggested_column_types()``.
        """
        return {
            key: (copy.copy(value) if value is not None else None)
            for key, value in table.items()
        }

    def suggested_storage_types(self) -> Dict[Any, Optional["DataType"]]:
        """The storage declaration this dialect suggests for each Python type.

        Must be overridden. Every key of the framework-modelled types has to
        be answered -- with a ``DataType`` instance, or with ``None`` when the
        dialect has no declaration for that value family. Values are copies.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not answer the suggested storage-type "
            f"table. Implement suggested_storage_types() with a DataType "
            f"instance (or None, as a last resort) for every framework-modelled "
            f"Python type; there is no inherited default."
        )

    def suggested_extra_storage_types(self) -> Dict[Any, "DataType"]:
        """Storage declarations for this dialect's own Python types.

        Empty by default: a backend with nothing of its own has nothing to
        report, and a type it does not offer is simply absent from the table.
        """
        return {}
