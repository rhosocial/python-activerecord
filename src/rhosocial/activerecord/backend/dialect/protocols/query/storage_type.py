# src/rhosocial/activerecord/backend/dialect/protocols/query/storage_type.py
"""StorageTypeSupport protocol: the storage declaration a dialect suggests.

This is the DDL-side counterpart of :mod:`...column_type`. The two answer
different questions about the same Python type and neither reads the other:

* ``suggested_column_types()`` -- *what operations does a value have here*,
  answered with a :class:`~...expression.column_types.ColumnBase` **class**;
* ``suggested_storage_types()`` -- *what column declaration does a field with
  no SQL type get here*, answered with a
  :class:`~...expression.types.DataType` **instance**.

An instance, not a class, because a storage declaration carries parameters:
``VARCHAR`` has a width, ``DECIMAL`` has a precision, ``TIMESTAMP`` has one
too. A class would only say "this concept", and the widths are per-dialect
policy rather than a portable fact -- measured, ``VarCharType()`` renders
``VARCHAR`` on PostgreSQL, ``TEXT`` on SQLite, and is a syntax error on
MySQL, whose grammar is ``VARCHAR(M)`` with ``M`` mandatory.

``suggested_storage_types()``
    The *suggested* table, i.e. the default used only when a field declares
    nothing. Keys are the Python types the framework models -- the same
    twenty-four the column-class table keys, common scalars plus the complex
    families -- and **every key must be answered**, with a ``DataType``
    instance or with ``None`` when the dialect has no declaration for it.
    An explicit ``UseSqlType(...)`` on the field always wins; a suggestion is
    never applied over a declaration, so a user may ignore this table
    entirely. A suggestion that turns out to be unrenderable is reported as
    an error naming the table and column, never as a silent substitution.

``suggested_extra_storage_types()``
    The backend's own vocabulary: keys are Python types the framework does
    not model, values are ``DataType`` instances. A type the backend does not
    offer is simply absent. The key set is disjoint from the suggested table
    by contract -- the two name different populations, not two spellings of
    one -- and matches the backend's own column-class extras, so a backend
    cannot answer one layer and forget the other.

Both are methods rather than class attributes, so the answer may depend on
the server version or build (and on extensions: PostGIS for geometry,
pgvector for vectors). Both return fresh dicts whose values are **copies**:
a ``DataType`` is a value object whose dialect is a mutable rendering
attribute, and a caller that binds it must not rebind what the next lookup
will read. There is no inherited default: a table in core would be a guess
about a server core has never seen.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.types import DataType


@runtime_checkable
class StorageTypeSupport(Protocol):
    """Which storage declaration each framework-modelled Python type means."""

    def suggested_storage_types(self) -> Dict[Any, Optional["DataType"]]:
        """The suggested ``DataType`` for each framework-modelled Python type.

        A suggestion only: it applies when a field declares no SQL type of
        its own, and an explicit ``UseSqlType`` always takes precedence.

        **Every key must be answered** -- an instance, or ``None`` when this
        dialect has no declaration for the value family. A missing key is an
        omission, not a decision. Values are copies, so a caller may bind the
        dialect on what it receives.
        """
        ...

    def suggested_extra_storage_types(self) -> Dict[Any, "DataType"]:
        """Storage declarations for the backend's own Python types.

        Keys are Python types the framework does not model; values are
        ``DataType`` instances (copies). A type the backend does not offer is
        simply absent, and the key set is disjoint from
        :meth:`suggested_storage_types`.
        """
        ...
