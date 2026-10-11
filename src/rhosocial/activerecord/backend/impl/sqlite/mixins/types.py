# src/rhosocial/activerecord/backend/impl/sqlite/mixins/types.py
"""SQLite DataType formatting and parsing mixin."""

from __future__ import annotations

import re
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
    DataType,
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

from ..expression.types import (
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
        if not getattr(data_type, "unsigned", False):
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
        if not getattr(data_type, "unsigned", False):
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

    def format_data_type_sqlite_integer(self, data_type: SQLiteIntegerType) -> Tuple[str, tuple]:
        """The INTEGER affinity class, so ``INTEGER`` whatever width was asked
        for -- SQLite's documented storage model, not a claim about range.

        ``unsigned`` is refused rather than ignored; see
        :meth:`_refuse_unsigned_integer`. The affinity collapse cannot stand in
        for it: signedness is not a width, so there is no narrower column for a
        wider range to collapse into."""
        self._refuse_unsigned_integer(data_type, "INTEGER")
        return "INTEGER", ()

    def format_data_type_sqlite_text(self, data_type: SQLiteTextType) -> Tuple[str, tuple]:
        length = getattr(data_type, "length", None)
        return (f"TEXT({length})" if length is not None else "TEXT"), ()

    def format_data_type_sqlite_real(self, data_type: SQLiteRealType) -> Tuple[str, tuple]:
        return "REAL", ()

    def format_data_type_sqlite_numeric(self, data_type: SQLiteNumericType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_sqlite_blob(self, data_type: SQLiteBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    # --- Core types (pure names) rendered per SQLite affinity ---

    def format_data_type_integer(self, data_type: IntegerType) -> Tuple[str, tuple]:
        """SQLite accepts both spellings of this one type (its affinity regex
        matches ``INT`` and ``INTEGER`` alike), so the spelling is honoured."""
        if data_type.spelling not in IntegerType.SPELLINGS:
            raise TypeError(
                f"{type(self).__name__} cannot render "
                f"{data_type.spelling!r}; it accepts "
                f"{', '.join(IntegerType.SPELLINGS)}."
            )
        self._refuse_unsigned_integer(data_type, data_type.spelling.upper())
        return ("INT" if data_type.spelling == "int" else "INTEGER"), ()

    def format_data_type_text(self, data_type: TextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_real(self, data_type: RealType) -> Tuple[str, tuple]:
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
        self._refuse_unsigned_numeric(data_type, "REAL")
        return "REAL", ()

    def format_data_type_blob(self, data_type: CoreBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    def format_data_type_bigint(self, data_type: BigIntType) -> Tuple[str, tuple]:
        """Every integer width collapses to ``INTEGER``, which is SQLite's
        documented storage model rather than a claim about width.

        ``unsigned`` is refused rather than ignored; see
        :meth:`_refuse_unsigned_integer`."""
        self._refuse_unsigned_integer(data_type, "INTEGER")
        return "INTEGER", ()

    def format_data_type_smallint(self, data_type: SmallIntType) -> Tuple[str, tuple]:
        """Collapses to ``INTEGER`` like every other integer width, and refuses
        ``unsigned``; see :meth:`_refuse_unsigned_integer`."""
        self._refuse_unsigned_integer(data_type, "INTEGER")
        return "INTEGER", ()

    def format_data_type_varchar(self, data_type: VarCharType) -> Tuple[str, tuple]:
        if data_type.spelling not in VarCharType.SPELLINGS:
            raise TypeError(
                f"{type(self).__name__} cannot render {data_type.spelling!r}; "
                f"it accepts {', '.join(VarCharType.SPELLINGS)}."
            )
        return "TEXT", ()

    def format_data_type_char(self, data_type: CharType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_float(self, data_type: FloatType) -> Tuple[str, tuple]:
        """``FLOAT(p)`` collapses to ``REAL``, which is SQLite's documented
        storage class for approximate numerics, and refuses ``unsigned``; see
        :meth:`_refuse_unsigned_numeric`."""
        self._refuse_unsigned_numeric(data_type, "REAL")
        return "REAL", ()

    def format_data_type_decimal(self, data_type: DecimalType) -> Tuple[str, tuple]:
        """``DECIMAL`` collapses to ``NUMERIC``, which is SQLite's documented
        storage class for fixed-point values, and refuses ``unsigned``; see
        :meth:`_refuse_unsigned_numeric`."""
        if data_type.spelling not in DecimalType.SPELLINGS:
            raise TypeError(
                f"{type(self).__name__} cannot render {data_type.spelling!r}; "
                f"it accepts {', '.join(DecimalType.SPELLINGS)}."
            )
        self._refuse_unsigned_numeric(data_type, "NUMERIC")
        return "NUMERIC", ()

    def format_data_type_boolean(self, data_type: BooleanType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_date(self, data_type: DateType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_datetime(self, data_type: DateTimeType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_timestamp(self, data_type: TimestampType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_time(self, data_type: TimeType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_tinyint(self, data_type: TinyIntType) -> Tuple[str, tuple]:

        """Collapses to ``INTEGER`` like every other integer width, and
        refuses ``unsigned``; see :meth:`_refuse_unsigned_integer`."""
        self._refuse_unsigned_integer(data_type, "INTEGER")
        return "INTEGER", ()

    def format_data_type_double(self, data_type: DoubleType) -> Tuple[str, tuple]:
        """``DOUBLE PRECISION`` collapses to ``REAL``, which is SQLite's
        documented storage class for approximate numerics, and refuses
        ``unsigned``; see :meth:`_refuse_unsigned_numeric`."""
        self._refuse_unsigned_numeric(data_type, "REAL")
        return "REAL", ()

    def format_data_type_timetz(self, data_type: TimeTzType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_timestamptz(self, data_type: TimestampTzType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_interval(self, data_type: IntervalType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_json(self, data_type: JsonType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_jsonb(self, data_type: JsonBType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_custom(self, data_type: CustomType) -> Tuple[str, tuple]:
        return data_type.raw, ()

    # ------------------------------------------------------------------
    #
    # SQLite stores everything through type affinity: any type this mixin
    # renders is genuinely storable, so the ``format_data_type_*`` family
    # above is the whole support declaration — the formatter *is* the
    # "supported" answer. Anything this mixin does not render (e.g. enum,
    # uuid, binary) is honestly absent, and covered by
    # ``suggested_data_types()`` instead.
    # ------------------------------------------------------------------


    # SQLite type affinity groups for parsing.
    #
    # These are SQLite's own affinity rules (https://sqlite.org/datatype3.html)
    # widened by the spellings the core type classes declare in ``SPELLINGS``.
    # A type the framework models must never fall through to ``CustomType``
    # merely because this backend spells its types differently, so every entry of
    # every core ``SPELLINGS`` tuple appears in exactly one group:
    #
    #   ``INT1``   INTEGER affinity — SQLite's rule is "the declared type
    #              *contains* INT", so ``INT1`` was always an INTEGER column and
    #              only this alternation list was missing it.
    #   ``CHARACTER``  TEXT affinity — same rule, "contains CHAR".
    #   ``DEC``    NUMERIC affinity — the unrecognised-type fallback, which is
    #   ``BOOL``   what SQLite has always done with ``DEC`` and ``BOOL``.
    #
    # Nothing else moves: the ``\b`` anchors keep ``CHAR`` from swallowing
    # ``CHARACTER`` and ``DEC`` from swallowing ``DECIMAL``, and the group each
    # spelling lands in is unchanged, so no affinity assignment is revised.
    _INTEGER_TYPES = re.compile(
        r"^(?:INT|INTEGER|BIGINT|SMALLINT|TINYINT|MEDIUMINT"
        r"|INT1|INT2|INT4|INT8)\b",
        re.IGNORECASE,
    )
    _TEXT_TYPES = re.compile(
        r"^(?:TEXT|CHAR|CHARACTER|CHARACTER\s+VARYING"
        r"|VARCHAR|NVARCHAR|NCHAR|CLOB)\b",
        re.IGNORECASE,
    )
    _REAL_TYPES = re.compile(
        r"^(?:REAL|FLOAT|DOUBLE)\b",
        re.IGNORECASE,
    )
    _NUMERIC_TYPES = re.compile(
        r"^(?:NUMERIC|DECIMAL|DEC|BOOLEAN|BOOL|DATE|DATETIME|TIMESTAMP|TIME)\b",
        re.IGNORECASE,
    )
    _BLOB_TYPES = re.compile(
        r"^(?:BLOB|BYTEA|BINARY|VARBINARY)\b",
        re.IGNORECASE,
    )

    def parse_type(self, raw: str) -> DataType:
        """Parse a raw SQL type string according to SQLite type affinity.

        SQLite uses five type affinities:
        - INTEGER: INT, INTEGER, BIGINT, SMALLINT, TINYINT, etc.
        - TEXT: TEXT, CHAR, VARCHAR, CLOB, etc.
        - REAL: REAL, FLOAT, DOUBLE, etc.
        - NUMERIC: NUMERIC, DECIMAL, BOOLEAN, DATE, DATETIME, etc.
        - BLOB: BLOB, BYTEA, etc.

        Returns the corresponding ``SQLite*Type`` for the matched affinity.
        Unknown type strings return ``CustomType``.

        Two properties of the answer are contractual.

        **Every spelling the framework models is recognised.**  Each entry of
        every core ``SPELLINGS`` tuple lands in one of the five groups above, so
        ``INT1``, ``CHARACTER``, ``DEC`` and ``BOOL`` reach a type instead of
        falling off the end into ``CustomType``.  A ``CustomType`` is the
        honest answer only for a name the framework has no concept for.

        **One concept in, one class out.**  All spellings of one concept reach
        the same class, so ``parse_type("INTEGER")`` and ``parse_type("INT")``
        cannot disagree about what a column is.  Which class is the affinity's,
        not the spelling's: SQLite stores ``TINYINT``, ``BIGINT`` and ``INT1``
        in the very same INTEGER-affinity cell and ``CHAR`` in the very same
        TEXT-affinity cell, and reporting them apart would be reporting a
        distinction the database does not make.  So the answer is the affinity
        class, and it is the *concept* class where the affinity names exactly
        one — ``SQLiteIntegerType`` **is** an ``IntegerType``,
        ``SQLiteTextType`` **is** a ``TextType``, ``SQLiteBlobType`` **is** a
        ``BlobType``.  ``SQLiteNumericType`` deliberately derives from no core
        type, because that affinity spans the numeric, boolean and temporal
        families at once; see ``impl/sqlite/expression/types.py``.
        """
        from ..expression.types import (
            SQLiteBlobType,
            SQLiteIntegerType,
            SQLiteNumericType,
            SQLiteRealType,
            SQLiteTextType,
        )

        stripped = raw.strip()
        # Strip UNSIGNED prefix for broader matching (SQLite ignores unsigned)
        if stripped.upper().startswith("UNSIGNED "):
            stripped = stripped[len("UNSIGNED "):].strip()
        upper = stripped.upper()

        # INTEGER affinity
        if self._INTEGER_TYPES.match(upper):
            return SQLiteIntegerType(self)

        # TEXT affinity — try to extract length parameter
        if self._TEXT_TYPES.match(upper):
            length = None
            m = re.search(r"\((\d+)\)", stripped)
            if m:
                length = int(m.group(1))
            return SQLiteTextType(self, length)

        # REAL affinity
        if self._REAL_TYPES.match(upper):
            precision = None
            m = re.search(r"\((\d+)\)", stripped)
            if m:
                precision = int(m.group(1))
            return SQLiteRealType(self, precision)

        # NUMERIC affinity — try to extract precision/scale
        if self._NUMERIC_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return SQLiteNumericType(self, int(nums[0]), int(nums[1]))
            if len(nums) == 1:
                return SQLiteNumericType(self, int(nums[0]))
            return SQLiteNumericType(self)

        # BLOB affinity
        if self._BLOB_TYPES.match(upper):
            return SQLiteBlobType(self)

        return CustomType(self, stripped)
