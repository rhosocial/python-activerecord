# src/rhosocial/activerecord/backend/expression/value_types.py
"""The value lattice: which family a value belongs to, and how to wrap one.

An operation's result family decides which operations the result offers.
``upper()`` yields a string, so ``substr()`` follows; ``length()`` is a legal
string operation whose result is an integer, so ``upper()`` does not. Nothing
checks that at runtime — the narrowing falls out of the types, and an
unavailable method raises :class:`AttributeError` because it was never defined
rather than because something rejected the call.

Families are declared, not inferred from a class hierarchy. ``VALUE_FAMILY``
is read off the expression, which means a backend-defined expression can
declare a family without subclassing anything from here, and an expression
that does not declare one is *unknown* rather than wrong.

This module deliberately imports nothing from the rest of the expression
package. The typed classes import their family constant from here, so a
module-level import in the other direction would be circular; the class
registry is therefore resolved lazily inside :func:`wrap_as`.
"""

# src/rhosocial/activerecord/backend/expression/value_types.py
from typing import Any, Dict, Optional

#: A string value. Operations: upper, lower, substr, length (→ integer), …
STRING = "string"
#: A whole-number value. The result of ``length``, ``row_number``, ``count``.
INTEGER = "integer"
#: A fractional value. The result of ``sqrt``, ``avg``, ``percent_rank``.
NUMERIC = "numeric"
#: A true/false value. Predicates are booleans, so it terminates a chain.
BOOLEAN = "boolean"
#: A date-and-time value. The result of ``now``, ``date_trunc``, ``date_add``.
DATETIME = "datetime"
#: A date without a time component.
DATE = "date"
#: A time without a date component.
TIME = "time"
#: A span of time. The result of ``interval``.
INTERVAL = "interval"
#: A JSON document. The result of ``json_path`` when the path resolves.
JSON = "json"
#: A sequence. The result of ``unnest``, and array columns.
ARRAY = "array"
#: Raw bytes. The result of ``decode``.
BINARY = "binary"
#: A UUID value.
UUID = "uuid"
#: An XML document.
XML = "xml"

#: Every family, for validation and for tooling that enumerates the lattice.
FAMILIES = (
    STRING, INTEGER, NUMERIC, BOOLEAN, DATETIME, DATE, TIME,
    INTERVAL, JSON, ARRAY, BINARY, UUID, XML,
)


def value_type_of(expr: Any) -> Optional[str]:
    """Return the value family *expr* belongs to, or ``None`` if unknown.

    Unknown is a real answer and not a failure: a bare ``FunctionCall``, a
    hand-written ``Column`` or a ``Literal`` carries no family, because nothing
    about them says what a database would return. Callers that need a family
    for such an expression either ask the user or fall back to a permissive
    value.

    Args:
        expr: Any expression node, or ``None``.

    Returns:
        One of :data:`FAMILIES`, or ``None``.
    """
    if expr is None:
        return None
    family = getattr(expr, "VALUE_FAMILY", None)
    return family if family in FAMILIES else None


def common_family(exprs: Any) -> Optional[str]:
    """Return the family every expression in *exprs* agrees on, or ``None``.

    For an operation over several values of one kind — GREATEST, LEAST,
    COALESCE, a CASE — the result is that kind. When the inputs disagree the
    answer is unknown rather than the first one seen or the widest, because
    either of those would hand back a surface the database does not promise:
    GREATEST of an integer and a string is legal SQL and is neither.

    Args:
        exprs: An iterable of expression nodes, or a single node.

    Returns:
        The shared family, or ``None`` if there is not exactly one.
    """
    if isinstance(exprs, (list, tuple)):
        families = {value_type_of(e) for e in exprs}
    else:
        families = {value_type_of(exprs)}
    families.discard(None)
    return families.pop() if len(families) == 1 else None


#: Leading keywords of SQL type names, mapped to the family a cast to them
#: produces. Matched as a prefix of the upper-cased name with any length or
#: precision stripped, so ``VARCHAR(255)``, ``character varying`` and
#: ``NVARCHAR2`` all land on a string.
_SQL_TYPE_FAMILIES = (
    ("BOOL", BOOLEAN),
    ("BIT", BINARY),
    ("VARCHAR", STRING),
    ("CHARACTER", STRING),
    ("CHAR", STRING),
    ("TEXT", STRING),
    ("STRING", STRING),
    ("CLOB", STRING),
    ("ENUM", STRING),
    ("SET", STRING),
    ("TINYINT", INTEGER),
    ("SMALLINT", INTEGER),
    ("MEDIUMINT", INTEGER),
    ("INT", INTEGER),
    ("SERIAL", INTEGER),
    ("BIGINT", INTEGER),
    ("NUMBER", NUMERIC),
    ("NUMERIC", NUMERIC),
    ("DECIMAL", NUMERIC),
    ("DEC", NUMERIC),
    ("FLOAT", NUMERIC),
    ("DOUBLE", NUMERIC),
    ("REAL", NUMERIC),
    ("MONEY", NUMERIC),
    ("DATE", DATETIME),
    ("TIME", DATETIME),
    ("JSON", JSON),
    ("XML", XML),
    ("BLOB", BINARY),
    ("BYTEA", BINARY),
    ("BINARY", BINARY),
    ("RAW", BINARY),
    ("IMAGE", BINARY),
    ("UUID", UUID),
    ("UNIQUEIDENTIFIER", UUID),
)


def family_for_sql_type(sql_type: Any) -> Optional[str]:
    """Return the family a cast to *sql_type* produces, or ``None``.

    A cast states its result in the target type, so this is how ``CAST(x AS
    JSON)`` knows it is a document. An unrecognised name gives ``None`` rather
    than a guess: the alternative is offering JSON navigation on a type nobody
    has heard of.

    Args:
        sql_type: A SQL type name, with or without a length or precision.

    Returns:
        One of :data:`FAMILIES`, or ``None``.
    """
    if not isinstance(sql_type, str):
        return None
    name = sql_type.split("(")[0].strip().upper()
    for prefix, family in _SQL_TYPE_FAMILIES:
        if name.startswith(prefix):
            return family
    # SQL Server and Oracle prefix a Unicode type with N: NVARCHAR2 is a
    # string, NCHAR is a string, and nothing else in the table starts with N.
    if name.startswith("N") and name[1:]:
        return family_for_sql_type(name[1:])
    return None


def wrap_as(dialect: Any, call: Any, family: Optional[str]) -> Any:
    """Wrap a rendered call in the value expression for *family*.

    Args:
        dialect: The dialect that will render the expression.
        call: The underlying node, typically a ``FunctionCall``.
        family: The value family, or ``None`` for a family that has no typed
            expression yet.

    Returns:
        A typed value expression, or *call* unchanged when the family is
        unknown or not yet modelled. Returning the node untouched is what makes
        this safe to apply to every factory: an unmodelled family degrades to
        today's behaviour instead of breaking.
    """
    if family is None:
        return call
    wrapper = _wrapper_registry().get(family)
    if wrapper is None:
        return call
    # The family is passed as well as looked up: one class can serve several
    # families, as DateTimeValueExpression does for a date, a time, a
    # timestamp and a span, which offer the same operations.
    try:
        return wrapper(dialect, call, family)
    except TypeError:
        return wrapper(dialect, call)


def _wrapper_registry() -> Dict[str, Any]:
    """Resolve the family-to-class registry.

    Imported lazily because the typed value expressions live in modules that
    import this one for their family constants.
    """
    global _WRAPPERS
    if _WRAPPERS is None:
        from .core import (
            ArrayValueExpression,
            BinaryValueExpression,
            BooleanValueExpression,
            DateTimeValueExpression,
            IntegerValueExpression,
            JSONValueExpression,
            NumericValueExpression,
            StringValueExpression,
            UUIDValueExpression,
        )

        _WRAPPERS = {
            STRING: StringValueExpression,
            INTEGER: IntegerValueExpression,
            NUMERIC: NumericValueExpression,
            DATETIME: DateTimeValueExpression,
            DATE: DateTimeValueExpression,
            TIME: DateTimeValueExpression,
            INTERVAL: DateTimeValueExpression,
            JSON: JSONValueExpression,
            ARRAY: ArrayValueExpression,
            BOOLEAN: BooleanValueExpression,
            BINARY: BinaryValueExpression,
            UUID: UUIDValueExpression,
        }
    return _WRAPPERS


_WRAPPERS: Optional[Dict[str, Any]] = None


__all__ = [
    "ARRAY", "BINARY", "BOOLEAN", "DATETIME", "DATE", "FAMILIES", "INTEGER",
    "INTERVAL", "JSON", "NUMERIC", "STRING", "TIME", "UUID", "XML",
    "common_family", "family_for_sql_type", "value_type_of", "wrap_as",
]
