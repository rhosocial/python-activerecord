# src/rhosocial/activerecord/backend/dialect/mixins/ddl_type.py
"""``DDLTypeMixin`` — registry-based type formatting mechanism.

Each backend registers its own ``DataType`` formatters via
``@DDLTypeMixin.handles(TypeClass)``.  The base mixin provides default
formatters for the portable **generic** core types so every dialect can render
them (SQL-standard forms) even before backend-specific overrides are added.

.. note::

   ``handles`` is a plain decorator function that tags the decorated method and
   is re-attached to the mixin as a staticmethod.  ``__init_subclass__`` walks
   the MRO in definition order (base → subclass) to build a per-subclass
   ``_type_formatters`` dict, so a backend's own ``@handles(<SameType>)``
   registration deterministically overrides the base default — it does **not**
   depend on member-name ordering.
"""

from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING

from ...expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntType,
    IntegerType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimeType,
    TimestampType,
    VarCharType,
)

if TYPE_CHECKING:
    from ...expression.types._base import DataType


SQLQueryAndParams = Tuple[str, tuple]

#: Module prefix of the core generic ``DataType`` classes.  Parent-class
#: dispatch in :meth:`DDLTypeMixin.format_data_type` is limited to types
#: defined under this prefix (i.e. core generic types and their core aliases
#: such as ``IntType``).  Backend-specific types defined in
#: ``backend/impl/<name>/...`` are **not** silently absorbed by a parent
#: handler: they must be registered explicitly on each backend that supports
#: them, otherwise rendering raises.
_CORE_TYPES_PREFIX = "rhosocial.activerecord.backend.expression.types"


def handles(*data_type_classes):
    """Decorator — tag a method as a formatter for *data_type_classes*.

    The actual registration happens in ``__init_subclass__`` so each subclass
    gets its own isolated registry.
    """
    def decorator(fn):
        fn._handles_types = data_type_classes
        return fn
    return decorator


class DDLTypeMixin:
    """Mixin providing registry-based ``format_data_type()`` dispatch.

    Subclasses register formatters via the :meth:`handles` decorator::

        class MySQLTypeSupportMixin(DDLTypeMixin):
            @DDLTypeMixin.handles(MySQLIntType)
            def format_data_type_int(self, data_type: MySQLIntType) -> SQLQueryAndParams:
                return "INT UNSIGNED" if data_type.unsigned else "INT", ()

    ``format_data_type()`` first looks for an exact-class registration; when
    the concrete type is a core generic type, it falls back to the nearest
    registered ancestor (e.g. ``IntType`` → ``IntegerType`` handler).
    Backend-specific types (defined outside the core types package) are **not**
    matched by ancestor registration — an explicit ``@handles`` is required.

    Unregistered types raise ``TypeError``.
    """

    _type_formatters: dict = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        formatters = {}
        for klass in reversed(cls.__mro__):
            for member_name, member in vars(klass).items():
                handles_types = getattr(member, "_handles_types", None)
                if handles_types is not None:
                    for dt_cls in handles_types:
                        formatters[dt_cls] = member_name
        cls._type_formatters = formatters

    # ------------------------------------------------------------------
    # Base default formatters for generic (portable) core types.
    # Backends override by tagging their own @handles(<SameType>); the
    # MRO-aware registry build makes the backend registration win.
    # ------------------------------------------------------------------

    @handles(IntegerType, IntType)
    def _default_integer(self, data_type) -> SQLQueryAndParams:
        return "INTEGER", ()

    @handles(SmallIntType)
    def _default_smallint(self, data_type) -> SQLQueryAndParams:
        return "SMALLINT", ()

    @handles(BigIntType)
    def _default_bigint(self, data_type) -> SQLQueryAndParams:
        return "BIGINT", ()

    @handles(FloatType)
    def _default_float(self, data_type) -> SQLQueryAndParams:
        return (f"FLOAT({data_type.precision})" if data_type.precision is not None else "FLOAT"), ()

    @handles(RealType)
    def _default_real(self, data_type) -> SQLQueryAndParams:
        return "REAL", ()

    @handles(DoubleType)
    def _default_double(self, data_type) -> SQLQueryAndParams:
        return "DOUBLE PRECISION", ()

    @handles(DecimalType)
    def _default_decimal(self, data_type) -> SQLQueryAndParams:
        sql = "DECIMAL"
        if data_type.precision is not None:
            sql += f"({data_type.precision}"
            if data_type.scale is not None:
                sql += f", {data_type.scale}"
            sql += ")"
        return sql, ()

    @handles(BooleanType)
    def _default_boolean(self, data_type) -> SQLQueryAndParams:
        return "BOOLEAN", ()

    @handles(CharType)
    def _default_char(self, data_type) -> SQLQueryAndParams:
        return (f"CHAR({data_type.length})" if data_type.length is not None else "CHAR"), ()

    @handles(VarCharType)
    def _default_varchar(self, data_type) -> SQLQueryAndParams:
        return (f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"), ()

    @handles(TextType)
    def _default_text(self, data_type) -> SQLQueryAndParams:
        return "TEXT", ()

    @handles(BlobType)
    def _default_blob(self, data_type) -> SQLQueryAndParams:
        return "BLOB", ()

    @handles(DateType)
    def _default_date(self, data_type) -> SQLQueryAndParams:
        return "DATE", ()

    @handles(TimeType)
    def _default_time(self, data_type) -> SQLQueryAndParams:
        return (f"TIME({data_type.precision})" if data_type.precision is not None else "TIME"), ()

    @handles(DateTimeType)
    def _default_datetime(self, data_type) -> SQLQueryAndParams:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    @handles(TimestampType)
    def _default_timestamp(self, data_type) -> SQLQueryAndParams:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    @handles(JsonType)
    def _default_json(self, data_type) -> SQLQueryAndParams:
        return "JSON", ()

    # NOTE: ``CustomType`` deliberately has NO base default renderer. Raw SQL
    # passthrough is a security-sensitive escape hatch, so each backend must
    # explicitly opt in by registering ``@handles(CustomType)`` (SQLite, SQL
    # Server, dummy do). On backends without a registration, rendering a
    # ``CustomType`` raises instead of silently emitting the raw string.

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def format_data_type(self, data_type: DataType) -> SQLQueryAndParams:
        formatter = self._find_formatter(type(data_type))
        if formatter is None:
            dt_cls = type(data_type)
            raise TypeError(
                f"{type(self).__name__} has no formatter for "
                f"{dt_cls.__module__}.{dt_cls.__qualname__}. Register it via "
                f"@DDLTypeMixin.handles(...) or use a type this backend supports."
            )
        return getattr(self, formatter)(data_type)

    def _find_formatter(self, dt_cls: type) -> Optional[str]:
        """Return the registered formatter method name for *dt_cls*, or None."""
        for klass in type(self).__mro__:
            formatters = getattr(klass, "_type_formatters", {})
            if dt_cls in formatters:
                return formatters[dt_cls]
        if dt_cls.__module__.startswith(_CORE_TYPES_PREFIX):
            for klass in type(self).__mro__:
                formatters = getattr(klass, "_type_formatters", {})
                for registered_cls, method_name in formatters.items():
                    if issubclass(dt_cls, registered_cls):
                        return method_name
        return None

    def supports_data_type(self, data_type_or_class) -> bool:
        """Whether this dialect can render *data_type_or_class*.

        Accepts either a ``DataType`` instance or a ``DataType`` subclass.
        """
        dt_cls = data_type_or_class if isinstance(data_type_or_class, type) else type(data_type_or_class)
        return self._find_formatter(dt_cls) is not None

    def supports_data_types(self) -> list[tuple[type, str]]:
        """Return ``(DataTypeClass, sql_name)`` pairs from the registry.

        Auto-generated from ``@handles`` registrations so it stays in sync
        without manual maintenance.
        """
        result = []
        seen = set()
        for klass in type(self).__mro__:
            for dt_cls, method_name in getattr(klass, "_type_formatters", {}).items():
                if dt_cls not in seen:
                    seen.add(dt_cls)
                    try:
                        sql_name, _ = getattr(self, method_name)(dt_cls())
                    except TypeError:
                        sql_name = dt_cls.__name__
                    result.append((dt_cls, sql_name))
        return result


DDLTypeMixin.handles = staticmethod(handles)


class DDLTypeSuggestionMixin:
    """Mixin providing ``suggest_column_type()`` for DDL generation.

    The default mapping is backend-neutral ("reasonable lowest common
    denominator"): it deliberately avoids backend-specific types such as
    PostgreSQL ``UUID``/``JSONB`` or MySQL ``ENUM``. Backend dialects that
    want richer suggestions override :meth:`suggest_column_type` directly.

    Resolution order in the caller (``ModelSchemaGenerator``):

    1. field-level ``UseSqlType`` annotation wins outright;
    2. otherwise ``dialect.suggest_column_type(python_type)`` is consulted;
    3. ``None`` return falls back to this neutral default.
    """

    def suggest_column_type(
        self, python_type: type, version: "Optional[Tuple[int, int, int]]" = None
    ) -> "Optional[DataType]":
        """Return the neutral default ``DataType`` for *python_type*.

        The neutral mapping is backend- and version-agnostic, so *version* is
        ignored here; backend-specific mixins override this method to make
        version-gated decisions.
        """
        return _NEUTRAL_TYPE_SUGGESTIONS.get(python_type)


def _build_neutral_suggestions() -> dict:
    import datetime as _dt
    import decimal as _dec
    import enum as _enum
    import uuid as _uuid

    from ...expression.types import (
        BlobType,
        BooleanType,
        DateType,
        DateTimeType,
        DecimalType,
        DoubleType,
        IntegerType,
        TextType,
        TimeType,
        VarCharType,
    )

    return {
        str: TextType(),
        int: IntegerType(),
        bool: BooleanType(),
        float: DoubleType(),
        bytes: BlobType(),
        _dt.datetime: DateTimeType(),
        _dt.date: DateType(),
        _dt.time: TimeType(),
        _dec.Decimal: DecimalType(),
        _uuid.UUID: VarCharType(length=36),
        dict: TextType(),
        list: TextType(),
        _enum.Enum: VarCharType(length=64),
    }


_NEUTRAL_TYPE_SUGGESTIONS: dict = _build_neutral_suggestions()