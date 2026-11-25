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


#: Multi-word built-in type names. The only reason a type name is not a bare
#: identifier, and enumerated rather than allowed through by permitting
#: spaces, so that ``INTEGER, (SELECT ...)`` still cannot be spelled.
MULTI_WORD_TYPE_NAMES = frozenset({
    "big int", "binary varying", "bit varying", "character varying",
    "double precision", "national character", "national character varying",
    "time with time zone", "time without time zone",
    "timestamp with time zone", "timestamp without time zone",
    "timestamp with local time zone",
    "unsigned big int", "unsigned int", "unsigned small int", "unsigned tiny int",
    "character large object", "binary large object",
})

#: The whitespace an ASCII-flagged pattern admits, written as character codes
#: so the set is exact rather than a guess about one platform's ``isspace``.
_ASCII_SPACE = frozenset(chr(code) for code in (9, 10, 11, 12, 13, 32))


def _skip_space(text: str, index: int) -> int:
    """Index past any whitespace character."""
    while index < len(text) and text[index].isspace():
        index += 1
    return index


def _skip_ascii_space(text: str, index: int) -> int:
    """Index past the whitespace an ASCII-flagged grammar admits."""
    while index < len(text) and text[index] in _ASCII_SPACE:
        index += 1
    return index


def _consume_identifier(text: str, index: int, extra: str = "") -> int:
    """End index of the identifier beginning at *index*, or ``-1``.

    An identifier starts with a letter or underscore and continues with
    letters, digits, underscores and any characters in *extra*. Every quote,
    space and punctuation character that could end the type or begin a new
    statement is thereby excluded. A ``-1`` means no identifier begins exactly
    at *index*.
    """
    length = len(text)
    if index >= length:
        return -1
    first = text[index]
    if not ("A" <= first <= "Z" or "a" <= first <= "z" or first == "_"):
        return -1
    index += 1
    while index < length:
        char = text[index]
        if (
            "A" <= char <= "Z"
            or "a" <= char <= "z"
            or "0" <= char <= "9"
            or char == "_"
            or char in extra
        ):
            index += 1
        else:
            break
    return index


def _consume_digits(text: str, index: int, *, ascii_only: bool = True) -> int:
    """End index of the digit run beginning at *index*, or ``-1``."""
    length = len(text)
    start = index
    while index < length:
        if ascii_only:
            if not ("0" <= text[index] <= "9"):
                break
        elif not text[index].isdecimal():
            break
        index += 1
    return index if index > start else -1


def _is_type_name(value: str) -> bool:
    """Whether *value* is a qualified identifier with precision and arrays.

    The grammar is ``IDENT[.IDENT]``, an optional ``(n)`` or ``(n, m)``
    precision, then any number of ``[]`` array markers -- with whitespace
    allowed around the qualifier dot, inside the precision and inside the
    array brackets. The precision digits and the admitted whitespace are
    ASCII, which is the one difference between this and a Unicode pattern.
    """
    length = len(value)
    index = _consume_identifier(value, 0, extra="$")
    if index == -1:
        return False

    qualified = _skip_ascii_space(value, index)
    if qualified < length and value[qualified] == ".":
        index = _consume_identifier(value, _skip_ascii_space(value, qualified + 1), extra="$")
        if index == -1:
            return False

    index = _skip_ascii_space(value, index)
    if index < length and value[index] == "(":
        index = _consume_digits(value, _skip_ascii_space(value, index + 1))
        if index == -1:
            return False
        index = _skip_ascii_space(value, index)
        if index < length and value[index] == ",":
            index = _consume_digits(value, _skip_ascii_space(value, index + 1))
            if index == -1:
                return False
            index = _skip_ascii_space(value, index)
        if index >= length or value[index] != ")":
            return False
        index += 1
        index = _skip_ascii_space(value, index)

    while index < length and value[index] == "[":
        index = _skip_ascii_space(value, index + 1)
        if index >= length or value[index] != "]":
            return False
        index += 1
    return index == length


def _bare_word(word: str) -> str:
    """The identifier of *word* when it carries a trailing ``(n)``, else *word*.

    A multi-word built-in may put its precision on either side of the words --
    PostgreSQL writes ``timestamp(3) with time zone`` -- so each word is
    compared without its precision. ``timestamp(3)`` reads as ``timestamp``;
    anything else is returned unchanged.
    """
    identifier_end = _consume_identifier(word, 0, extra="$")
    if identifier_end == -1:
        return word
    index = identifier_end
    if index >= len(word) or word[index] != "(":
        return word
    index = _consume_digits(word, _skip_space(word, index + 1), ascii_only=False)
    if index == -1:
        return word
    index = _skip_space(word, index)
    if index >= len(word) or word[index] != ")":
        return word
    if index + 1 != len(word):
        return word
    return word[:identifier_end]


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
            bare.append(_bare_word(word).lower())
        if " ".join(bare) in MULTI_WORD_TYPE_NAMES:
            return value
    if _is_type_name(value):
        return value
    raise InvalidTypeNameError(value)


__all__ = [
    "InvalidTypeNameError",
    "MULTI_WORD_TYPE_NAMES",
    "is_valid_type_name",
    "validate_type_name",
]
