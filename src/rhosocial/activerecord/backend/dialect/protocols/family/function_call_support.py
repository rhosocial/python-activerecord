# src/rhosocial/activerecord/backend/dialect/protocols/family/FunctionCallSupport.py
"""Protocol mirror of FunctionCallMixin (family-level feature group). Members/order/signatures identical."""

import re
from typing import Any, Dict, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.objects import Function
from typing import runtime_checkable, Protocol


@runtime_checkable
class FunctionCallSupport(Protocol):
    def format_function_call(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_row_number_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_rank_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_dense_rank_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_json_objectagg_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_json_arrayagg_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_absolute_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_round_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_ceil_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_floor_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_truncate_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_square_root_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_power_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_exponential_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_logarithm_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_sine_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_cosine_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_tangent_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_modulo_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_sign_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_array_agg_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_count_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_sum_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_avg_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_min_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_max_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_upper_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_lower_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_char_length_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_current_user_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_session_user_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_system_user_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_declared_result(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_concat_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_coalesce_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_substring_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_overlay_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_position_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_replace_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_initcap_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_left_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_right_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_reverse_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_translate_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_space_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_chr_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_ascii_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_octet_length_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_bit_length_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_to_char_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_to_number_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_to_date_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_unnest_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_array_length_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_json_build_object_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_json_array_elements_function(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover
