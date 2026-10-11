# src/rhosocial/activerecord/backend/expression/types/numeric.py
"""Floating-point and exact numeric SQL types.

``UNSIGNED`` reaches these three concepts exactly as it reaches the four integer
widths, and for exactly the same reason: it is a **field**, not a class.

MySQL's manual says so of the numeric types in the same breath as the integers --
"Floating point and fixed-point types also can be ``UNSIGNED``" -- so
``DECIMAL(10,2) UNSIGNED`` and ``DECIMAL(10,2)`` are two different columns with
different ranges, on MySQL and on MariaDB alike. A concept that cannot hold the
flag cannot distinguish them, and the schema differ then reports no change for a
change the database happily makes. Measured on all fifteen wired MariaDB servers,
``decimal(10,2) unsigned zerofill`` introspected as ``DecimalType(10, 2)``: the
signedness was simply gone.

Width is the class axis here just as it is in ``integer.py`` -- a ``FLOAT(p)``
exists for every ``p`` -- and a linear chain cannot hold a (width x signedness)
grid, so ``unsigned: bool`` is a field on each of the three concepts that have
one. Which dialect honours it and which refuses it is that vendor's own
question, answered from that vendor's own documentation and recorded in that
dialect's ``format_data_type_*``.
"""

from __future__ import annotations

from typing import Optional

from ._base import DataType
from ._defaults import declared_parameter


class FloatType(DataType):
    """FLOAT[(p)] — approximate numeric, variable precision."""

    name = "float"

    unsigned: bool = False

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 *, unsigned: bool = False):
        super().__init__(dialect)
        self._precision = precision
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        self.unsigned = unsigned

    @property
    def precision(self) -> Optional[int]:
        """The declared binary precision, or the one this server supplies for none.

        Oracle is the case this exists for: a bare ``FLOAT`` there **is**
        ``FLOAT(126)``.  The ANSI conversion table's note 2 says so in the
        vendor's own words — "The default precision for this data type is 126
        binary, or 38 decimal" — and the catalog agrees rather than merely
        documenting it: ``CREATE TABLE t (c FLOAT)`` reports
        ``DATA_TYPE = 'FLOAT'`` and ``DATA_PRECISION = 126``, the same two
        values a ``FLOAT(126)`` column reports, so a declaration that named no
        precision and a column of 126 are one column and the differ has to be
        able to say so.  A dialect with nothing to declare keeps ``None``,
        which is the honest answer for a server whose bare form names no
        particular width — PostgreSQL's ``FLOAT`` among them, and no dialect at
        all as well.

        Resolving at read time rather than in ``__init__`` is what makes the
        deferred binding work: ``FloatType()`` bound to a server afterwards
        resolves the same way as ``FloatType(dialect)`` built with one.  The cost
        is stated rather than hidden — this type's identity is settled only once
        a dialect is bound, so bind one before using it as a dictionary key or a
        set member, exactly as rendering already requires.
        """
        return self._precision if self._precision is not None else declared_parameter(
            self.name, "precision", self._dialect
        )

    @precision.setter
    def precision(self, value: Optional[int]) -> None:
        self._precision = value

    # ``unsigned`` is appended, never inserted ahead of ``precision``: the order
    # of this tuple is what ``identity()`` reads, so it is what ``==`` and
    # ``__hash__`` read, and reordering it would change every hash of every
    # instance of this class.
    PARAMETERS = ("precision", "unsigned")

class RealType(DataType):
    
    """
    REAL — single-precision (4 bytes / 24-bit mantissa).

    ``unsigned`` is here because the vendor documents it on this word: MySQL's
    numeric-type syntax lists ``REAL[(M,D)] [UNSIGNED] [ZEROFILL]`` as a synonym
    for ``DOUBLE``, and its attributes page extends the ``UNSIGNED`` deprecation
    to that word explicitly — "deprecated for columns of type ``FLOAT``,
    ``DOUBLE``, and ``DECIMAL`` (**and any synonyms**)".
    https://dev.mysql.com/doc/refman/9.7/en/numeric-type-syntax.html

    **The server reports the storage, not the word.** Measured on all seven wired
    servers, 5.6.51 through 26.7.0, a ``REAL UNSIGNED`` column is reported by
    ``information_schema`` and ``SHOW COLUMNS`` as ``double unsigned`` — MySQL
    resolves the synonym in the storage layer. So a live ``REAL UNSIGNED`` column
    introspects as ``DoubleType(unsigned=True)`` and cannot round-trip against a
    declared ``RealType``. That is MySQL's documented synonym behaviour, it
    predates this field, and it applies equally to a signed ``REAL``: it is one
    more instance of the fact recorded below, that on this backend the concept
    and its storage are not the same thing.

    Note also that ``REAL`` is a synonym for ``DOUBLE`` unless the
    ``REAL_AS_FLOAT`` SQL mode is enabled, in which case it is a synonym for
    ``FLOAT``. Which is why this class stays separate from :class:`DoubleType`
    instead of becoming one of its spellings.

    Because of that mode-dependence MySQL and MariaDB do not render this
    concept at all: the catalog reports the resolved storage (``double``, or
    ``float`` under the mode) and never the word, so a declared ``RealType``
    could not round-trip. Both dialects substitute :class:`DoubleType` and say
    why in their ``substitute_advice``.

    """

    name = "real"

    unsigned: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False):
        super().__init__(dialect)
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        self.unsigned = unsigned

    PARAMETERS = ("unsigned",)


class DoubleType(DataType):
    """DOUBLE PRECISION — double-precision (8 bytes / 53-bit mantissa).

    ``DOUBLE PRECISION`` is the standard's name; ``DOUBLE`` is the common
    abbreviation.
    """

    name = "double"

    SPELLINGS = ("double", "double precision")

    unsigned: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 spelling: str = "double"):
        super().__init__(dialect)
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        self.unsigned = unsigned
        self.spelling = spelling

    PARAMETERS = ("unsigned",)


class DecimalType(DataType):
    """DECIMAL[(p[,s])] / NUMERIC[(p[,s])] — exact fixed-point.

    SQL:2016 makes ``DECIMAL`` a shorthand for ``NUMERIC``, and ``DEC`` is the
    common abbreviation.
    """

    name = "decimal"

    SPELLINGS = ("decimal", "numeric", "dec")

    unsigned: bool = False

    def __init__(self, dialect=None, precision: Optional[int] = None,
                 scale: Optional[int] = None,
                 *, unsigned: bool = False, spelling: str = "decimal"):
        super().__init__(dialect)
        self._precision = precision
        self._scale = scale
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        self.unsigned = unsigned
        self.spelling = spelling

    @property
    def precision(self) -> Optional[int]:
        """The declared precision, or the precision this server supplies for none.

        Snowflake is the case this exists for: a bare ``NUMBER`` there **is**
        ``NUMBER(38, 0)`` — "By default, precision is 38, and scale is 0; that
        is, NUMBER(38, 0)", in the manual's own words — and ``DESC TABLE``
        renders the two spellings identically, so a declaration that named no
        precision and a column of 38 are one column and the differ has to be
        able to say so.  A dialect with nothing to declare keeps ``None``,
        which is what PostgreSQL says about its own exact numerics by having
        nothing to say, and it is also the answer with no dialect bound at all.

        Resolving at read time rather than in ``__init__`` is what makes the
        deferred binding work: ``DecimalType()`` bound to a server afterwards
        resolves the same way as ``DecimalType(dialect)`` built with one.  The
        cost is stated rather than hidden — this type's identity is settled only
        once a dialect is bound, so bind one before using it as a dictionary key
        or a set member, exactly as rendering already requires.
        """
        return self._precision if self._precision is not None else declared_parameter(
            self.name, "precision", self._dialect
        )

    @precision.setter
    def precision(self, value: Optional[int]) -> None:
        self._precision = value

    @property
    def scale(self) -> Optional[int]:
        """The declared scale, or the scale this server supplies for none.

        ``scale`` resolves independently of ``precision`` because the question
        is asked and answered per parameter: on Snowflake a declaration that
        names a precision and no scale is still stored with a scale of 0
        (``NUMBER(10)`` is ``NUMBER(10, 0)``), and one that names neither
        carries both halves of the documented pair.  Writing this as "only fill
        the scale in when the precision is absent too" would leave the
        precision-only declaration comparing unequal to the column it produced
        — the same defect one parameter over — and ``type_parameter_defaults``
        is keyed per parameter for exactly this reason.

        A dialect that declares nothing keeps ``None``, and so does an unbound
        instance; both are the honest answer when no server has said what its
        bare form means.  Like :attr:`precision`, this resolves at read time so
        a dialect bound after construction counts, and identity is settled only
        once a dialect is bound.
        """
        return self._scale if self._scale is not None else declared_parameter(
            self.name, "scale", self._dialect
        )

    @scale.setter
    def scale(self, value: Optional[int]) -> None:
        self._scale = value

    # ``unsigned`` is appended, never inserted ahead of ``precision`` / ``scale``:
    # see the note on ``FloatType.PARAMETERS``.
    PARAMETERS = ("precision", "scale", "unsigned")
