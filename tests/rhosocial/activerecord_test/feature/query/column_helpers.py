# tests/rhosocial/activerecord_test/feature/query/column_helpers.py
"""Building a column expression for a test, now that resolution is the dialect's.

The framework used to ship a ``build_column(dialect, name, annotation)`` in
``base/column_dispatch.py`` and these tests called it. There is no such function
now, and that is the point of the ruling that removed the module: a factory in
the model layer that classified annotations had to hold a table, and a table in
core can only answer for the half of the key space core knows about.

What replaced it is two steps the caller now performs explicitly, which is what
:meth:`~rhosocial.activerecord.backend.dialect.mixins.column_suggestion.ColumnSuggestionMixin.column_class_for`
is for:

    column = build_column(dialect, "price", decimal.Decimal)

and that is all this helper does. It is a test convenience, not a framework
entry point — the production caller is
``base/field_proxy.py``, which does the same two steps while reading the field's
declaration out of pydantic's metadata.

Deliberately **not** a fallback: an annotation this helper cannot resolve raises
:class:`ColumnTypeResolutionError` exactly as ``Model.c.<field>`` would, so a
test that builds a column from a bad annotation fails here for the same reason
the model would, and the two cannot drift apart.
"""

from typing import Any, Optional

from rhosocial.activerecord.backend.expression.column_suggestions import (
    ColumnTypeResolutionError,
    strip_annotation,
)
from rhosocial.activerecord.backend.expression.column_types import ColumnBase
from rhosocial.activerecord.backend.expression.core import Column


def build_column(
    dialect: Any,
    column_name: str,
    annotation: Any,
    table: Optional[str] = None,
    schema_name: Optional[str] = None,
    column_type: Any = None,
) -> ColumnBase:
    """Build the column expression *dialect* suggests for *annotation*.

    Args:
        dialect: The dialect to resolve through. Resolution is per-backend by
            design, so a test that wants a specific column class must say which
            backend's answer it is asking for.
        column_name: The SQL name to render.
        annotation: The Python annotation, ``Annotated`` / ``Optional`` included.
        table: Optional table qualifier.
        schema_name: Optional schema qualifier.
        column_type: A ``UseColumnType`` when the test is exercising an explicit
            declaration; ``None`` asks the dialect's table.

    Returns:
        The constructed column expression.

    Raises:
        ColumnTypeResolutionError: The dialect's table has no column class for
            *annotation*, or answers ``UNSUPPORTED`` for it.
    """
    column_class = dialect.column_class_for(annotation, column_type)
    if column_class is Column:
        # The untyped column predates `value_type` and keeps its own narrower
        # constructor. It can only arrive by being declared explicitly now, so
        # this is a shape difference rather than a fallback.
        return Column(dialect, column_name, table=table, schema_name=schema_name)
    return column_class(
        dialect,
        column_name,
        table=table,
        schema_name=schema_name,
        value_type=getattr(strip_annotation(annotation), "__name__", None),
    )


__all__ = ["ColumnTypeResolutionError", "build_column"]
