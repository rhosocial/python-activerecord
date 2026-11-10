# src/rhosocial/activerecord/backend/base/result_processing.py
from typing import List, Optional, Dict
from ..result import QueryResult


class ResultProcessingMixin:
    """Mixin for query result processing."""

    def _build_query_result(self, cursor, data: Optional[List[Dict]], duration: float) -> QueryResult:
        return QueryResult(
            data=data,
            affected_rows=getattr(cursor, "rowcount", 0),
            last_insert_id=getattr(cursor, "lastrowid", None),
            duration=duration,
        )
