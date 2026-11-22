# src/rhosocial/activerecord/backend/dialect/mixins/timestamp_mixin.py
"""Mixin for TimestampSupport. Members/order/signature mirror the protocol."""


class TimestampMixin:
    def supports_microsecond_timestamp(self) -> bool:
        return False  # default: no microsecond precision guarantee
