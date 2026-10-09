# src/rhosocial/activerecord/backend/dialect/mixins/column_type.py
"""Baseline plumbing for the ColumnTypeSupport protocol.

A dialect implements the protocol by answering two tables; this mixin supplies
the parts that are the same everywhere and deliberately withholds the part
that is not.

There is **no inherited common-type table**. A table in core would be a guess
about a server core has never seen — and a wrong guess is worse than an
omission here, because resolution would accept it silently. A dialect that
does not answer is told so when a field is resolved, by an error naming the
missing entry.
"""

from typing import Any, Dict, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.column_types import ColumnBase


class ColumnTypeMixin:
    """Default implementation of the suggested-tables half of the protocol.

    ``suggested_extra_column_types()`` defaults to no extras, which is the
    honest answer for most backends. ``suggested_column_types()`` has no
    default and must be overridden.
    """

    def suggested_column_types(self) -> Dict[Any, Optional[Type["ColumnBase"]]]:
        """The column class this dialect suggests for each common Python type.

        Must be overridden. Every key of the framework's common types has to
        be answered -- with a column class, or with ``None`` when the dialect
        genuinely has no workaround for that value family.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not answer the column-type table. "
            f"Implement suggested_column_types() with a class (or None, as a "
            f"last resort) for every common Python type; there is no "
            f"inherited default."
        )

    def suggested_extra_column_types(self) -> Dict[Any, Type["ColumnBase"]]:
        """Extra Python types this dialect offers beyond the common ones.

        Empty by default: a backend with nothing of its own has nothing to
        report, and a type it does not offer is simply absent from the table.
        """
        return {}
