# src/rhosocial/activerecord/backend/expression/functions.py
"""
Standalone factory functions for creating SQL expression objects.

Usage Rules:
- For COUNT(*), pass "*" as a string: count(dialect, "*")
- For column references (e.g., COUNT(column), SUM(column)), pass Column objects: count(dialect, Column(dialect, "column_name"))
- For literal values (e.g., COUNT(?), SUM(?)), pass literal values as strings: count(dialect, "literal_value")
- For scalar functions (e.g., lower, upper), string arguments are treated as literal values by default
- For functions that operate on columns, wrap column names in Column objects
"""
from typing import Union, Optional, TYPE_CHECKING, List, Any

from . import bases
from . import aggregates
from . import core
from . import operators
from . import advanced_functions

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


# --- Aggregate Function Factories ---

def count(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"] = "*", is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """
    Creates a COUNT aggregate function call.

    Usage rules:
    - To generate COUNT(*), pass "*" as a string: count(dialect, "*")
    - To generate COUNT(column), pass a Column object: count(dialect, Column(dialect, "column_name"))
    - To generate COUNT(?), pass a literal value: count(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to count. Defaults to "*" to generate COUNT(*).
              If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the COUNT function
    """
    # 只检查是否传入的是字符串"*"
    if expr == '*' and isinstance(expr, str):
        target_expr = operators.RawSQLExpression(dialect, '*')
    else:
        target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "COUNT", target_expr, is_distinct=is_distinct, alias=alias)

def sum_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """
    Creates a SUM aggregate function call.

    Usage rules:
    - To generate SUM(column), pass a Column object: sum_(dialect, Column(dialect, "column_name"))
    - To generate SUM(?), pass a literal value: sum_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to sum. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the SUM function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "SUM", target_expr, is_distinct=is_distinct, alias=alias)

def avg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """
    Creates an AVG aggregate function call.

    Usage rules:
    - To generate AVG(column), pass a Column object: avg(dialect, Column(dialect, "column_name"))
    - To generate AVG(?), pass a literal value: avg(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to average. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the AVG function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "AVG", target_expr, is_distinct=is_distinct, alias=alias)

def min_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """
    Creates a MIN aggregate function call.

    Usage rules:
    - To generate MIN(column), pass a Column object: min_(dialect, Column(dialect, "column_name"))
    - To generate MIN(?), pass a literal value: min_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to find minimum of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the MIN function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "MIN", target_expr, alias=alias)

def max_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """
    Creates a MAX aggregate function call.

    Usage rules:
    - To generate MAX(column), pass a Column object: max_(dialect, Column(dialect, "column_name"))
    - To generate MAX(?), pass a literal value: max_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to find maximum of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the MAX function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "MAX", target_expr, alias=alias)



def concat(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    target_exprs = [e if isinstance(e, bases.BaseExpression) else core.Literal(dialect, e) for e in exprs]
    return core.FunctionCall(dialect, "CONCAT", *target_exprs)

def coalesce(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    target_exprs = [e if isinstance(e, bases.BaseExpression) else core.Literal(dialect, e) for e in exprs]
    return core.FunctionCall(dialect, "COALESCE", *target_exprs)


# --- String Function Factories ---

def length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "LENGTH", target_expr)

def substring(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
              start: Union[int, "bases.BaseExpression"],
              length: Optional[Union[int, "bases.BaseExpression"]] = None) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    start_expr = start if isinstance(start, bases.BaseExpression) else core.Literal(dialect, start)
    if length is not None:
        length_expr = length if isinstance(length, bases.BaseExpression) else core.Literal(dialect, length)
        return core.FunctionCall(dialect, "SUBSTRING", target_expr, start_expr, length_expr)
    return core.FunctionCall(dialect, "SUBSTRING", target_expr, start_expr)

def trim(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         chars: Optional[Union[str, "bases.BaseExpression"]] = None,
         direction: str = "BOTH") -> "operators.RawSQLExpression":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    target_sql, target_params = target_expr.to_sql()

    if chars is not None:
        chars_expr = chars if isinstance(chars, bases.BaseExpression) else core.Literal(dialect, chars)
        chars_sql, chars_params = chars_expr.to_sql()
        formatted_sql = f"TRIM({direction} {chars_sql} FROM {target_sql})"
        # Combine parameters
        all_params = target_params + chars_params
        # For now, return a RawSQLExpression; in a real implementation, the dialect would handle this
        return operators.RawSQLExpression(dialect, formatted_sql)
    else:
        formatted_sql = f"TRIM({direction} FROM {target_sql})"
        return operators.RawSQLExpression(dialect, formatted_sql)

def replace(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
            pattern: Union[str, "bases.BaseExpression"],
            replacement: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    pattern_expr = pattern if isinstance(pattern, bases.BaseExpression) else core.Literal(dialect, pattern)
    replacement_expr = replacement if isinstance(replacement, bases.BaseExpression) else core.Literal(dialect, replacement)
    return core.FunctionCall(dialect, "REPLACE", target_expr, pattern_expr, replacement_expr)

def upper(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "UPPER", target_expr)

def lower(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "LOWER", target_expr)

def initcap(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "INITCAP", target_expr)

def left(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    n_expr = core.Literal(dialect, n)
    return core.FunctionCall(dialect, "LEFT", target_expr, n_expr)

def right(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    n_expr = core.Literal(dialect, n)
    return core.FunctionCall(dialect, "RIGHT", target_expr, n_expr)

def lpad(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         length: int, pad: Optional[str] = None) -> "core.FunctionCall":
    """
    Creates an LPAD scalar function call.

    Usage rules:
    - To generate LPAD(column, length, pad), pass a Column object: lpad(dialect, Column(dialect, "column_name"), 10, "0")
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    length_expr = core.Literal(dialect, length)
    if pad is not None:
        pad_expr = core.Literal(dialect, pad)
        return core.FunctionCall(dialect, "LPAD", target_expr, length_expr, pad_expr)
    return core.FunctionCall(dialect, "LPAD", target_expr, length_expr)

def rpad(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         length: int, pad: Optional[str] = None) -> "core.FunctionCall":
    """
    Creates an RPAD scalar function call.

    Usage rules:
    - To generate RPAD(column, length, pad), pass a Column object: rpad(dialect, Column(dialect, "column_name"), 10, " ")
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    length_expr = core.Literal(dialect, length)
    if pad is not None:
        pad_expr = core.Literal(dialect, pad)
        return core.FunctionCall(dialect, "RPAD", target_expr, length_expr, pad_expr)
    return core.FunctionCall(dialect, "RPAD", target_expr, length_expr)

def reverse(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
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
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "REVERSE", target_expr)

def strpos(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
           substring: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a STRPOS scalar function call (position of substring).

    Usage rules:
    - To generate STRPOS(column, substring), pass Column objects: strpos(dialect, Column(dialect, "column_name"), "substr")
    - To generate STRPOS(?, ?), pass literal values: strpos(dialect, "text", "substr")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to search in. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        substring: Substring to find. If a string is passed, it's treated as a literal value.

    Returns:
        A FunctionCall instance representing the STRPOS function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    substr_expr = substring if isinstance(substring, bases.BaseExpression) else core.Literal(dialect, substring)
    return core.FunctionCall(dialect, "STRPOS", target_expr, substr_expr)


# --- Math Function Factories ---

def abs_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates an ABS scalar function call.

    Usage rules:
    - To generate ABS(column), pass a Column object: abs_(dialect, Column(dialect, "column_name"))
    - To generate ABS(?), pass a numeric value: abs_(dialect, -5)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get absolute value of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the ABS function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "ABS", target_expr)

def round_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
           decimals: Optional[int] = None) -> "core.FunctionCall":
    """
    Creates a ROUND scalar function call.

    Usage rules:
    - To generate ROUND(column), pass a Column object: round_(dialect, Column(dialect, "column_name"))
    - To generate ROUND(?, decimals), pass a numeric value: round_(dialect, 3.14159, 2)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to round. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        decimals: Optional number of decimal places to round to. If provided, treated as literal value.

    Returns:
        A FunctionCall instance representing the ROUND function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    if decimals is not None:
        decimals_expr = core.Literal(dialect, decimals)
        return core.FunctionCall(dialect, "ROUND", target_expr, decimals_expr)
    return core.FunctionCall(dialect, "ROUND", target_expr)

def ceil(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a CEIL scalar function call.

    Usage rules:
    - To generate CEIL(column), pass a Column object: ceil(dialect, Column(dialect, "column_name"))
    - To generate CEIL(?), pass a numeric value: ceil(dialect, 3.14)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get ceiling of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the CEIL function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "CEIL", target_expr)

def floor(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a FLOOR scalar function call.

    Usage rules:
    - To generate FLOOR(column), pass a Column object: floor(dialect, Column(dialect, "column_name"))
    - To generate FLOOR(?), pass a numeric value: floor(dialect, 3.99)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get floor of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the FLOOR function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "FLOOR", target_expr)

def sqrt(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a SQRT scalar function call.

    Usage rules:
    - To generate SQRT(column), pass a Column object: sqrt(dialect, Column(dialect, "column_name"))
    - To generate SQRT(?), pass a numeric value: sqrt(dialect, 16)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get square root of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the SQRT function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "SQRT", target_expr)

def power(dialect: "SQLDialectBase", base: Union[str, "bases.BaseExpression"],
          exponent: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a POWER scalar function call.

    Usage rules:
    - To generate POWER(column, exp), pass Column objects: power(dialect, Column(dialect, "base_col"), Column(dialect, "exp_col"))
    - To generate POWER(?, ?), pass numeric values: power(dialect, 2, 3)

    Args:
        dialect: The SQL dialect instance
        base: The base value. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        exponent: The exponent value. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the POWER function
    """
    base_expr = base if isinstance(base, bases.BaseExpression) else (core.Literal(dialect, base) if isinstance(base, (int, float)) else core.Column(dialect, base))
    exp_expr = exponent if isinstance(exponent, bases.BaseExpression) else (core.Literal(dialect, exponent) if isinstance(exponent, (int, float)) else core.Column(dialect, exponent))
    return core.FunctionCall(dialect, "POWER", base_expr, exp_expr)

def exp(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates an EXP scalar function call.

    Usage rules:
    - To generate EXP(column), pass a Column object: exp(dialect, Column(dialect, "column_name"))
    - To generate EXP(?), pass a numeric value: exp(dialect, 1)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get exponential of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the EXP function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "EXP", target_expr)

def log(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
        base: Optional[Union[str, "bases.BaseExpression"]] = None) -> "core.FunctionCall":
    """
    Creates a LOG scalar function call.

    Usage rules:
    - To generate LOG(column), pass a Column object: log(dialect, Column(dialect, "column_name"))
    - To generate LOG(?, base), pass numeric values: log(dialect, 100, 10)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get logarithm of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        base: Optional base for the logarithm. If provided, treated as a literal value if numeric.

    Returns:
        A FunctionCall instance representing the LOG function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    if base is not None:
        base_expr = base if isinstance(base, bases.BaseExpression) else (core.Literal(dialect, base) if isinstance(base, (int, float)) else core.Column(dialect, base))
        return core.FunctionCall(dialect, "LOG", target_expr, base_expr)
    return core.FunctionCall(dialect, "LOG", target_expr)

def sin(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a SIN scalar function call.

    Usage rules:
    - To generate SIN(column), pass a Column object: sin(dialect, Column(dialect, "column_name"))
    - To generate SIN(?), pass a numeric value: sin(dialect, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get sine of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the SIN function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "SIN", target_expr)

def cos(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a COS scalar function call.

    Usage rules:
    - To generate COS(column), pass a Column object: cos(dialect, Column(dialect, "column_name"))
    - To generate COS(?), pass a numeric value: cos(dialect, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get cosine of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the COS function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "COS", target_expr)

def tan(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a TAN scalar function call.

    Usage rules:
    - To generate TAN(column), pass a Column object: tan(dialect, Column(dialect, "column_name"))
    - To generate TAN(?), pass a numeric value: tan(dialect, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get tangent of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the TAN function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "TAN", target_expr)


# --- Date/Time Function Factories ---

def now(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """
    Creates a NOW scalar function call.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the NOW function
    """
    return core.FunctionCall(dialect, "NOW")

def current_date(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """
    Creates a CURRENT_DATE scalar function call.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the CURRENT_DATE function
    """
    return core.FunctionCall(dialect, "CURRENT_DATE")

def current_time(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """
    Creates a CURRENT_TIME scalar function call.

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the CURRENT_TIME function
    """
    return core.FunctionCall(dialect, "CURRENT_TIME")

def year(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a YEAR scalar function call.

    Usage rules:
    - To generate YEAR(column), pass a Column object: year(dialect, Column(dialect, "column_name"))
    - To generate YEAR(?), pass a numeric value: year(dialect, 2023)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract year from. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the YEAR function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "YEAR", target_expr)

def month(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a MONTH scalar function call.

    Usage rules:
    - To generate MONTH(column), pass a Column object: month(dialect, Column(dialect, "column_name"))
    - To generate MONTH(?), pass a numeric value: month(dialect, 12)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract month from. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the MONTH function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "MONTH", target_expr)

def day(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a DAY scalar function call.

    Usage rules:
    - To generate DAY(column), pass a Column object: day(dialect, Column(dialect, "column_name"))
    - To generate DAY(?), pass a numeric value: day(dialect, 25)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract day from. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the DAY function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "DAY", target_expr)

def hour(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates an HOUR scalar function call.

    Usage rules:
    - To generate HOUR(column), pass a Column object: hour(dialect, Column(dialect, "column_name"))
    - To generate HOUR(?), pass a numeric value: hour(dialect, 14)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract hour from. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the HOUR function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "HOUR", target_expr)

def minute(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a MINUTE scalar function call.

    Usage rules:
    - To generate MINUTE(column), pass a Column object: minute(dialect, Column(dialect, "column_name"))
    - To generate MINUTE(?), pass a numeric value: minute(dialect, 30)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract minute from. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the MINUTE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "MINUTE", target_expr)

def second(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a SECOND scalar function call.

    Usage rules:
    - To generate SECOND(column), pass a Column object: second(dialect, Column(dialect, "column_name"))
    - To generate SECOND(?), pass a numeric value: second(dialect, 45)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract second from. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the SECOND function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "SECOND", target_expr)

def date_part(dialect: "SQLDialectBase", field: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a DATE_PART scalar function call.

    Usage rules:
    - To generate DATE_PART(field, column), pass a Column object: date_part(dialect, "year", Column(dialect, "date_col"))
    - To generate DATE_PART(field, ?), pass a literal value: date_part(dialect, "month", "2023-01-01")

    Args:
        dialect: The SQL dialect instance
        field: The date part field (e.g., "year", "month", "day", "hour", "minute", "second")
        expr: The expression to extract date part from. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the DATE_PART function
    """
    field_expr = core.Literal(dialect, field)
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "DATE_PART", field_expr, target_expr)

def date_trunc(dialect: "SQLDialectBase", field: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a DATE_TRUNC scalar function call.

    Usage rules:
    - To generate DATE_TRUNC(field, column), pass a Column object: date_trunc(dialect, "month", Column(dialect, "date_col"))
    - To generate DATE_TRUNC(field, ?), pass a literal value: date_trunc(dialect, "day", "2023-01-01 14:30:00")

    Args:
        dialect: The SQL dialect instance
        field: The date part field to truncate to (e.g., "year", "month", "day", "hour", "minute")
        expr: The expression to truncate. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the DATE_TRUNC function
    """
    field_expr = core.Literal(dialect, field)
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "DATE_TRUNC", field_expr, target_expr)


# --- Conditional Function Factories ---

def case(dialect: "SQLDialectBase",
         value: Optional["bases.BaseExpression"] = None,
         alias: Optional[str] = None) -> "advanced_functions.CaseExpression":
    """
    Creates a CASE expression.

    Args:
        dialect: The SQL dialect instance
        value: Optional value to compare against in searched CASE. If provided, used as the base expression.
        alias: Optional alias for the result.

    Returns:
        A CaseExpression instance representing the CASE expression
    """
    return advanced_functions.CaseExpression(dialect, value=value, alias=alias)

def nullif(dialect: "SQLDialectBase", value: Union[str, "bases.BaseExpression"],
           null_value: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a NULLIF scalar function call.

    Usage rules:
    - To generate NULLIF(column, null_val), pass Column objects: nullif(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate NULLIF(?, ?), pass literal values: nullif(dialect, "value", "null_value")

    Args:
        dialect: The SQL dialect instance
        value: The value to compare. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        null_value: The value to compare against. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the NULLIF function
    """
    value_expr = value if isinstance(value, bases.BaseExpression) else core.Literal(dialect, value)
    null_expr = null_value if isinstance(null_value, bases.BaseExpression) else core.Literal(dialect, null_value)
    return core.FunctionCall(dialect, "NULLIF", value_expr, null_expr)

def greatest(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a GREATEST scalar function call.

    Usage rules:
    - To generate GREATEST(column1, column2, ...), pass Column objects: greatest(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate GREATEST(?, ?, ...), pass literal values: greatest(dialect, "val1", "val2", "val3")

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to compare. If strings are passed, they're treated as literal values.
                If BaseExpressions are passed, they're used as-is.

    Returns:
        A FunctionCall instance representing the GREATEST function
    """
    target_exprs = [e if isinstance(e, bases.BaseExpression) else core.Literal(dialect, e) for e in exprs]
    return core.FunctionCall(dialect, "GREATEST", *target_exprs)

def least(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a LEAST scalar function call.

    Usage rules:
    - To generate LEAST(column1, column2, ...), pass Column objects: least(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate LEAST(?, ?, ...), pass literal values: least(dialect, "val1", "val2", "val3")

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to compare. If strings are passed, they're treated as literal values.
                If BaseExpressions are passed, they're used as-is.

    Returns:
        A FunctionCall instance representing the LEAST function
    """
    target_exprs = [e if isinstance(e, bases.BaseExpression) else core.Literal(dialect, e) for e in exprs]
    return core.FunctionCall(dialect, "LEAST", *target_exprs)


# --- Window Function Factories ---

def row_number(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """Creates a ROW_NUMBER window function call."""
    return advanced_functions.WindowFunctionCall(dialect, "ROW_NUMBER", alias=alias)

def rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """Creates a RANK window function call."""
    return advanced_functions.WindowFunctionCall(dialect, "RANK", alias=alias)

def dense_rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """Creates a DENSE_RANK window function call."""
    return advanced_functions.WindowFunctionCall(dialect, "DENSE_RANK", alias=alias)

def lag(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
        offset: int = 1, default: Optional[Any] = None,
        alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """
    Creates a LAG window function call.

    Usage rules:
    - To generate LAG(column, offset, default), pass a Column object: lag(dialect, Column(dialect, "column_name"), 1, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to lag. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        offset: Number of rows to look back. Default is 1.
        default: Default value if lag goes beyond the partition. Optional.
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the LAG function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    args = [target_expr, core.Literal(dialect, offset)]
    if default is not None:
        args.append(core.Literal(dialect, default))
    return advanced_functions.WindowFunctionCall(dialect, "LAG", args=args, alias=alias)

def lead(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         offset: int = 1, default: Optional[Any] = None,
         alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """
    Creates a LEAD window function call.

    Usage rules:
    - To generate LEAD(column, offset, default), pass a Column object: lead(dialect, Column(dialect, "column_name"), 1, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to lead. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        offset: Number of rows to look ahead. Default is 1.
        default: Default value if lead goes beyond the partition. Optional.
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the LEAD function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    args = [target_expr, core.Literal(dialect, offset)]
    if default is not None:
        args.append(core.Literal(dialect, default))
    return advanced_functions.WindowFunctionCall(dialect, "LEAD", args=args, alias=alias)

def first_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
                alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """
    Creates a FIRST_VALUE window function call.

    Usage rules:
    - To generate FIRST_VALUE(column), pass a Column object: first_value(dialect, Column(dialect, "column_name"))

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get first value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the FIRST_VALUE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return advanced_functions.WindowFunctionCall(dialect, "FIRST_VALUE", args=[target_expr], alias=alias)

def last_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
               alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """
    Creates a LAST_VALUE window function call.

    Usage rules:
    - To generate LAST_VALUE(column), pass a Column object: last_value(dialect, Column(dialect, "column_name"))

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get last value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the LAST_VALUE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return advanced_functions.WindowFunctionCall(dialect, "LAST_VALUE", args=[target_expr], alias=alias)

def nth_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
              n: int, alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """
    Creates an NTH_VALUE window function call.

    Usage rules:
    - To generate NTH_VALUE(column, n), pass a Column object: nth_value(dialect, Column(dialect, "column_name"), 2)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get nth value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        n: Position of the value to retrieve (1-indexed).
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the NTH_VALUE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    n_expr = core.Literal(dialect, n)
    return advanced_functions.WindowFunctionCall(dialect, "NTH_VALUE", args=[target_expr, n_expr], alias=alias)


# --- JSON Function Factories ---

def json_extract(dialect: "SQLDialectBase", column: Union[str, "bases.BaseExpression"],
                 path: str) -> "advanced_functions.JSONExpression":
    """
    Creates a JSON extract operation (e.g., column->path).

    Usage rules:
    - To generate column->path, pass a Column object: json_extract(dialect, Column(dialect, "json_col"), "$.field")

    Args:
        dialect: The SQL dialect instance
        column: The JSON column to extract from. If a string is passed, it's treated as a column name.
                If a BaseExpression is passed, it's used as-is.
        path: The JSON path to extract.

    Returns:
        A JSONExpression instance representing the JSON extract operation
    """
    target_column = column if isinstance(column, bases.BaseExpression) else core.Column(dialect, column)
    return advanced_functions.JSONExpression(dialect, target_column, path, operation="->")

def json_extract_text(dialect: "SQLDialectBase", column: Union[str, "bases.BaseExpression"],
                      path: str) -> "advanced_functions.JSONExpression":
    """
    Creates a JSON extract text operation (e.g., column->>path).

    Usage rules:
    - To generate column->>path, pass a Column object: json_extract_text(dialect, Column(dialect, "json_col"), "$.field")

    Args:
        dialect: The SQL dialect instance
        column: The JSON column to extract from. If a string is passed, it's treated as a column name.
                If a BaseExpression is passed, it's used as-is.
        path: The JSON path to extract as text.

    Returns:
        A JSONExpression instance representing the JSON extract text operation
    """
    target_column = column if isinstance(column, bases.BaseExpression) else core.Column(dialect, column)
    return advanced_functions.JSONExpression(dialect, target_column, path, operation="->>")

def json_build_object(dialect: "SQLDialectBase", *key_value_pairs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a JSON_BUILD_OBJECT function call.

    Usage rules:
    - To generate JSON_BUILD_OBJECT(key1, val1, key2, val2, ...), pass expressions:
      json_build_object(dialect, "key1", Column(dialect, "col1"), "key2", Column(dialect, "col2"))

    Args:
        dialect: The SQL dialect instance
        *key_value_pairs: Alternating sequence of key-value expressions. Keys and values can be strings (literal) or BaseExpression.

    Returns:
        A FunctionCall instance representing the JSON_BUILD_OBJECT function
    """
    # Expect alternating sequence of key-value expressions
    processed_args = []
    for arg in key_value_pairs:
        processed_args.append(arg if isinstance(arg, bases.BaseExpression) else core.Literal(dialect, arg))
    return core.FunctionCall(dialect, "JSON_BUILD_OBJECT", *processed_args)

def json_array_elements(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """
    Creates a JSON_ARRAY_ELEMENTS function call.

    Usage rules:
    - To generate JSON_ARRAY_ELEMENTS(column), pass a Column object: json_array_elements(dialect, Column(dialect, "json_array"))

    Args:
        dialect: The SQL dialect instance
        expr: The JSON array expression. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the JSON_ARRAY_ELEMENTS function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "JSON_ARRAY_ELEMENTS", target_expr)

def json_objectagg(dialect: "SQLDialectBase", key_expr: Union[str, "bases.BaseExpression"],
                   value_expr: Union[str, "bases.BaseExpression"]) -> "aggregates.AggregateFunctionCall":
    """Creates a JSON_OBJECTAGG aggregate function call."""
    key_target = key_expr if isinstance(key_expr, bases.BaseExpression) else core.Column(dialect, key_expr)
    value_target = value_expr if isinstance(value_expr, bases.BaseExpression) else core.Column(dialect, value_expr)
    return aggregates.AggregateFunctionCall(dialect, "JSON_OBJECTAGG", key_target, value_target)

def json_arrayagg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
                  is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """Creates a JSON_ARRAYAGG aggregate function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "JSON_ARRAYAGG", target_expr, is_distinct=is_distinct, alias=alias)


# --- Array Function Factories ---

def array_agg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
              is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """Creates an ARRAY_AGG aggregate function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "ARRAY_AGG", target_expr, is_distinct=is_distinct, alias=alias)

def unnest(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates an UNNEST function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "UNNEST", target_expr)

def array_length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
                 dimension: int = 1) -> "core.FunctionCall":
    """Creates an ARRAY_LENGTH function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    dimension_expr = core.Literal(dialect, dimension)
    return core.FunctionCall(dialect, "ARRAY_LENGTH", target_expr, dimension_expr)


# --- Type Conversion Function Factories ---

def cast(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         target_type: str) -> "advanced_functions.CastExpression":
    """
    Creates a CAST expression.

    Usage rules:
    - To generate CAST(column AS type), pass a Column object: cast(dialect, Column(dialect, "column_name"), "INTEGER")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to cast. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        target_type: The target data type to cast to.

    Returns:
        A CastExpression instance representing the CAST operation
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return advanced_functions.CastExpression(dialect, target_expr, target_type)

def to_char(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
            format: Optional[str] = None) -> "core.FunctionCall":
    """
    Creates a TO_CHAR function call.

    Usage rules:
    - To generate TO_CHAR(column), pass a Column object: to_char(dialect, Column(dialect, "date_col"))
    - To generate TO_CHAR(column, format), pass a format string: to_char(dialect, Column(dialect, "date_col"), "YYYY-MM-DD")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to character. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_CHAR function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    if format is not None:
        format_expr = core.Literal(dialect, format)
        return core.FunctionCall(dialect, "TO_CHAR", target_expr, format_expr)
    return core.FunctionCall(dialect, "TO_CHAR", target_expr)

def to_number(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
              format: Optional[str] = None) -> "core.FunctionCall":
    """
    Creates a TO_NUMBER function call.

    Usage rules:
    - To generate TO_NUMBER(column), pass a Column object: to_number(dialect, Column(dialect, "char_col"))
    - To generate TO_NUMBER(column, format), pass a format string: to_number(dialect, Column(dialect, "char_col"), "9999")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to number. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_NUMBER function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    if format is not None:
        format_expr = core.Literal(dialect, format)
        return core.FunctionCall(dialect, "TO_NUMBER", target_expr, format_expr)
    return core.FunctionCall(dialect, "TO_NUMBER", target_expr)

def to_date(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
            format: Optional[str] = None) -> "core.FunctionCall":
    """
    Creates a TO_DATE function call.

    Usage rules:
    - To generate TO_DATE(column), pass a Column object: to_date(dialect, Column(dialect, "char_col"))
    - To generate TO_DATE(column, format), pass a format string: to_date(dialect, Column(dialect, "char_col"), "YYYY-MM-DD")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to date. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_DATE function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    if format is not None:
        format_expr = core.Literal(dialect, format)
        return core.FunctionCall(dialect, "TO_DATE", target_expr, format_expr)
    return core.FunctionCall(dialect, "TO_DATE", target_expr)


# --- Grouping Function Factories ---

def grouping_sets(dialect: "SQLDialectBase", *grouping_lists: List[Union[str, "bases.BaseExpression"]]) -> "query_parts.GroupingExpression":
    """
    Creates a GROUPING SETS expression for use in GROUP BY clauses.

    Usage rules:
    - To generate GROUPING SETS((col1, col2), (col3)), pass column lists:
      grouping_sets(dialect, ["col1", "col2"], ["col3"])

    Args:
        dialect: The SQL dialect instance
        *grouping_lists: Variable number of lists, each containing expressions to group by

    Returns:
        A GroupingExpression instance representing the GROUPING SETS operation
    """
    from . import query_parts
    processed_lists = []
    for grouping_list in grouping_lists:
        processed_exprs = [expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr) for expr in grouping_list]
        processed_lists.append(processed_exprs)
    return query_parts.GroupingExpression(dialect, "GROUPING SETS", processed_lists)

def rollup(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "query_parts.GroupingExpression":
    """
    Creates a ROLLUP expression for use in GROUP BY clauses.

    Usage rules:
    - To generate ROLLUP(col1, col2), pass expressions:
      rollup(dialect, "col1", "col2") or rollup(dialect, Column(dialect, "col1"), Column(dialect, "col2"))

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to include in the ROLLUP

    Returns:
        A GroupingExpression instance representing the ROLLUP operation
    """
    from . import query_parts
    processed_exprs = [expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr) for expr in exprs]
    return query_parts.GroupingExpression(dialect, "ROLLUP", processed_exprs)

def cube(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "query_parts.GroupingExpression":
    """
    Creates a CUBE expression for use in GROUP BY clauses.

    Usage rules:
    - To generate CUBE(col1, col2), pass expressions:
      cube(dialect, "col1", "col2") or cube(dialect, Column(dialect, "col1"), Column(dialect, "col2"))

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to include in the CUBE

    Returns:
        A GroupingExpression instance representing the CUBE operation
    """
    from . import query_parts
    processed_exprs = [expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr) for expr in exprs]
    return query_parts.GroupingExpression(dialect, "CUBE", processed_exprs)
