# src/rhosocial/activerecord/backend/dialect/mixins/database_assigned_column_mixin.py
"""Mixin for DatabaseAssignedColumnSupport. Members/order/signature mirror the protocol."""


class DatabaseAssignedColumnMixin:
    def supports_database_assigned_integer_column(self) -> bool:
        return False  # default: no database-assigned integer column
