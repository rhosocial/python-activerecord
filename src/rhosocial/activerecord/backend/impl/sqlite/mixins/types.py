# src/rhosocial/activerecord/backend/impl/sqlite/mixins/types.py
"""SQLite DataType formatting and parsing mixin."""

from __future__ import annotations

from typing import Tuple

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins.data_type import DataTypeMixin
from rhosocial.activerecord.backend.dialect.protocols import DataTypeSupport
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType as CoreBlobType,
    BooleanType,
    CharType,
    CustomType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    IntervalType,
    JsonBType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    TinyIntType,
    VarCharType,
)

from ..expression.types.types import (
    SQLiteBlobType,
    SQLiteIntegerType,
    SQLiteNumericType,
    SQLiteRealType,
    SQLiteTextType,
)


class SQLiteTypeSupportMixin(DataTypeMixin, DataTypeSupport):
    """SQLite DataType formatting and parsing.

    Implements ``DataTypeSupport`` so the dialect can render ``DataType``
    expressions to SQL strings and parse raw SQL type strings back into
    ``DataType`` instances.

    SQLite has a simple type system based on five type affinities (TEXT,
    NUMERIC, INTEGER, REAL, BLOB).  This mixin maps the standard SQL types
    to their SQLite representation.
    """

    def _refuse_unsigned_integer(self, data_type, word: str) -> None:
        """Refuse ``unsigned=True``, because SQLite has no unsigned integer.

        The core integer concepts carry signedness as a field rather than as a
        class, so ``IntegerType(unsigned=True)`` is constructible and the flag
        reaches the formatter. SQLite's honest answer is a refusal:

        * The integer storage class is a signed 8-byte integer -- "whole
          numbers between -9223372036854775808 and +9223372036854775807" -- with
          no unsigned counterpart anywhere in the five storage classes.
          https://sqlite.org/datatype3.html
        * SQLite's declared type is only a *recommendation*: the column's
          affinity is derived from it, and nothing else in the grammar accepts
          an attribute after the type name. There is not even a spelling that
          would parse.

        Writing a bare ``INTEGER`` for an unsigned request would create a column
        that accepts the negatives the caller declared it would not, and report
        success: the same silent data loss as accepting the flag and discarding
        it, which is what this replaces.

        Note the affinity collapse these formatters already perform -- every
        integer width renders as ``INTEGER`` -- is a different decision and
        stays: it is SQLite's documented storage model, and it says nothing
        about range. Signedness is not a width, so it cannot collapse that way.
        """
        if not isinstance(data_type.unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got "
                f"{type(data_type.unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        if not data_type.unsigned:
            return
        raise UnsupportedFeatureError(
            self.name,
            f"an unsigned {word} column "
            f"(SQLite has no unsigned integer type; INTEGER is a signed 8-byte "
            f"integer covering -9223372036854775808..9223372036854775807)",
            suggestion=(
                "Declare the column signed and enforce the range with a CHECK "
                "constraint if negatives must be rejected."
            ),
        )

    def _refuse_unsigned_numeric(self, data_type, word: str) -> None:
        """Refuse ``unsigned=True`` on a floating-point, single-precision or exact
        fixed-point concept, because SQLite has none and has no attribute to
        write.

        The same field reaches these four concepts that it reaches the four
        integer widths -- ``DecimalType``, ``FloatType``, ``RealType`` and
        ``DoubleType`` each carry ``unsigned`` in ``PARAMETERS``, so two
        declarations differing only in it are *different columns* as far as the
        schema differ is concerned -- and SQLite's answer is the same refusal for
        the same two reasons:

        * **The storage has no unsigned counterpart.**  SQLite has five storage
          classes and they are a closed list: ``INTEGER`` ("whole numbers
          between -9223372036854775808 and +9223372036854775807"), ``REAL``
          ("floating point numbers, using an 8-byte IEEE 754 floating-point
          number"), ``TEXT``, ``BLOB``, ``NUMERIC``.  ``REAL`` is an IEEE 754
          binary64, whose documented range is signed on both sides, and there is
          no ``REAL UNSIGNED`` row to select.  A ``DECIMAL`` column gets the
          ``NUMERIC`` affinity and is stored as an ``INTEGER`` or a ``REAL``
          depending on the value, so it has no unsigned form either.
          https://sqlite.org/datatype3.html
        * **There is not even a spelling that would parse.**  SQLite's
          ``column-def`` is ``column-name [type-name] column-constraint*``,
          ``type-name`` is one or more bare type names (optionally
          parenthesised), and the constraints are ``CONSTRAINT``,
          ``PRIMARY KEY``, ``NOT NULL``, ``UNIQUE``, ``CHECK`` and the default
          clauses: a nullability and a set of column constraints, never a type
          modifier.  ``REAL UNSIGNED`` is not a column declaration SQLite
          admits.  https://sqlite.org/lang_createtable.html

        The affinity collapse these formatters already perform -- ``FLOAT`` and
        ``DOUBLE PRECISION`` both render as ``REAL``, and ``DECIMAL`` as
        ``NUMERIC`` -- is a *different* decision and stays: it is SQLite's
        documented storage model.  Signedness is not a width, so it cannot
        collapse that way, and collapsing it would hand the caller a column that
        stores the negatives they declared it would not.

        ``word`` is the word SQLite renders, not the concept the caller named,
        so the message says what this backend would have written instead.

        ``UnsupportedFeatureError``, not ``ValueError``: this is a declaration
        the grammar cannot express at all rather than a wrong value, and the two
        exceptions do not share a base class.
        """
        if not isinstance(data_type.unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got "
                f"{type(data_type.unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        if not data_type.unsigned:
            return
        raise UnsupportedFeatureError(
            self.name,
            f"an unsigned {word} column "
            f"(SQLite has no unsigned floating-point or fixed-point column; its "
            f"five storage classes are a closed list and REAL is documented as "
            f"an 8-byte IEEE 754 floating-point number with a signed range, and "
            f"SQLite's column grammar has no type-modifier position after the "
            f"type name, so there is not even a spelling that would parse)",
            suggestion=(
                "Declare the column signed and enforce the range with a CHECK "
                "constraint if negatives must be rejected."
            ),
        )

    def format_data_type_sqlite_integer(self, expr: SQLiteIntegerType) -> Tuple[str, tuple]:
        """The INTEGER affinity class, so ``INTEGER`` whatever width was asked
        for -- SQLite's documented storage model, not a claim about range.

        ``unsigned`` is refused rather than ignored; see
        :meth:`_refuse_unsigned_integer`. The affinity collapse cannot stand in
        for it: signedness is not a width, so there is no narrower column for a
        wider range to collapse into."""
        self._refuse_unsigned_integer(expr, "INTEGER")
        return "INTEGER", ()

    def format_data_type_sqlite_text(self, expr: SQLiteTextType) -> Tuple[str, tuple]:
        length = expr.length
        return (f"TEXT({length})" if length is not None else "TEXT"), ()

    def format_data_type_sqlite_real(self, expr: SQLiteRealType) -> Tuple[str, tuple]:
        return "REAL", ()

    def format_data_type_sqlite_numeric(self, expr: SQLiteNumericType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_sqlite_blob(self, expr: SQLiteBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    # --- Core types (pure names) rendered per SQLite affinity ---

    def format_data_type_integer(self, expr: IntegerType) -> Tuple[str, tuple]:
        """SQLite accepts both spellings of this one type (its affinity regex
        matches ``INT`` and ``INTEGER`` alike), so the spelling is honoured."""
        if expr.spelling not in IntegerType.SPELLINGS:
            raise TypeError(
                f"{type(self).__name__} cannot render "
                f"{expr.spelling!r}; it accepts "
                f"{', '.join(IntegerType.SPELLINGS)}."
            )
        self._refuse_unsigned_integer(expr, expr.spelling.upper())
        return ("INT" if expr.spelling == "int" else "INTEGER"), ()

    def format_data_type_text(self, expr: TextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_real(self, expr: RealType) -> Tuple[str, tuple]:
        """``REAL``, and refuses ``unsigned``; see
        :meth:`_refuse_unsigned_numeric`.

        ``REAL`` is one of the two words SQLite's five storage classes use, and
        the one this dialect already renders for ``FLOAT`` and ``DOUBLE
        PRECISION`` as well -- so unlike the integer widths there is nothing to
        collapse here and the signedness is the only thing to answer for.  SQLite
        documents ``REAL`` as "floating point numbers, using an 8-byte IEEE 754
        floating-point number": a binary64, signed on both sides, with no
        unsigned row among the five storage classes and no type-modifier position
        in ``column-def`` in which ``UNSIGNED`` could go.  Affinity collapse and
        signedness are different decisions, and signedness is not a width, so it
        cannot collapse away: a bare ``REAL`` for an unsigned request would be a
        column that stores the negatives the caller declared it would not.
        https://sqlite.org/datatype3.html
        """
        self._refuse_unsigned_numeric(expr, "REAL")
        return "REAL", ()

    def format_data_type_blob(self, expr: CoreBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    def format_data_type_bigint(self, expr: BigIntType) -> Tuple[str, tuple]:
        """Every integer width collapses to ``INTEGER``, which is SQLite's
        documented storage model rather than a claim about width.

        ``unsigned`` is refused rather than ignored; see
        :meth:`_refuse_unsigned_integer`."""
        self._refuse_unsigned_integer(expr, "INTEGER")
        return "INTEGER", ()

    def format_data_type_smallint(self, expr: SmallIntType) -> Tuple[str, tuple]:
        """Collapses to ``INTEGER`` like every other integer width, and refuses
        ``unsigned``; see :meth:`_refuse_unsigned_integer`."""
        self._refuse_unsigned_integer(expr, "INTEGER")
        return "INTEGER", ()

    def format_data_type_varchar(self, expr: VarCharType) -> Tuple[str, tuple]:
        if expr.spelling not in VarCharType.SPELLINGS:
            raise TypeError(
                f"{type(self).__name__} cannot render {expr.spelling!r}; "
                f"it accepts {', '.join(VarCharType.SPELLINGS)}."
            )
        return "TEXT", ()

    def format_data_type_char(self, expr: CharType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_float(self, expr: FloatType) -> Tuple[str, tuple]:
        """``FLOAT(p)`` collapses to ``REAL``, which is SQLite's documented
        storage class for approximate numerics, and refuses ``unsigned``; see
        :meth:`_refuse_unsigned_numeric`."""
        self._refuse_unsigned_numeric(expr, "REAL")
        return "REAL", ()

    def format_data_type_decimal(self, expr: DecimalType) -> Tuple[str, tuple]:
        """``DECIMAL`` collapses to ``NUMERIC``, which is SQLite's documented
        storage class for fixed-point values, and refuses ``unsigned``; see
        :meth:`_refuse_unsigned_numeric`."""
        if expr.spelling not in DecimalType.SPELLINGS:
            raise TypeError(
                f"{type(self).__name__} cannot render {expr.spelling!r}; "
                f"it accepts {', '.join(DecimalType.SPELLINGS)}."
            )
        self._refuse_unsigned_numeric(expr, "NUMERIC")
        return "NUMERIC", ()

    def format_data_type_boolean(self, expr: BooleanType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_date(self, expr: DateType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_datetime(self, expr: DateTimeType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_timestamp(self, expr: TimestampType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_time(self, expr: TimeType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_tinyint(self, expr: TinyIntType) -> Tuple[str, tuple]:

        """Collapses to ``INTEGER`` like every other integer width, and
        refuses ``unsigned``; see :meth:`_refuse_unsigned_integer`."""
        self._refuse_unsigned_integer(expr, "INTEGER")
        return "INTEGER", ()

    def format_data_type_double(self, expr: DoubleType) -> Tuple[str, tuple]:
        """``DOUBLE PRECISION`` collapses to ``REAL``, which is SQLite's
        documented storage class for approximate numerics, and refuses
        ``unsigned``; see :meth:`_refuse_unsigned_numeric`."""
        self._refuse_unsigned_numeric(expr, "REAL")
        return "REAL", ()

    def format_data_type_timetz(self, expr: TimeTzType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_timestamptz(self, expr: TimestampTzType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_interval(self, expr: IntervalType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_json(self, expr: JsonType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_jsonb(self, expr: JsonBType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_custom(self, expr: CustomType) -> Tuple[str, tuple]:
        return expr.raw, ()

    # ------------------------------------------------------------------
    #
    # SQLite stores everything through type affinity: any type this mixin
    # renders is genuinely storable, so the ``format_data_type_*`` family
    # above is the whole support declaration — the formatter *is* the
    # "supported" answer. Anything this mixin does not render (e.g. enum,
    # uuid, binary) is honestly absent, and covered by
    # ``substitute_data_types()`` instead.
    # ------------------------------------------------------------------

