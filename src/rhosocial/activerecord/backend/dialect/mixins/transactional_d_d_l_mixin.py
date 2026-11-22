# src/rhosocial/activerecord/backend/dialect/mixins/transactional_d_d_l_mixin.py
"""Mixin for TransactionalDDLSupport. Members/order/signature mirror the protocol."""


class TransactionalDDLMixin:
    def supports_transactional_ddl(self) -> bool:
        return False  # default: DDL not transactional
