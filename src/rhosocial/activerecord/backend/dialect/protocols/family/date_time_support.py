# src/rhosocial/activerecord/backend/dialect/protocols/family/DateTimeSupport.py
"""Protocol mirror of DateTimeMixin (family-level feature group). Members/order/signatures identical."""

from typing import Tuple
from rhosocial.activerecord.backend.expression import bases
from typing import runtime_checkable, Protocol


@runtime_checkable
class DateTimeSupport(Protocol):
    def apply_alias(self, sql: str, params: tuple, expr) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_extract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_now_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_current_date_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_current_time_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_current_timestamp_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_localtimestamp_function(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_date_part_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_date_trunc_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_interval_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_datetime_add_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_datetime_subtract_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_datetime_diff_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover

    def format_seconds_between_expression(self, expr: "bases.BaseExpression") -> Tuple[str, Tuple]:
        ...  # pragma: no cover
