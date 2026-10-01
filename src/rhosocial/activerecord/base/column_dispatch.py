# src/rhosocial/activerecord/base/column_dispatch.py
"""Maps a model field's Python annotation to a column expression class.

This is a *model-layer* concern: it answers "what does this field hold, so
which operations may be offered on ``Model.c.<field>``". It deliberately
knows nothing about SQL types or dialects — the narrow classes in
:mod:`rhosocial.activerecord.backend.expression.column_types` describe what a
value can *do*, and the DDL layer (``DataType``) independently decides how it
is stored. The two never read each other.

Anything that cannot be classified with confidence falls back to the
permissive :class:`~rhosocial.activerecord.backend.expression.core.Column`.
Guessing would be worse than not narrowing: a wrong guess removes an
operation the caller legitimately needs, and the resulting ``AttributeError``
points at the column rather than at the annotation that caused it.
"""

import datetime
import decimal
import enum
import types
import typing
import uuid
from typing import Any, Dict, Optional, Type

from ..backend.expression.value_types import INTEGER
from ..backend.expression.column_types import (
    ArrayColumn,
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    DateTimeColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    UUIDColumn,
)
from ..backend.expression.core import Column

#: Value families that are not Python classes (``dict``, ``list``, …) are
#: mapped explicitly; everything else is looked up by type below.
_BY_NAME: Dict[str, Type[ColumnBase]] = {
    "str": StringColumn,
    "int": NumericColumn,
    "float": NumericColumn,
    "bool": BooleanColumn,
    "bytes": BinaryColumn,
    "bytearray": BinaryColumn,
    "dict": JSONColumn,
    "list": ArrayColumn,
    "tuple": ArrayColumn,
    "set": ArrayColumn,
    "frozenset": ArrayColumn,
}

#: Types that are not builtin names but still map to a family.
_BY_TYPE: Dict[Any, Type[ColumnBase]] = {
    decimal.Decimal: NumericColumn,
    datetime.datetime: DateTimeColumn,
    datetime.date: DateTimeColumn,
    datetime.time: DateTimeColumn,
    datetime.timedelta: NumericColumn,
    uuid.UUID: UUIDColumn,
}


def strip_annotation(annotation: Any) -> Any:
    """Peel ``Annotated`` and ``Optional`` off *annotation*.

    ``Annotated[str, UseColumn("x")]`` -> ``str``; ``Optional[dict]`` ->
    ``dict``. Declaration markers are not consulted: they describe storage and
    constraints, not the Python value, and reading them here would couple this
    module to the DDL layer.
    """
    # `typing.get_origin(Annotated[...])` returns the `Annotated` special form
    # on 3.9+, but on 3.8 `typing` has no `Annotated` attribute at all, so the
    # identity check raises AttributeError. The presence of `__metadata__` is
    # how the runtime marks an annotated alias on every supported version, so
    # that is what this tests.
    while hasattr(annotation, "__metadata__"):
        annotation = typing.get_args(annotation)[0]

    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is getattr(types, "UnionType", None):
        members = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(members) == 1:
            return strip_annotation(members[0])
    return annotation


def column_class_for(annotation: Any) -> Type[ColumnBase]:
    """Return the column class matching *annotation*.

    Falls back to :class:`~rhosocial.activerecord.backend.expression.core.Column`
    for anything unrecognised: ``Any``, an empty container, a bare
    ``Union[int, str]``, a forward reference, or a custom class. The caller
    still gets a fully usable column.
    """
    annotation = strip_annotation(annotation)

    if annotation in _BY_TYPE:
        return _BY_TYPE[annotation]

    if isinstance(annotation, type):
        if issubclass(annotation, enum.Enum):
            return StringColumn
        for base, column_class in _BY_TYPE.items():
            if isinstance(base, type) and issubclass(annotation, base):
                return column_class
        named = _BY_NAME.get(annotation.__name__)
        if named is not None:
            return named

    return Column


#: Annotations that mean a whole number even though their column class is
#: shared with the fractional ones. ``ABS(int)`` is an int in SQL, so the
#: family has to be narrower than the class or "integer in, integer out"
#: cannot be expressed.
_WHOLE_NUMBER_ANNOTATIONS = (int,)


def family_for(annotation: Any) -> Optional[str]:
    """Return the value family *annotation* implies, or ``None``.

    Only annotations that *narrow* their column class are listed. Everything
    else takes the family its class declares, so a new annotation cannot
    accidentally claim a family it does not have.

    Args:
        annotation: A field's Python annotation, already stripped.

    Returns:
        One of the families in
        :mod:`...backend.expression.value_types`, or ``None``.
    """
    if annotation in _WHOLE_NUMBER_ANNOTATIONS:
        return INTEGER
    return None


def build_column(
    dialect: Any,
    column_name: str,
    annotation: Any,
    table: Optional[str] = None,
    schema_name: Optional[str] = None,
) -> ColumnBase:
    """Build the column expression for a field of type *annotation*.

    The permissive :class:`~rhosocial.activerecord.backend.expression.core.Column`
    keeps its own narrower constructor signature (it predates the
    ``value_type`` argument), so the two shapes are constructed separately
    rather than funnelled through one call.
    """
    column_class = column_class_for(annotation)

    if column_class is Column:
        return Column(dialect, column_name, table=table, schema_name=schema_name)

    value_type = getattr(strip_annotation(annotation), "__name__", None)
    return column_class(
        dialect,
        column_name,
        table=table,
        schema_name=schema_name,
        value_type=value_type,
        value_family=family_for(strip_annotation(annotation)),
    )


__all__ = ["build_column", "column_class_for", "strip_annotation"]
