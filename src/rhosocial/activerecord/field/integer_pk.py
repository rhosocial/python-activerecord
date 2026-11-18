# src/rhosocial/activerecord/field/integer_pk.py
"""Module providing integer primary key functionality."""

from typing import ClassVar, Optional


class IntegerPKMixin:
    """Integer Primary Key Mixin.

    A ready-made declaration for the common "integer auto-increment primary
    key" shape. It packages two things the developer would otherwise write
    separately:

    * the ``id`` field itself (``Optional[int]`` -- only a Python type, no SQL
      storage declaration; the backend decides the DDL via its type
      suggestions);
    * the primary-key declaration (``__primary_key__ = "id"``), which the
      ActiveRecord interface's ``primary_key()`` reads.

    A model that wants a different key field overrides ``__primary_key__``;
    a model that wants no key simply does not mix this in (the base declares
    ``__primary_key__ = None``, keyless). Integer auto-increment *storage* is
    a separate, backend-side DDL suggestion and is not decided here.
    """

    __primary_key__: ClassVar[str] = "id"

    id: Optional[int] = None
