# src/rhosocial/activerecord/backend/dialect/protocols/sqlfunctionsupport.py
"""SQLFunctionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Dict, Protocol, runtime_checkable

@runtime_checkable
class SQLFunctionSupport(Protocol):
    """Protocol for SQL function availability detection.

    This protocol exposes all SQL functions supported by the current dialect,
    including both standard functions and backend-specific functions.

    Scope:
    ======
    This protocol covers ALL SQL functions that can be invoked as expressions:
    - Aggregate functions: COUNT, SUM, AVG, MIN, MAX
    - Window functions: ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD
    - Scalar functions: SUBSTR, INSTR, LOWER, UPPER
    - JSON functions: JSON_EXTRACT, JSON_ARRAY, JSON_OBJECT
    - Date/Time functions: DATE, TIME, DATETIME, STRFTIME
    - Math functions: ABS, ROUND, SQRT, POW
    - System functions: CURRENT_USER, VERSION
    - Backend-specific: SQLite's IIF, MySQL's ST_Distance, etc.

    Relation to Other Protocols:
    ============================
    Other protocols may check specific FUNCTION CATEGORIES as capability flags:
    - WindowFunctionSupport.supports_window_functions() - Window feature capability
    - JSONSupport.supports_json_type() - JSON capability
    - CreateRoutineSupport.supports_create_function() - DDL (CREATE FUNCTION)

    SQLFunctionSupport is DIFFERENT: it returns the actual list of functions
    available in the current dialect version, as a function_name -> bool dict.

    This protocol DOES NOT replace existing capability protocols.
    Both are valid and serve different purposes:
    - Capability protocols: "Does the dialect support this feature category?"
    - SQLFunctionSupport: "Which specific functions can I call?"

    Function Sources:
    =================
    The function list is built from TWO sources:
    1. Core functions (rhosocial.activerecord.backend.expression.functions)
       - Standard SQL functions: count, sum, row_number, json_extract, etc.
       - Always available (subject to dialect capability)
    2. Backend-specific functions (rhosocial.activerecord.backend.impl.{backend}.functions)
       - SQLite: iif, substr, instr, json, etc.
       - MySQL: ST_Distance, ST_Within, etc.
       - PostgreSQL: array_agg (PostgreSQL-specific), etc.

    Usage:
        dialect.supports_functions() -> {
            "count": True, "sum": True, "row_number": True,
            "substr": True, "ST_Distance": False, ...
        }
    """

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        Returns:
            Dict mapping function names to True (supported) or False (not supported).
            The dict contains ALL functions from both core and backend-specific sources.

        Example:
            {
                # Core functions
                "count": True,
                "sum": True,
                "row_number": True,
                "json_extract": True,
                # Backend-specific
                "substr": True,      # SQLite
                "iif": True,         # SQLite
                "ST_Distance": False, # Not available in SQLite
                ...
            }
        """
        ...  # pragma: no cover
