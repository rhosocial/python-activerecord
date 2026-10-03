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
module-level import in the other direction would be circular; the typed value
expressions therefore never import this module's classes back.
"""

# src/rhosocial/activerecord/backend/expression/value_types.py
from typing import Any, Optional

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


def family_for_data_type(data_type: Any) -> Optional[str]:
    """Return the value family a cast to *data_type* produces.

    Keyed on the type object's own ``name`` rather than on a rendered string,
    so the family travels with the type and a cast cannot disagree with it. An
    unrecognised type leaves the family unknown rather than guessed.

    Args:
        data_type: A :class:`DataType` instance.

    Returns:
        One of :data:`FAMILIES`, or ``None``.
    """
    name = getattr(data_type, "name", None)
    if not isinstance(name, str):
        return None
    from .type_name import family_for_sql_type_name

    return family_for_sql_type_name(name)




def family_for_sql_type(sql_type: Any) -> Optional[str]:
    """Return the value family a SQL type name belongs to, or ``None``.

    Kept for callers that hold a name rather than a type. The mapping lives in
    :mod:`...expression.type_name` beside the grammar that decides whether a
    name is renderable at all, because both answer the same question from the
    same input.

    Args:
        sql_type: A SQL type name, with or without a length or precision.

    Returns:
        One of :data:`FAMILIES`, or ``None`` when unrecognised.
    """
    from .type_name import family_for_sql_type_name

    return family_for_sql_type_name(sql_type)



__all__ = [
    "ARRAY", "BINARY", "BOOLEAN", "DATETIME", "DATE", "FAMILIES", "INTEGER",
    "INTERVAL", "JSON", "NUMERIC", "STRING", "TIME", "UUID", "XML",
    "family_for_sql_type", "value_type_of",
]
