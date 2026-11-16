# src/rhosocial/activerecord/base/annotation_lookup.py
"""How a Python annotation becomes a key of a dialect's answer table.

Both answer tables in the framework -- the column-class table that decides
what a value can do, and the storage-type table that decides what a column
*is* -- are keyed by bare Python types.  A field's annotation is rarely bare:
it may be ``Optional[T]``, ``Annotated[T, ...]``, a subclass of a key
(``class MyStr(str)``), an ``enum.Enum``, or a pydantic type the backend
models separately.  Normalising is therefore identical work on both sides,
so it lives here once, and each consumer supplies only its own table.
"""
from __future__ import annotations

import enum
import types
import typing
from typing import Any


def strip_annotation(annotation: Any) -> Any:
    """Peel ``Annotated`` and ``Optional`` off *annotation*."""
    # `typing.get_origin(Annotated[...])` returns the `Annotated` special form
    # on 3.9+, but on 3.8 `typing` has no `Annotated` attribute, so the
    # identity check raises AttributeError. The presence of `__metadata__`
    # marks an annotated alias on every supported version.
    while hasattr(annotation, "__metadata__"):
        annotation = typing.get_args(annotation)[0]

    origin = typing.get_origin(annotation)
    if origin is typing.Union or origin is getattr(types, "UnionType", None):
        members = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(members) == 1:
            return strip_annotation(members[0])
    return annotation


def table_entry_for(annotation: Any, keys: Any) -> Any:
    """The table key *annotation* normalises to, or ``None``.

    Three rules and the pydantic bridge: exact key match, ``enum.Enum``
    subclass, then a subclass walk in *keys* order (``class MyStr(str)``
    -> ``str``). The bridge is consulted last, so it can turn a failure into
    an answer and can never change an answer that already existed; its result
    is re-checked against the same keys.
    """
    peeled = strip_annotation(annotation)
    if peeled in keys:
        return peeled

    if isinstance(peeled, type):
        if issubclass(peeled, enum.Enum):
            # Checked before the walk: an enum that also subclasses something
            # else (`class Weekday(int, Enum)`) stays an enum.
            return enum.Enum
        for key in keys:
            if isinstance(key, type) and key is not peeled and issubclass(peeled, key):
                return key

    from .pydantic_fields import normalize_pydantic_annotation

    bridged = normalize_pydantic_annotation(peeled)
    if bridged is not None and bridged in keys:
        return bridged
    return None


def entry_name(entry: Any) -> str:
    """A readable name for a table key."""
    module = getattr(entry, "__module__", None)
    name = getattr(entry, "__name__", None) or repr(entry)
    if module and module not in ("builtins",):
        return f"{module}.{name}"
    return name


def describe_annotation(annotation: Any) -> str:
    """A readable description of a field annotation."""
    name = getattr(annotation, "__name__", None) or repr(annotation)
    return f"{name!r} (the annotation {annotation!r})"


__all__ = [
    "describe_annotation",
    "entry_name",
    "strip_annotation",
    "table_entry_for",
]
