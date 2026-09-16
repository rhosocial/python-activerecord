# src/rhosocial/activerecord/backend/expression/statements/fulltext_match.py
from typing import List, Optional
from ..core import BaseExpression


class FulltextMatchExpression(BaseExpression):
    """MATCH ... AGAINST full-text search expression."""

    def __init__(self, dialect, columns: List[str], search_term: str,
                 mode: Optional[str] = None):
        super().__init__(dialect)
        self.columns = columns
        self.search_term = search_term
        self.mode = mode

    @property
    def format_method(self) -> str:
        return "format_fulltext_match"
