# src/rhosocial/activerecord/base/field_proxy.py
"""
Field proxy implementation for accessing model fields via Model.proxy_name.field_name syntax.

This module provides the FieldProxy class, which allows users to access model fields
using syntax like User.c.name, and generates corresponding SQL expression objects.
Supports:
- Normal field access
- UseColumn annotated fields
- Dynamic table aliases
- Predefined table aliases
- Column aliases
- Self-join queries
"""

from typing import ClassVar, TYPE_CHECKING
from ..backend.expression.core import Column

if TYPE_CHECKING:
    from ..backend.dialect.base import SQLDialectBase
    from ..model import ActiveRecord



class FieldProxy:
    """Field proxy descriptor for accessing fields via Model.proxy_name.field_name syntax"""

    def __init__(self, table_alias: str = None):
        """
        Initialize field proxy
        :param table_alias: Optional table alias, if provided all columns from this proxy will use this table alias
        """
        self._table_alias = table_alias

    def __get__(self, instance, owner):
        # Return a dynamic field accessor
        class _FieldAccessor:
            def __init__(self, model_class: 'ActiveRecord', static_table_alias: str = None):
                self._model_class = model_class
                self._table_alias = static_table_alias  # Could be set during initialization

            def with_table_alias(self, alias: str):
                """Set table alias"""
                new_accessor = _FieldAccessor(self._model_class, alias)
                return new_accessor

            def __getattr__(self, field_name: str):
                # Use Pydantic's model_fields to get field information
                if field_name not in self._model_class.model_fields:
                    raise AttributeError(f"Field '{field_name}' does not exist on model '{self._model_class.__name__}'")

                # Use ColumnNameMixin's method to get the correct column name
                # This properly handles UseColumn annotations, returning custom column name if UseColumn is used, otherwise field name
                column_name = self._model_class._get_column_name(field_name)

                # Use table alias (if set) as table name
                table_name = self._table_alias if self._table_alias else self._model_class.table_name()

                # Create column expression object using the real dialect
                backend = self._model_class.backend()
                dialect: 'SQLDialectBase' = backend.dialect
                return Column(dialect, column_name, table=table_name)

        return _FieldAccessor(owner, self._table_alias)