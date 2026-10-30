# src/rhosocial/activerecord/backend/impl/sqlite/expression/table.py
"""SQLite's table, which carries a schema of its own kind.

SQLite has no schema in the SQL-standard sense -- it has no ``CREATE SCHEMA``,
no persistent schema objects, and nothing between catalogue and table except the
name of an *attached database*, which is session state rather than a catalogue
entry. The core :class:`~...expression.objects.Table` therefore refuses a
``schema_name`` on this backend, and that refusal is correct: it is about the
standard construct.

This subclass exists so the standard construct and SQLite's construct are not
forced to share one slot's acceptance rule. It carries ``schema_name`` because
the *slot* is the right slot -- a level between catalogue and table is what
SQLite has -- while the *rule* for what may occupy it is this dialect's to write.

So the distinction is by node identity rather than by a capability flag:

* a **core** ``Table`` with ``schema_name`` is refused, because SQLite has no
  schema of that kind;
* a **SQLiteTable** with ``schema_name`` renders, because it stands for an
  attached-database name, which SQLite does have.

Conflating them would lose the fact rather than record it. A single
accommodating flag would make SQLite look as though it supports schemas, and the
next reader would have no way to tell which construct a ``schema_name`` meant.
"""

from ....expression.objects.relation import Table

__all__ = ["SQLiteTable"]


class SQLiteTable(Table):
    """A table inside a SQLite schema -- the attached-database name.

    Adds no slots: a schema is the one namespace level SQLite has, and the
    inherited ``schema_name`` already carries it. The class exists for its
    *identity*, which is what tells the dialect's object-name formatter that
    this ``schema_name`` is an attached database rather than a standard schema.

    Example:
        >>> from rhosocial.activerecord.backend.impl.sqlite.dialect import (
        ...     SQLiteDialect,
        ... )
        >>> d = SQLiteDialect()
        >>> SQLiteTable(d, "sqlite_master", schema_name="main").to_sql()
        ('main."sqlite_master"', ())
    """

    __slots__ = ()
