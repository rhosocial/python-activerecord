# src/rhosocial/activerecord/backend/base/returning.py
import logging
from typing import List, Optional, Union
from ..dialect import ReturningOptions
from ..errors import ReturningNotSupportedError
from ..schema import StatementType

class ReturningClauseMixin:
    """Mixin for RETURNING clause processing."""
    def _process_returning_options(self, returning: Optional[Union[bool, List[str], ReturningOptions]]) -> Optional[ReturningOptions]:
        if returning is None: return None
        if isinstance(returning, bool): return ReturningOptions.from_legacy(returning)
        if isinstance(returning, list): return ReturningOptions.columns_only(returning)
        if isinstance(returning, ReturningOptions): return returning
        raise ValueError(f"Unsupported returning type: {type(returning)}")
    def _prepare_returning_clause(self, sql: str, options: ReturningOptions, stmt_type: StatementType) -> str:
        # This is a placeholder for logic that would exist in a real implementation
        return sql + " RETURNING *"
    def _check_returning_compatibility(self, options: ReturningOptions) -> None:
        pass