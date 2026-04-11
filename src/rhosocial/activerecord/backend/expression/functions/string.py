# src/rhosocial/activerecord/backend/expression/functions/string.py
"""String function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import Column, FunctionCall, Literal
from ..operators import BinaryExpression, RawSQLExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def concat(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "FunctionCall":
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
    return FunctionCall(dialect, "CONCAT", *target_exprs)


def coalesce(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "FunctionCall":
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
    return FunctionCall(dialect, "COALESCE", *target_exprs)


def length(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
    return FunctionCall(dialect, "LENGTH", target_expr)


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
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    start_expr = start if isinstance(start, BaseExpression) else Literal(dialect, start)
    if length is not None:
        length_expr = length if isinstance(length, BaseExpression) else Literal(dialect, length)
        return FunctionCall(dialect, "SUBSTRING", target_expr, start_expr, length_expr)
    return FunctionCall(dialect, "SUBSTRING", target_expr, start_expr)


def trim(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    chars: Optional[Union[str, "BaseExpression"]] = None,
    direction: str = "BOTH",
) -> "RawSQLExpression":
    """
    Creates a TRIM scalar function call.

    Usage rules:
    - To generate TRIM(BOTH FROM column), pass a Column object: trim(dialect, Column(dialect, "column_name"))
    - To generate TRIM(BOTH chars FROM ?), pass literal values: trim(dialect, "text", " ", "BOTH")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to trim. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        chars: Optional characters to trim. If provided, treated as literal value if string.
        direction: Direction of trim operation (BOTH, LEADING, TRAILING). Default is BOTH.

    Returns:
        A RawSQLExpression instance representing the TRIM function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    target_sql, target_params = target_expr.to_sql()

    if chars is not None:
        chars_expr = chars if isinstance(chars, BaseExpression) else Literal(dialect, chars)
        chars_sql, chars_params = chars_expr.to_sql()
        formatted_sql = f"TRIM({direction} {chars_sql} FROM {target_sql})"
        # Combine parameters
        all_params = target_params + chars_params
        # For now, return a RawSQLExpression; in a real implementation, the dialect would handle this
        return RawSQLExpression(dialect, formatted_sql, all_params)
    else:
        formatted_sql = f"TRIM({direction} FROM {target_sql})"
        return RawSQLExpression(dialect, formatted_sql, target_params)


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
    replacement_expr = (
        replacement if isinstance(replacement, BaseExpression) else Literal(dialect, replacement)
    )
    return FunctionCall(dialect, "REPLACE", target_expr, pattern_expr, replacement_expr)


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
    return FunctionCall(dialect, "UPPER", target_expr)


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
    return FunctionCall(dialect, "LOWER", target_expr)


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
    return FunctionCall(dialect, "INITCAP", target_expr)


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
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    n_expr = Literal(dialect, n)
    return FunctionCall(dialect, "LEFT", target_expr, n_expr)


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
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    n_expr = Literal(dialect, n)
    return FunctionCall(dialect, "RIGHT", target_expr, n_expr)


def lpad(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], length: int, pad: Optional[str] = None
) -> "FunctionCall":
    """
    Creates an LPAD scalar function call.

    Usage rules:
    - To generate LPAD(column, length, pad), pass a Column object:
      lpad(dialect, Column(dialect, "column_name"), 10, "0")
    - To generate LPAD(?, length, pad), pass a literal value: lpad(dialect, "text", 10, "0")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to pad. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        length: Total length after padding.
        pad: Optional padding character/string. If provided, treated as literal value.

    Returns:
        A FunctionCall instance representing the LPAD function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    length_expr = Literal(dialect, length)
    if pad is not None:
        pad_expr = Literal(dialect, pad)
        return FunctionCall(dialect, "LPAD", target_expr, length_expr, pad_expr)
    return FunctionCall(dialect, "LPAD", target_expr, length_expr)


def rpad(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], length: int, pad: Optional[str] = None
) -> "FunctionCall":
    """
    Creates an RPAD scalar function call.

    Usage rules:
    - To generate RPAD(column, length, pad), pass a Column object:
      rpad(dialect, Column(dialect, "column_name"), 10, " ")
    - To generate RPAD(?, length, pad), pass a literal value: rpad(dialect, "text", 10, " ")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to pad. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        length: Total length after padding.
        pad: Optional padding character/string. If provided, treated as literal value.

    Returns:
        A FunctionCall instance representing the RPAD function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    length_expr = Literal(dialect, length)
    if pad is not None:
        pad_expr = Literal(dialect, pad)
        return FunctionCall(dialect, "RPAD", target_expr, length_expr, pad_expr)
    return FunctionCall(dialect, "RPAD", target_expr, length_expr)


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
    return FunctionCall(dialect, "REVERSE", target_expr)


def strpos(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], substring: Union[str, "BaseExpression"]
) -> "FunctionCall":
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
    return FunctionCall(dialect, "STRPOS", target_expr, substr_expr)


def concat_op(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "BinaryExpression":
    """
    Creates a string concatenation operation using the || operator (SQL standard).

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
    result = BinaryExpression(dialect, "||", target_exprs[0], target_exprs[1])

    # Chain additional expressions using the || operator
    for i in range(2, len(target_exprs)):
        result = BinaryExpression(dialect, "||", result, target_exprs[i])

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
    return FunctionCall(dialect, "CHR", code_expr)


def ascii(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
    return FunctionCall(dialect, "ASCII", target_expr)


def octet_length(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
    return FunctionCall(dialect, "OCTET_LENGTH", target_expr)


def bit_length(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
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
    return FunctionCall(dialect, "BIT_LENGTH", target_expr)


def position(
    dialect: "SQLDialectBase", substring: Union[str, "BaseExpression"], expr: Union[str, "BaseExpression"]
) -> "FunctionCall":
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
    return FunctionCall(dialect, "POSITION", substr_expr, target_expr)


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
        return FunctionCall(dialect, "OVERLAY", target_expr, replace_expr, start_expr, length_expr)
    return FunctionCall(dialect, "OVERLAY", target_expr, replace_expr, start_expr)


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
    return FunctionCall(dialect, "TRANSLATE", target_expr, from_expr, to_expr)


def repeat(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], count: int) -> "FunctionCall":
    """
    Creates a REPEAT function call.

    SQL:2003 standard function repeating a string.

    Usage rules:
    - To generate REPEAT(column, 3): repeat(dialect, Column("text"), 3)
    - To generate REPEAT('ab', 5): repeat(dialect, "ab", 5)

    Args:
        dialect: The SQL dialect instance
        expr: The string to repeat
        count: Number of repetitions

    Returns:
        A FunctionCall instance representing the REPEAT function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    count_expr = Literal(dialect, count)
    return FunctionCall(dialect, "REPEAT", target_expr, count_expr)


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
    return FunctionCall(dialect, "SPACE", Literal(dialect, count))
