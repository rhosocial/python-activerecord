# src/rhosocial/activerecord/backend/dialect/mixins/sql_function_mixin.py
"""Per-statement mixin for SQLFunctionSupport. Members/order/signature mirror the protocol."""

from typing import Any, Dict, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Function

class SQLFunctionMixin:
    def supports_functions(self) -> Dict[str, bool]:
            """Return supported SQL functions as function_name -> bool mapping.

            Default implementation returns empty dict. Subclasses should override
            to provide actual function list from both core and backend-specific sources.

            Returns:
                Dict mapping function names to True/False. Default: empty dict.
            """
            return {}
