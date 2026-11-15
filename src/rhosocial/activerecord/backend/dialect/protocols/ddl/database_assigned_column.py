# src/rhosocial/activerecord/backend/dialect/protocols/ddl/database_assigned_column.py
"""DatabaseAssignedColumnSupport.

Whether the engine supplies an integer column's value on INSERT when the caller
omits it, and lets the caller read it back.

This is a **capability**, not a spelling, and it is deliberately separate from
:class:`~...ddl.auto_increment.AutoIncrementColumnSupport` and
:class:`~...ddl.identity_column.IdentityColumnSupport`:

* ``supports_auto_increment_column()`` asks whether the bare ``AUTO_INCREMENT``
  *token* can be written. PostgreSQL cannot write it, and answers ``False``;
* ``supports_identity_column()`` asks whether the SQL-standard identity *clause*
  can be written;
* this one asks whether the column's value comes from the database at all.
  PostgreSQL answers yes through ``SERIAL``, which is a pseudo-type rather than
  a clause, so the two answers differ on the same dialect. That is why a
  declaration asks this question and never a mechanism's name.

What a ``True`` answer guarantees: omitting the value yields one assigned by the
engine, and an insert can return it (``RETURNING``, ``lastrowid``, or the
engine's equivalent).

What it does **not** guarantee: that an explicit value moves the counter the
way ``AUTO_INCREMENT`` does. MySQL raises the counter to ``max + 1`` when a
larger explicit value is inserted; a sequence-backed column leaves the sequence
untouched, so a later generated value may collide. Implementations differ on
that point and no answer here implies the MySQL behaviour.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class DatabaseAssignedColumnSupport(Protocol):
    """Whether the engine assigns an integer column's value on INSERT."""

    def supports_database_assigned_integer_column(self) -> bool:
        """``True`` when omitting the value makes the database supply one.

        Not a spelling probe: a dialect answers yes however it spells the
        mechanism (column marker, pseudo-type, identity clause).
        """
        ...  # pragma: no cover
