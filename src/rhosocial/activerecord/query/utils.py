# src/rhosocial/activerecord/query/utils.py
"""Query utility functions for the ActiveRecord layer.

This module provides internal utilities used by the query building
layer, such as placeholder conversion for raw SQL strings.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def convert_qmark_placeholder(dialect: "SQLDialectBase", sql: str) -> str:
    """Convert '?' parameter placeholders to the dialect's native format.

    The ActiveRecord layer uses '?' as its API placeholder convention.
    This function converts them to the format required by the backend
    driver (SQLite→'?': no conversion needed, MySQL/PostgreSQL→'%s').

    Escape rules (standard backslash escaping):
    - ``\\?`` is converted to a literal ``?`` (used for backend-specific
      operators like PostgreSQL's ``?``, ``?|``, ``?&`` for hstore/jsonb)
    - ``\\\\`` is converted to a literal ``\\`` (standard backslash escape)
    - Unescaped ``?`` is replaced with the dialect's parameter placeholder

    This function contains no backend-specific knowledge and is fully generic.

    Args:
        dialect: The SQL dialect instance providing ``get_parameter_placeholder()``.
        sql: The raw SQL string potentially containing ``?`` placeholders.

    Returns:
        The SQL string with placeholders converted to the dialect's native format.
    """
    placeholder = dialect.get_parameter_placeholder()
    if placeholder == "?":
        # '?' dialect: no placeholder replacement needed, but still process escapes
        # Use iterative replacement to handle \\ before \?
        result = []
        i = 0
        length = len(sql)
        while i < length:
            if sql[i] == '\\' and i + 1 < length:
                if sql[i + 1] == '\\':
                    result.append('\\')
                    i += 2
                elif sql[i + 1] == '?':
                    result.append('?')
                    i += 2
                else:
                    result.append(sql[i])
                    i += 1
            else:
                result.append(sql[i])
                i += 1
        return ''.join(result)

    result = []
    i = 0
    length = len(sql)
    while i < length:
        if sql[i] == '\\' and i + 1 < length:
            if sql[i + 1] == '\\':
                # \\ → preserve literal \
                result.append('\\')
                i += 2
            elif sql[i + 1] == '?':
                # \? → preserve literal ?
                result.append('?')
                i += 2
            else:
                # \x where x is not ? or \ → preserve as-is
                result.append(sql[i])
                i += 1
        elif sql[i] == '?':
            # Unescaped ? → replace with dialect placeholder
            result.append(placeholder)
            i += 1
        else:
            result.append(sql[i])
            i += 1
    return ''.join(result)
