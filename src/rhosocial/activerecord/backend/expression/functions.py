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

# if TYPE_CHECKING:
#     from ..dialect import SQLDialectBase


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


# --- Scalar Function Factories ---

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
    """Creates a LENGTH scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "LENGTH", target_expr)

def substring(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
              start: Union[int, "bases.BaseExpression"],
              length: Optional[Union[int, "bases.BaseExpression"]] = None) -> "core.FunctionCall":
    """Creates a SUBSTRING scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    start_expr = start if isinstance(start, bases.BaseExpression) else core.Literal(dialect, start)
    if length is not None:
        length_expr = length if isinstance(length, bases.BaseExpression) else core.Literal(dialect, length)
        return core.FunctionCall(dialect, "SUBSTRING", target_expr, start_expr, length_expr)
    return core.FunctionCall(dialect, "SUBSTRING", target_expr, start_expr)

def trim(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         chars: Optional[Union[str, "bases.BaseExpression"]] = None,
         direction: str = "BOTH") -> "operators.RawSQLExpression":
    """Creates a TRIM scalar function call."""
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
    """Creates a REPLACE scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    pattern_expr = pattern if isinstance(pattern, bases.BaseExpression) else core.Literal(dialect, pattern)
    replacement_expr = replacement if isinstance(replacement, bases.BaseExpression) else core.Literal(dialect, replacement)
    return core.FunctionCall(dialect, "REPLACE", target_expr, pattern_expr, replacement_expr)

def upper(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates an UPPER scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "UPPER", target_expr)

def lower(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a LOWER scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "LOWER", target_expr)

def initcap(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates an INITCAP scalar function call (title case)."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "INITCAP", target_expr)

def left(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int) -> "core.FunctionCall":
    """Creates a LEFT scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    n_expr = core.Literal(dialect, n)
    return core.FunctionCall(dialect, "LEFT", target_expr, n_expr)

def right(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int) -> "core.FunctionCall":
    """Creates a RIGHT scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    n_expr = core.Literal(dialect, n)
    return core.FunctionCall(dialect, "RIGHT", target_expr, n_expr)

def lpad(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         length: int, pad: Optional[str] = None) -> "core.FunctionCall":
    """Creates an LPAD scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    length_expr = core.Literal(dialect, length)
    if pad is not None:
        pad_expr = core.Literal(dialect, pad)
        return core.FunctionCall(dialect, "LPAD", target_expr, length_expr, pad_expr)
    return core.FunctionCall(dialect, "LPAD", target_expr, length_expr)

def rpad(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         length: int, pad: Optional[str] = None) -> "core.FunctionCall":
    """Creates an RPAD scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    length_expr = core.Literal(dialect, length)
    if pad is not None:
        pad_expr = core.Literal(dialect, pad)
        return core.FunctionCall(dialect, "RPAD", target_expr, length_expr, pad_expr)
    return core.FunctionCall(dialect, "RPAD", target_expr, length_expr)

def reverse(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a REVERSE scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    return core.FunctionCall(dialect, "REVERSE", target_expr)

def strpos(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
           substring: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a STRPOS scalar function call (position of substring)."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Literal(dialect, expr)
    substr_expr = substring if isinstance(substring, bases.BaseExpression) else core.Literal(dialect, substring)
    return core.FunctionCall(dialect, "STRPOS", target_expr, substr_expr)


# --- Math Function Factories ---

def abs_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates an ABS scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "ABS", target_expr)

def round_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
           decimals: Optional[int] = None) -> "core.FunctionCall":
    """Creates a ROUND scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    if decimals is not None:
        decimals_expr = core.Literal(dialect, decimals)
        return core.FunctionCall(dialect, "ROUND", target_expr, decimals_expr)
    return core.FunctionCall(dialect, "ROUND", target_expr)

def ceil(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a CEIL scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "CEIL", target_expr)

def floor(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a FLOOR scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "FLOOR", target_expr)

def sqrt(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a SQRT scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "SQRT", target_expr)

def power(dialect: "SQLDialectBase", base: Union[str, "bases.BaseExpression"],
          exponent: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a POWER scalar function call."""
    base_expr = base if isinstance(base, bases.BaseExpression) else (core.Literal(dialect, base) if isinstance(base, (int, float)) else core.Column(dialect, base))
    exp_expr = exponent if isinstance(exponent, bases.BaseExpression) else (core.Literal(dialect, exponent) if isinstance(exponent, (int, float)) else core.Column(dialect, exponent))
    return core.FunctionCall(dialect, "POWER", base_expr, exp_expr)

def exp(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates an EXP scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "EXP", target_expr)

def log(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
        base: Optional[Union[str, "bases.BaseExpression"]] = None) -> "core.FunctionCall":
    """Creates a LOG scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    if base is not None:
        base_expr = base if isinstance(base, bases.BaseExpression) else (core.Literal(dialect, base) if isinstance(base, (int, float)) else core.Column(dialect, base))
        return core.FunctionCall(dialect, "LOG", target_expr, base_expr)
    return core.FunctionCall(dialect, "LOG", target_expr)

def sin(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a SIN scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "SIN", target_expr)

def cos(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a COS scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "COS", target_expr)

def tan(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a TAN scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "TAN", target_expr)


# --- Date/Time Function Factories ---

def now(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """Creates a NOW scalar function call."""
    return core.FunctionCall(dialect, "NOW")

def current_date(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """Creates a CURRENT_DATE scalar function call."""
    return core.FunctionCall(dialect, "CURRENT_DATE")

def current_time(dialect: "SQLDialectBase") -> "core.FunctionCall":
    """Creates a CURRENT_TIME scalar function call."""
    return core.FunctionCall(dialect, "CURRENT_TIME")

def year(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a YEAR scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "YEAR", target_expr)

def month(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a MONTH scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "MONTH", target_expr)

def day(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a DAY scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "DAY", target_expr)

def hour(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates an HOUR scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "HOUR", target_expr)

def minute(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a MINUTE scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "MINUTE", target_expr)

def second(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a SECOND scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else (core.Literal(dialect, expr) if isinstance(expr, (int, float)) else core.Column(dialect, expr))
    return core.FunctionCall(dialect, "SECOND", target_expr)

def date_part(dialect: "SQLDialectBase", field: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a DATE_PART scalar function call."""
    field_expr = core.Literal(dialect, field)
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "DATE_PART", field_expr, target_expr)

def date_trunc(dialect: "SQLDialectBase", field: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a DATE_TRUNC scalar function call."""
    field_expr = core.Literal(dialect, field)
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "DATE_TRUNC", field_expr, target_expr)


# --- Conditional Function Factories ---

def case(dialect: "SQLDialectBase",
         value: Optional["bases.BaseExpression"] = None,
         alias: Optional[str] = None) -> "advanced_functions.CaseExpression":
    """Creates a CASE expression."""
    return advanced_functions.CaseExpression(dialect, value=value, alias=alias)

def nullif(dialect: "SQLDialectBase", value: Union[str, "bases.BaseExpression"],
           null_value: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a NULLIF scalar function call."""
    value_expr = value if isinstance(value, bases.BaseExpression) else core.Literal(dialect, value)
    null_expr = null_value if isinstance(null_value, bases.BaseExpression) else core.Literal(dialect, null_value)
    return core.FunctionCall(dialect, "NULLIF", value_expr, null_expr)

def greatest(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a GREATEST scalar function call."""
    target_exprs = [e if isinstance(e, bases.BaseExpression) else core.Literal(dialect, e) for e in exprs]
    return core.FunctionCall(dialect, "GREATEST", *target_exprs)

def least(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a LEAST scalar function call."""
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
    """Creates a LAG window function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    args = [target_expr, core.Literal(dialect, offset)]
    if default is not None:
        args.append(core.Literal(dialect, default))
    return advanced_functions.WindowFunctionCall(dialect, "LAG", args=args, alias=alias)

def lead(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
         offset: int = 1, default: Optional[Any] = None,
         alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """Creates a LEAD window function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    args = [target_expr, core.Literal(dialect, offset)]
    if default is not None:
        args.append(core.Literal(dialect, default))
    return advanced_functions.WindowFunctionCall(dialect, "LEAD", args=args, alias=alias)

def first_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
                alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """Creates a FIRST_VALUE window function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return advanced_functions.WindowFunctionCall(dialect, "FIRST_VALUE", args=[target_expr], alias=alias)

def last_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
               alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """Creates a LAST_VALUE window function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return advanced_functions.WindowFunctionCall(dialect, "LAST_VALUE", args=[target_expr], alias=alias)

def nth_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
              n: int, alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall":
    """Creates an NTH_VALUE window function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    n_expr = core.Literal(dialect, n)
    return advanced_functions.WindowFunctionCall(dialect, "NTH_VALUE", args=[target_expr, n_expr], alias=alias)


# --- JSON Function Factories ---

def json_extract(dialect: "SQLDialectBase", column: Union[str, "bases.BaseExpression"],
                 path: str) -> "advanced_functions.JSONExpression":
    """Creates a JSON extract operation (e.g., column->path)."""
    target_column = column if isinstance(column, bases.BaseExpression) else core.Column(dialect, column)
    return advanced_functions.JSONExpression(dialect, target_column, path, operation="->")

def json_extract_text(dialect: "SQLDialectBase", column: Union[str, "bases.BaseExpression"],
                      path: str) -> "advanced_functions.JSONExpression":
    """Creates a JSON extract text operation (e.g., column->>path)."""
    target_column = column if isinstance(column, bases.BaseExpression) else core.Column(dialect, column)
    return advanced_functions.JSONExpression(dialect, target_column, path, operation="->>")

def json_build_object(dialect: "SQLDialectBase", *key_value_pairs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a JSON_BUILD_OBJECT function call."""
    # Expect pairs of key-value expressions
    processed_args = []
    for arg in key_value_pairs:
        processed_args.append(arg if isinstance(arg, bases.BaseExpression) else core.Literal(dialect, arg))
    return core.FunctionCall(dialect, "JSON_BUILD_OBJECT", *processed_args)

def json_array_elements(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a JSON_ARRAY_ELEMENTS function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "JSON_ARRAY_ELEMENTS", target_expr)


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
    """Creates a CAST expression."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return advanced_functions.CastExpression(dialect, target_expr, target_type)

def to_char(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
            format: Optional[str] = None) -> "core.FunctionCall":
    """Creates a TO_CHAR function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    if format is not None:
        format_expr = core.Literal(dialect, format)
        return core.FunctionCall(dialect, "TO_CHAR", target_expr, format_expr)
    return core.FunctionCall(dialect, "TO_CHAR", target_expr)

def to_number(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
              format: Optional[str] = None) -> "core.FunctionCall":
    """Creates a TO_NUMBER function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    if format is not None:
        format_expr = core.Literal(dialect, format)
        return core.FunctionCall(dialect, "TO_NUMBER", target_expr, format_expr)
    return core.FunctionCall(dialect, "TO_NUMBER", target_expr)

def to_date(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"],
            format: Optional[str] = None) -> "core.FunctionCall":
    """Creates a TO_DATE function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    if format is not None:
        format_expr = core.Literal(dialect, format)
        return core.FunctionCall(dialect, "TO_DATE", target_expr, format_expr)
    return core.FunctionCall(dialect, "TO_DATE", target_expr)
