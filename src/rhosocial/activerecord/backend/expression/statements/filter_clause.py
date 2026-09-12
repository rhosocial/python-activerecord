# src/rhosocial/activerecord/backend/expression/statements/filter_clause.py
from ..core import BaseExpression


class FilterClauseExpression(BaseExpression):
    """FILTER (WHERE ...) clause wrapping a condition expression."""

    def __init__(self, dialect, condition: BaseExpression):
        super().__init__(dialect)
        self.condition = condition

    @property
    def format_method(self) -> str:
        return "format_filter_clause"
