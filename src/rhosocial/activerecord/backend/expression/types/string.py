# src/rhosocial/activerecord/backend/expression/types/string.py
"""Character / string SQL types.

``CHARACTER`` and ``CHARACTER VARYING`` are SQL's own long forms of ``CHAR``
and ``VARCHAR``. National-character-set spellings (``NCHAR``,
``NVARCHAR``) are deliberately absent: the framework treats a character set as a
*field* rather than a type — the position ``MariaDBEnumType.charset`` already
takes — so they are not a separate spelling of the same concept here.

Widths
------
``CharType`` and ``VarCharType`` are the only core concepts that take a bare
width, and their ``length`` is **resolved rather than stored**: a declaration
that names no width carries the width this server supplies for one, or no width
at all when this server has no default to supply.  See
:mod:`~...expression.types._defaults` for why that value cannot be written down
here, and :attr:`VarCharType.length` for what resolution means for identity.

``BinaryType`` and ``VarBinaryType`` take a width too and deliberately do **not**
do this.  A backend that has no width-bearing byte string renders the unbounded
one — Firebird and core's dummy dialect both answer a bare ``BinaryType`` with
``BLOB``, and SQL Server answers a bare ``VarBinaryType`` with ``VARBINARY(MAX)``
— so there is no server here whose bare form names a particular width, and no
asymmetry for a resolution to close.
"""

from __future__ import annotations

from typing import Optional

from ._base import DataType
from ._defaults import declared_parameter


class CharType(DataType):
    """CHAR[(n)] / CHARACTER[(n)] — fixed-length string.

    A shorter value is padded to ``n`` rather than stored as written, which is
    what makes this concept fixed-length where :class:`VarCharType` is not.
    """

    name = "char"

    SPELLINGS = ("char", "character")

    def __init__(self, dialect=None, length: Optional[int] = None,
                 *, spelling: str = "char"):
        super().__init__(dialect)
        self._length = length
        self.spelling = spelling

    @property
    def length(self) -> Optional[int]:
        """The declared width, or the width this server supplies for none declared.

        ``None`` in, two different things out, and which one is decided by the
        bound dialect: on PostgreSQL it stays ``None``, because ``CHAR`` there
        really is one character long and the catalog reports ``atttypmod = -1``,
        so an absent width means *no* width.  On a server that supplies a width
        for the bare form it becomes that width, because an absent width there
        is not stored — the server writes out its own default and reports it back,
        so a declaration of nothing and a column of that width are the same
        column, and the differ has to be able to say so.

        Resolving at read time rather than in ``__init__`` is what makes the
        deferred binding work: ``CharType()`` bound to a server afterwards
        resolves the same way as ``CharType(dialect)`` built with one.  The cost
        is stated rather than hidden — this type's identity is settled only once
        a dialect is bound, so bind one before using it as a dictionary key or a
        set member, exactly as rendering already requires.
        """
        return self._length if self._length is not None else declared_parameter(
            self.name, "length", self._dialect
        )

    @length.setter
    def length(self, value: Optional[int]) -> None:
        self._length = value

    PARAMETERS = ("length",)

class VarCharType(DataType):
    """VARCHAR(n) / CHARACTER VARYING(n) — variable-length string.

    PostgreSQL reports ``character varying`` from the catalog, which is why the
    long form is a spelling here rather than a class of its own.
    """

    name = "varchar"

    SPELLINGS = ("varchar", "character varying")

    def __init__(self, dialect=None, length: Optional[int] = None,
                 *, spelling: str = "varchar"):
        super().__init__(dialect)
        self._length = length
        self.spelling = spelling

    @property
    def length(self) -> Optional[int]:
        """The declared width, or the width this server supplies for none declared.

        This is the case the whole ``None`` question turns on, so it is worth
        saying what each server means by a bare ``VARCHAR`` here, measured rather
        than assumed:

        * **PostgreSQL — stays ``None``, and that is the honest answer.**  A bare
          ``character varying`` comes back from the catalog with ``atttypmod =
          -1``: the column is unbounded, the word names no width because there is
          none, and normalising it to a number would make this claim the column
          is bounded when it is not.
        * **Firebird, SQL Server — the bare form means a specific width**, which
          the server stores and reports back, so ``None`` in the declaration
          becomes that width here.
        * **Snowflake — the bare form means 16777216**, per its own reference.

        So ``None`` is polymorphic across servers and no value written down here
        would be right for more than one of them.  The resolution is therefore
        read off the bound dialect, and a dialect that supplies nothing keeps
        ``None`` — which is what PostgreSQL does, by having nothing to declare.

        As with :attr:`CharType.length`, this resolves at read time so a dialect
        bound after construction counts, and the consequence is that identity is
        settled only once a dialect is bound.
        """
        return self._length if self._length is not None else declared_parameter(
            self.name, "length", self._dialect
        )

    @length.setter
    def length(self, value: Optional[int]) -> None:
        self._length = value

    PARAMETERS = ("length",)

class TextType(DataType):
    """TEXT / CLOB — unbounded string.

    PostgreSQL treats ``clob`` as an alias for ``text``.
    """

    name = "text"

    SPELLINGS = ("text", "clob")

    def __init__(self, dialect=None, *, spelling: str = "text"):
        super().__init__(dialect)
        self.spelling = spelling
