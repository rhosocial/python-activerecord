# src/rhosocial/activerecord/backend/expression/functions/string.py
"""String function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import (
    FunctionCall,
    IntegerValueExpression,
    Literal,
    StringValueExpression,
)
from ..operators import BinaryExpression, StringConcatExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..advanced_functions import (
        LpadExpression,
        RepeatExpression,
        RpadExpression,
        TrimExpression,
    )


def concat(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "StringValueExpression":
    """
    Creates a CONCAT scalar function call.

    Usage rules:
    - To generate CONCAT(column1, column2, ...), pass Column objects: concat(dialect, Column(...), Column(...))
    - To generate CONCAT(?, ?, ...), pass literal values: concat(dialect, "value1", "value2")

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to concatenate. If strings are passed, they're treated as literal values.
                If BaseExpressions are passed, they're used as-is.

    Returns:
        A FunctionCall instance representing the CONCAT function
    """
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]
    return StringValueExpression(dialect, FunctionCall(dialect, "CONCAT", *target_exprs))


def coalesce(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "StringValueExpression":
    """
    Creates a COALESCE scalar function call.

    Usage rules:
    - To generate COALESCE(column1, column2, ...), pass Column objects: coalesce(dialect, Column(...), Column(...))
    - To generate COALESCE(?, ?, ...), pass literal values: coalesce(dialect, "value1", "value2")

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to coalesce. If strings are passed, they're treated as literal values.
                If BaseExpressions are passed, they're used as-is.

    Returns:
        A FunctionCall instance representing the COALESCE function
    """
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]
    return StringValueExpression(dialect, FunctionCall(dialect, "COALESCE", *target_exprs))


def length(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "IntegerValueExpression":
    """
    Creates a LENGTH scalar function call.

    Usage rules:
    - To generate LENGTH(column), pass a Column object: length(dialect, Column(dialect, "column_name"))
    - To generate LENGTH(?), pass a literal value: length(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to measure length of. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the LENGTH function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return IntegerValueExpression(dialect, FunctionCall(dialect, "LENGTH", target_expr))


def substring(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    start: Union[int, "BaseExpression"],
    length: Optional[Union[int, "BaseExpression"]] = None,
) -> "FunctionCall":
    """
    Creates a SUBSTRING scalar function call.

    Usage rules:
    - To generate SUBSTRING(column, start, length), pass a Column object as expr and integers for start/length:
      substring(dialect, Column(dialect, "column_name"), 1, 5)
    - To generate SUBSTRING(?, ?, ?), pass literal values: substring(dialect, "text", 1, 5)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract substring from. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        start: Starting position for extraction. If an integer is passed, it's treated as a literal value.
        length: Optional ending position or length. If provided, it's treated as a literal value.

    Returns:
        A FunctionCall instance representing the SUBSTRING function

    Raises:
        ValueError: A literal *start* below 1, or a literal *length* below 0.

    Contract:
        ``start`` is 1-based and ``length`` counts forward. Both edges were
        measured across the ten backends (2026-10-09) and are refused here
        rather than rendered, because the backends do not agree on what an
        out-of-range argument means: a position below 1 is consumed by the
        length on PostgreSQL, SQL Server, Firebird and SQLite, yields an empty
        string on MySQL, MariaDB and ClickHouse, and is read as 1 on Oracle; a
        negative length is an error on some backends, an empty string on
        MySQL/MariaDB, NULL on Oracle and something unrelated again on
        ClickHouse.
    """
    if isinstance(start, int) and start < 1:
        raise ValueError(
            f"substring(): start must be >= 1 (positions are 1-based), got {start!r}"
        )
    if isinstance(length, int) and length < 0:
        raise ValueError(f"substring(): length must be >= 0, got {length!r}")
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    start_expr = start if isinstance(start, BaseExpression) else Literal(dialect, start)
    if length is not None:
        length_expr = length if isinstance(length, BaseExpression) else Literal(dialect, length)
        return StringValueExpression(dialect, FunctionCall(dialect, "SUBSTRING", target_expr, start_expr, length_expr))
    return StringValueExpression(dialect, FunctionCall(dialect, "SUBSTRING", target_expr, start_expr))


def trim(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    chars: Optional[Union[str, "BaseExpression"]] = None,
    direction: str = "BOTH",
) -> "TrimExpression":
    """
    Creates a TRIM node.

    Usage rules:
    - To generate TRIM(BOTH FROM column), pass a Column object: trim(dialect, Column(dialect, "column_name"))
    - To generate TRIM(BOTH chars FROM ?), pass literal values: trim(dialect, "text", " ", "BOTH")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to trim. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        chars: Optional single character to trim. If provided, treated as
            literal value if string.
        direction: Direction of trim operation (BOTH, LEADING, TRAILING). Default is BOTH.

    Returns:
        A :class:`~...expression.advanced_functions.TrimExpression` node, which
        the dialect renders through its ``format_trim_expression`` hook.

    Raises:
        ValueError: An unknown *direction*, or a trim set that is not exactly
            one character.

    Contract:
        The trim set is **one character**, which is what SQL:2016 feature
        E021-09 (``trim(<char> from ...)``) defines and what every backend
        agrees on. A multi-character set means three different things in the
        wild -- a character set on PostgreSQL, SQL Server, ClickHouse and
        Snowflake, a whole string repeated on MySQL, MariaDB and Firebird, and
        ``ORA-30001`` on Oracle -- so it is refused at construction instead of
        rendered into whichever of the three the backend happens to implement.
        The node, not a raw SQL string, is what makes the dialect's spelling a
        formatter's decision: SQLite overrides the hook because it parses no
        ``trim(... from ...)`` syntax at all.
    """
    # Validate direction: only allow known trim directions.
    valid_directions = frozenset({"BOTH", "LEADING", "TRAILING"})
    if direction not in valid_directions:
        raise ValueError(f"Invalid trim direction '{direction}': must be one of {valid_directions}")
    if isinstance(chars, str) and len(chars) != 1:
        raise ValueError(
            f"Invalid trim set {chars!r}: must be exactly one character -- SQL:2016 "
            "feature E021-09 defines trim(<char> from ...), and a multi-character "
            "set means three different things across the backends"
        )

    from ..advanced_functions import TrimExpression

    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    chars_expr: Optional[BaseExpression] = None
    if chars is not None:
        chars_expr = chars if isinstance(chars, BaseExpression) else Literal(dialect, chars)
    return TrimExpression(dialect, target_expr, chars_expr, direction)


def replace(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    pattern: Union[str, "BaseExpression"],
    replacement: Union[str, "BaseExpression"],
) -> "FunctionCall":
    """
    Creates a REPLACE scalar function call.

    Usage rules:
    - To generate REPLACE(column, pattern, replacement), pass Column objects:
      replace(dialect, Column(dialect, "column_name"), "old", "new")
    - To generate REPLACE(?, ?, ?), pass literal values: replace(dialect, "text", "old", "new")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to perform replacement on. If a string is passed, it's treated as a literal value.
        pattern: Pattern to find. If a string is passed, it's treated as a literal value.
        replacement: Replacement value. If a string is passed, it's treated as a literal value.

    Returns:
        A FunctionCall instance representing the REPLACE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    pattern_expr = pattern if isinstance(pattern, BaseExpression) else Literal(dialect, pattern)
    replacement_expr = replacement if isinstance(replacement, BaseExpression) else Literal(dialect, replacement)
    return StringValueExpression(dialect, FunctionCall(dialect, "REPLACE", target_expr, pattern_expr, replacement_expr))


def upper(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates an UPPER scalar function call.

    Usage rules:
    - To generate UPPER(column), pass a Column object: upper(dialect, Column(dialect, "column_name"))
    - To generate UPPER(?), pass a literal value: upper(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to uppercase. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the UPPER function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return StringValueExpression(dialect, FunctionCall(dialect, "UPPER", target_expr))


def lower(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a LOWER scalar function call.

    Usage rules:
    - To generate LOWER(column), pass a Column object: lower(dialect, Column(dialect, "column_name"))
    - To generate LOWER(?), pass a literal value: lower(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to lowercase. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the LOWER function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return StringValueExpression(dialect, FunctionCall(dialect, "LOWER", target_expr))


def initcap(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates an INITCAP scalar function call (title case).

    Usage rules:
    - To generate INITCAP(column), pass a Column object: initcap(dialect, Column(dialect, "column_name"))
    - To generate INITCAP(?), pass a literal value: initcap(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to title case. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the INITCAP function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return StringValueExpression(dialect, FunctionCall(dialect, "INITCAP", target_expr))


def left(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], n: int) -> "FunctionCall":
    """
    Creates a LEFT scalar function call.

    Usage rules:
    - To generate LEFT(column, n), pass a Column object: left(dialect, Column(dialect, "column_name"), 5)
    - To generate LEFT(?, n), pass a literal value: left(dialect, "text", 5)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract left portion from. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        n: Number of characters to extract from the left.

    Returns:
        A FunctionCall instance representing the LEFT function

    Raises:
        ValueError: If *n* is negative.

    Contract:
        ``n >= 0``, and everything above it is portable: 0 is the empty string
        and more than the length is the whole string on every backend. Below 0
        the backends answer four different ways -- PostgreSQL and ClickHouse
        drop the trailing ``|n|`` characters, MySQL, MariaDB and Snowflake
        return an empty string, SQL Server and Firebird raise, and BigQuery
        raises -- so a negative count is refused rather than rendered.
    """
    if isinstance(n, int) and n < 0:
        raise ValueError(f"left(): n must be >= 0, got {n!r}")
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    n_expr = Literal(dialect, n)
    return StringValueExpression(dialect, FunctionCall(dialect, "LEFT", target_expr, n_expr))


def right(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], n: int) -> "FunctionCall":
    """
    Creates a RIGHT scalar function call.

    Usage rules:
    - To generate RIGHT(column, n), pass a Column object: right(dialect, Column(dialect, "column_name"), 5)
    - To generate RIGHT(?, n), pass a literal value: right(dialect, "text", 5)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract right portion from. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        n: Number of characters to extract from the right.

    Returns:
        A FunctionCall instance representing the RIGHT function

    Raises:
        ValueError: If *n* is negative.

    Contract:
        The mirror of :func:`left` -- ``n >= 0``, 0 is the empty string, more
        than the length is the whole string, and a negative count is refused
        because no two backends agree on it (see :func:`left`).
    """
    if isinstance(n, int) and n < 0:
        raise ValueError(f"right(): n must be >= 0, got {n!r}")
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    n_expr = Literal(dialect, n)
    return StringValueExpression(dialect, FunctionCall(dialect, "RIGHT", target_expr, n_expr))


def lpad(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], length: int, pad: Optional[str] = None
) -> "LpadExpression":
    """
    Creates a left-padding node.

    Usage rules:
    - To generate LPAD(column, length, pad), pass a Column object:
      lpad(dialect, Column(dialect, "column_name"), 10, "0")
    - To generate LPAD(?, length, pad), pass a literal value: lpad(dialect, "text", 10, "0")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to pad. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        length: Total length after padding.
        pad: Optional padding string, non-empty. Defaults to a single space.

    Returns:
        A :class:`~...expression.advanced_functions.LpadExpression` node, which
        the dialect renders through ``format_lpad_expression`` -- a spelling
        where the function exists (PostgreSQL, MySQL, MariaDB, Oracle,
        Firebird, ClickHouse, Snowflake, BigQuery) and an emulation composed
        from ordinary nodes where it does not (SQLite).

    Raises:
        ValueError: A negative *length*, or an empty *pad*.

    Contract:
        ``length >= 0`` and the pad is non-empty; an omitted pad means one
        space, and it is always passed explicitly because the backends differ
        on whether the argument is optional at all (MySQL raises 1582 without
        it, MariaDB fills with spaces). An empty pad is refused: measured
        2026-10-09, it leaves the string alone on PostgreSQL/Firebird/Snowflake,
        returns an empty string on MySQL 8.0, the untouched string on MySQL 26
        (the same server, two answers), NULL on MariaDB/Oracle and pads with
        spaces on ClickHouse.
    """
    if isinstance(length, int) and length < 0:
        raise ValueError(f"lpad(): length must be >= 0, got {length!r}")
    if isinstance(pad, str) and pad == "":
        raise ValueError(
            "lpad(): empty pad string is refused -- backends disagree on what it "
            "means (untouched string, empty string or NULL)"
        )
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    length_expr = length if isinstance(length, BaseExpression) else Literal(dialect, length)
    pad_expr = pad if isinstance(pad, BaseExpression) else Literal(dialect, " " if pad is None else pad)
    from ..advanced_functions import LpadExpression

    return LpadExpression(dialect, target_expr, length_expr, pad_expr)


def rpad(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], length: int, pad: Optional[str] = None
) -> "RpadExpression":
    """
    Creates a right-padding node.

    Usage rules:
    - To generate RPAD(column, length, pad), pass a Column object:
      rpad(dialect, Column(dialect, "column_name"), 10, " ")
    - To generate RPAD(?, length, pad), pass a literal value: rpad(dialect, "text", 10, " ")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to pad. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        length: Total length after padding.
        pad: Optional padding string, non-empty. Defaults to a single space.

    Returns:
        A :class:`~...expression.advanced_functions.RpadExpression` node,
        rendered through ``format_rpad_expression`` -- a spelling where the
        function exists and a one-branch emulation where it does not.

    Raises:
        ValueError: A negative *length*, or an empty *pad*.

    Contract:
        The mirror of :func:`lpad`: ``length >= 0``, a non-empty pad, an
        omitted pad spelled out as one space, and an empty pad refused.
    """
    if isinstance(length, int) and length < 0:
        raise ValueError(f"rpad(): length must be >= 0, got {length!r}")
    if isinstance(pad, str) and pad == "":
        raise ValueError(
            "rpad(): empty pad string is refused -- backends disagree on what it "
            "means (untouched string, empty string or NULL)"
        )
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    length_expr = length if isinstance(length, BaseExpression) else Literal(dialect, length)
    pad_expr = pad if isinstance(pad, BaseExpression) else Literal(dialect, " " if pad is None else pad)
    from ..advanced_functions import RpadExpression

    return RpadExpression(dialect, target_expr, length_expr, pad_expr)


def reverse(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a REVERSE scalar function call.

    Usage rules:
    - To generate REVERSE(column), pass a Column object: reverse(dialect, Column(dialect, "column_name"))
    - To generate REVERSE(?), pass a literal value: reverse(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to reverse. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the REVERSE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return StringValueExpression(dialect, FunctionCall(dialect, "REVERSE", target_expr))


def strpos(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], substring: Union[str, "BaseExpression"]
) -> "IntegerValueExpression":
    """
    Creates a STRPOS scalar function call (position of substring).

    Usage rules:
    - To generate STRPOS(column, substring), pass Column objects:
      strpos(dialect, Column(dialect, "column_name"), "substr")
    - To generate STRPOS(?, ?), pass literal values: strpos(dialect, "text", "substr")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to search in. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        substring: Substring to find. If a string is passed, it's treated as a literal value.

    Returns:
        A FunctionCall instance representing the STRPOS function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    substr_expr = substring if isinstance(substring, BaseExpression) else Literal(dialect, substring)
    return IntegerValueExpression(dialect, FunctionCall(dialect, "STRPOS", target_expr, substr_expr))


def concat_op(
    dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]
) -> "BinaryExpression":
    """Creates a string concatenation using the ``||`` operator.

    Deliberately not offered as a ``StringValueMixin`` method. ``||`` does not
    mean concatenation everywhere — in MySQL it is logical OR by default — so
    an operation reachable from a string column would silently produce a
    boolean on some backends. Use :func:`concat`, whose meaning is the same
    everywhere.

    Usage rules:
    - To generate column1 || column2, pass Column objects:
      concat_op(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate ? || ?, pass literal values: concat_op(dialect, "value1", "value2")
    - To generate complex concatenations: concat_op(dialect, col1, lit1, col2, lit2)

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to concatenate using || operator

    Returns:
        A BinaryExpression instance representing the || concatenation operation
    """
    if len(exprs) < 2:
        raise ValueError("Concatenation operation requires at least 2 expressions")

    # Convert all expressions to BaseExpression objects
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]

    # Start with the first two expressions
    result = StringConcatExpression(dialect, target_exprs[0], target_exprs[1])

    # Chain additional expressions
    for i in range(2, len(target_exprs)):
        result = StringConcatExpression(dialect, result, target_exprs[i])

    return result


def chr_(dialect: "SQLDialectBase", code: Union[int, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a CHR function call.

    SQL:2003 standard function converting integer code to character.

    Usage rules:
    - To generate CHR(column): chr_(dialect, Column(dialect, "code"))
    - To generate CHR(65): chr_(dialect, 65)  # Returns 'A'

    Args:
        dialect: The SQL dialect instance
        code: The character code (integer)

    Returns:
        A FunctionCall instance representing the CHR function
    """
    code_expr = code if isinstance(code, BaseExpression) else Literal(dialect, code)
    return StringValueExpression(dialect, FunctionCall(dialect, "CHR", code_expr))


def ascii(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "IntegerValueExpression":
    """
    Creates an ASCII function call.

    SQL:2003 standard function returning the ASCII code of the first character.

    Usage rules:
    - To generate ASCII(column): ascii(dialect, Column(dialect, "char"))
    - To generate ASCII('A'): ascii(dialect, "A")  # Returns 65

    Args:
        dialect: The SQL dialect instance
        expr: The string expression

    Returns:
        A FunctionCall instance representing the ASCII function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return IntegerValueExpression(dialect, FunctionCall(dialect, "ASCII", target_expr))


def octet_length(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "IntegerValueExpression":
    """
    Creates an OCTET_LENGTH function call.

    SQL:2003 standard function returning the byte length of a string.

    Usage rules:
    - To generate OCTET_LENGTH(column): octet_length(dialect, Column(dialect, "text"))
    - To generate OCTET_LENGTH('hello'): octet_length(dialect, "hello")

    Args:
        dialect: The SQL dialect instance
        expr: The string expression

    Returns:
        A FunctionCall instance representing the OCTET_LENGTH function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return IntegerValueExpression(dialect, FunctionCall(dialect, "OCTET_LENGTH", target_expr))


def bit_length(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "IntegerValueExpression":
    """
    Creates a BIT_LENGTH function call.

    SQL:2003 standard function returning the bit length of a string.

    Usage rules:
    - To generate BIT_LENGTH(column): bit_length(dialect, Column(dialect, "text"))
    - To generate BIT_LENGTH('hello'): bit_length(dialect, "hello")

    Args:
        dialect: The SQL dialect instance
        expr: The string expression

    Returns:
        A FunctionCall instance representing the BIT_LENGTH function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return IntegerValueExpression(dialect, FunctionCall(dialect, "BIT_LENGTH", target_expr))


def position(
    dialect: "SQLDialectBase", substring: Union[str, "BaseExpression"], expr: Union[str, "BaseExpression"]
) -> "IntegerValueExpression":
    """
    Creates a POSITION function call.

    SQL:2003 standard function finding substring position (1-based).

    Usage rules:
    - To generate POSITION('abc' IN column): position(dialect, "abc", Column(dialect, "text"))
    - To generate POSITION('world' IN 'hello world'): position(dialect, "world", "hello world")

    Args:
        dialect: The SQL dialect instance
        substring: The substring to find
        expr: The string to search in

    Returns:
        A FunctionCall instance representing the POSITION function
    """
    substr_expr = substring if isinstance(substring, BaseExpression) else Literal(dialect, substring)
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return IntegerValueExpression(dialect, FunctionCall(dialect, "POSITION", substr_expr, target_expr))


def overlay(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    replacement: Union[str, "BaseExpression"],
    start: int,
    length: Optional[int] = None,
) -> "FunctionCall":
    """
    Creates an OVERLAY function call.

    SQL:2003 standard function replacing a substring.

    Usage rules:
    - To generate OVERLAY(column PLACING 'xxx' FROM 1): overlay(dialect, Column("text"), "xxx", 1)
    - To generate OVERLAY(column PLACING 'xx' FROM 1 FOR 2): overlay(dialect, Column("text"), "xx", 1, 2)

    Args:
        dialect: The SQL dialect instance
        expr: The source string
        replacement: The replacement string
        start: Starting position (1-based)
        length: Optional length to replace

    Returns:
        A FunctionCall instance representing the OVERLAY function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    replace_expr = replacement if isinstance(replacement, BaseExpression) else Literal(dialect, replacement)
    start_expr = Literal(dialect, start)
    if length is not None:
        length_expr = Literal(dialect, length)
        return StringValueExpression(
            dialect,
            FunctionCall(dialect, "OVERLAY", target_expr, replace_expr, start_expr, length_expr),
        )
    return StringValueExpression(
        dialect, FunctionCall(dialect, "OVERLAY", target_expr, replace_expr, start_expr)
    )


def translate(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], from_chars: str, to_chars: str
) -> "FunctionCall":
    """
    Creates a TRANSLATE function call.

    SQL:2003 standard function for character-by-character replacement.

    Usage rules:
    - To generate TRANSLATE(column, 'abc', 'xyz'): translate(dialect, Column("text"), "abc", "xyz")
    - To generate TRANSLATE('hello', 'el', 'ip'): translate(dialect, "hello", "el", "ip")

    Args:
        dialect: The SQL dialect instance
        expr: The source string
        from_chars: Characters to replace
        to_chars: Replacement characters

    Returns:
        A FunctionCall instance representing the TRANSLATE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    from_expr = Literal(dialect, from_chars)
    to_expr = Literal(dialect, to_chars)
    return StringValueExpression(dialect, FunctionCall(dialect, "TRANSLATE", target_expr, from_expr, to_expr))


def repeat(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], count: int) -> "RepeatExpression":
    """
    Creates a repetition node.

    Usage rules:
    - To generate REPEAT(column, 3): repeat(dialect, Column("text"), 3)
    - To generate REPEAT('ab', 5): repeat(dialect, "ab", 5)

    Args:
        dialect: The SQL dialect instance
        expr: The string to repeat
        count: Number of repetitions

    Returns:
        A :class:`~...expression.advanced_functions.RepeatExpression` node,
        rendered through ``format_repeat_expression`` -- a spelling where the
        function exists (PostgreSQL, MySQL, MariaDB, ClickHouse, BigQuery) and
        an emulation composed from ordinary nodes where it does not (SQLite,
        Oracle, Firebird).

    Contract:
        ``count >= 0`` repeats, and a negative count is the **empty string**
        rather than a refusal -- the native answer on PostgreSQL, MySQL,
        MariaDB and ClickHouse alike, measured 2026-10-09. SQL Server's
        ``REPLICATE`` answers NULL for a negative count and Oracle, Firebird
        and SQLite have no such function at all, so the meaning is settled
        once here instead of once per backend.
    """
    if isinstance(count, int) and count < 0:
        return StringValueExpression(dialect, Literal(dialect, ""))
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    count_expr = count if isinstance(count, BaseExpression) else Literal(dialect, count)
    from ..advanced_functions import RepeatExpression

    return RepeatExpression(dialect, target_expr, count_expr)


def space(dialect: "SQLDialectBase", count: int) -> "FunctionCall":
    """
    Creates a SPACE function call.

    SQL standard function generating spaces.

    Usage rules:
    - To generate SPACE(5): space(dialect, 5)  # Returns '     '

    Args:
        dialect: The SQL dialect instance
        count: Number of spaces

    Returns:
        A FunctionCall instance representing the SPACE function
    """
    return StringValueExpression(dialect, FunctionCall(dialect, "SPACE", Literal(dialect, count)))
