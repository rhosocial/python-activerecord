# src/rhosocial/activerecord/backend/expression/type_name.py
"""The grammar a SQL type name is allowed to have.

Two positions in a statement take a type name and neither accepts a bound
parameter: ``CAST(expr AS type)`` and PostgreSQL's ``expr::type``. Both are
grammar productions rather than expressions, so there is no ``?`` to bind and
the name has to be rendered into the statement. Anything that ends the type
and starts a new statement, or opens a subquery, goes straight through.

So the defence is the grammar. A type name is an identifier, optionally
qualified, optionally carrying a precision or an array marker — plus the
multi-word built-in names, which are the one thing that is not a bare
identifier. Restricting *characters* rather than the *set of names* is what
keeps user-defined and extension types working: ``vector``, ``hstore``,
``ltree`` and ``myschema.mytype`` are all ordinary identifiers, and nothing in
this module has to know they exist.

Validation lives here rather than in each dialect's formatter because a
per-formatter check is a per-formatter bug waiting to happen — PostgreSQL's
``::`` override is exactly that, having skipped the check the generic
``CAST`` path performs.
"""

# src/rhosocial/activerecord/backend/expression/type_name.py
import re
from typing import Optional


#: Multi-word built-in type names. The only reason a type name is not a bare
#: identifier, and enumerated rather than allowed through by permitting
#: spaces, so that ``INTEGER, (SELECT ...)`` still cannot be spelled.
MULTI_WORD_TYPE_NAMES = frozenset({
    "big int", "binary varying", "bit varying", "character varying",
    "double precision", "national character", "national character varying",
    "time with time zone", "time without time zone",
    "timestamp with time zone", "timestamp without time zone",
    "unsigned big int", "unsigned int", "unsigned small int", "unsigned tiny int",
    "character large object", "binary large object",
})

#: One identifier segment. Deliberately excludes every quote, space and
#: punctuation character that could end the type or begin something else.
_IDENT = r"[A-Za-z_][A-Za-z0-9_$]*"

#: ``schema.name``, then an optional ``(n)`` or ``(n, m)``, then array markers.
_QUALIFIED = rf"{_IDENT}(?:\s*\.\s*{_IDENT})?"
#: Precision is numeric, not an identifier: VARCHAR(255), NUMERIC(10, 2).
_PRECISION = r"(?:\s*\(\s*\d+(?:\s*,\s*\d+)?\s*\))?"

#: Array markers, as many as the type is nested.
_MODIFIERS = rf"{_PRECISION}\s*(?:\[\s*\])*"

_TYPE_NAME_RE = re.compile(rf"^{_QUALIFIED}{_MODIFIERS}$", re.ASCII)


class InvalidTypeNameError(ValueError):
    """Raised when a string cannot be used as a SQL type name.

    A :class:`ValueError` rather than a dialect error, because the name is
    rejected before a dialect is ever consulted: the position it would occupy
    cannot hold a parameter on any backend.
    """

    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(
            f"{value!r} is not a usable SQL type name. A type name is an "
            f"identifier, optionally schema-qualified, optionally with a "
            f"precision such as (10, 2) and array markers: "
            f"varchar(255), myschema.mytype, text[]. "
            f"It cannot contain quotes, semicolons, commas outside the "
            f"parentheses or a comment marker, because that position cannot "
            f"take a bound parameter."
        )


def is_valid_type_name(value: object) -> bool:
    """Whether *value* is a SQL type name this package will render.

    Args:
        value: The candidate, normally a string.

    Returns:
        True when the name matches the grammar above.
    """
    try:
        validate_type_name(value)
    except InvalidTypeNameError:
        return False
    return True


def validate_type_name(value: object) -> str:
    """Return *value* when it is a usable SQL type name, else raise.

    Args:
        value: The candidate, normally a string.

    Returns:
        The name, unchanged, so this can wrap a constructor argument.

    Raises:
        InvalidTypeNameError: If the name cannot be rendered safely.
    """
    if not isinstance(value, str):
        raise InvalidTypeNameError(value)
    # A multi-word built-in may carry a precision or array markers, and the
    # precision is not always at the end: PostgreSQL spells it
    # `timestamp(3) with time zone`. So the words are matched rather than the
    # string, with each word stripped of a trailing precision on the way.
    words = value.split()
    if len(words) > 1:
        bare = []
        for word in words:
            # strip() would only remove the outer parentheses and leave
            # `varying(20`; the word with its precision removed is what the
            # list is keyed by.
            m = re.fullmatch(rf"({_IDENT})\(\s*\d+\s*\)", word)
            bare.append((m.group(1) if m else word).lower())
        if " ".join(bare) in MULTI_WORD_TYPE_NAMES:
            return value
    if _TYPE_NAME_RE.match(value):
        return value
    raise InvalidTypeNameError(value)


__all__ = [
    "InvalidTypeNameError",
    "MULTI_WORD_TYPE_NAMES",
    "is_valid_type_name",
    "validate_type_name",
]
