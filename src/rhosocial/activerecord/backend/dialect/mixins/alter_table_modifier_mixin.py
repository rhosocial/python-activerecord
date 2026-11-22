# .../mixins/alter_table_modifier_mixin.py
"""Mixin for AlterTableModifierSupport. Members/order/signature mirror the protocol."""

class AlterTableModifierMixin:

    def supports_add_column_if_not_exists(self) -> bool:
            """Whether ``ADD COLUMN IF NOT EXISTS`` is supported.

            Defaults to ``False``; backends that support the vendor extension
            override this to return ``True``.
            """
            return False

    def supports_drop_column_if_exists(self) -> bool:
            """Whether ``DROP COLUMN IF EXISTS`` is supported.

            Defaults to ``False``; backends that support the vendor extension
            override this to return ``True``.
            """
            return False

    def supports_drop_constraint_if_exists(self) -> bool:
            """Whether ``DROP CONSTRAINT IF EXISTS`` is supported.

            Defaults to ``False``; backends that support the vendor extension
            override this to return ``True``.
            """
            return False
