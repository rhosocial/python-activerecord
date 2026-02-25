# src/rhosocial/activerecord/backend/base/result_processing.py
import logging
from typing import List, Optional, Dict
from ..result import QueryResult
from ..schema import StatementType

class ResultProcessingMixin:
    """Mixin for query result processing."""
    def _log_query_completion(self, stmt_type: StatementType, cursor, data: Optional[List[Dict]], duration: float) -> None:
        if stmt_type == StatementType.DML:
            rowcount = getattr(cursor, 'rowcount', 0)
            lastrowid = getattr(cursor, 'lastrowid', None)
            self.log(logging.INFO, f"{stmt_type.name} affected {rowcount} rows, last_insert_id={lastrowid}, duration={duration:.3f}s")
        elif stmt_type == StatementType.DQL:
            row_count = len(data) if data is not None else 0
            self.log(logging.INFO, f"{stmt_type.name} returned {row_count} rows, duration={duration:.3f}s")
    def _build_query_result(self, cursor, data: Optional[List[Dict]], duration: float) -> QueryResult:
        return QueryResult(data=data, affected_rows=getattr(cursor, 'rowcount', 0), last_insert_id=getattr(cursor, 'lastrowid', None), duration=duration)