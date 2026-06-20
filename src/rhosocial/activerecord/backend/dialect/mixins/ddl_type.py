# src/rhosocial/activerecord/backend/dialect/mixins/ddl_type.py
"""``DDLTypeMixin`` — registry-based type formatting mechanism.

Each backend registers its own ``DataType`` formatters via
``@DDLTypeMixin.handles(TypeClass)``.  The base mixin provides only the
dispatch logic; it does **not** register any types itself.

.. note::

   ``handles`` is a ``@staticmethod`` that tags the decorated method.
   ``__init_subclass__`` then scans for tagged methods and builds a
   per-subclass ``_type_formatters`` dict so that registrations stay
   isolated and never conflict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...expression.types._base import DataType


class DDLTypeMixin:
    """Mixin providing registry-based ``format_data_type()`` dispatch.

    Subclasses register formatters via the :meth:`handles` decorator::

        class MySQLTypeSupportMixin(DDLTypeMixin):
            @DDLTypeMixin.handles(MySQLIntType)
            def format_data_type_int(self, data_type: MySQLIntType) -> str:
                return "INT UNSIGNED" if data_type.unsigned else "INT"

    ``format_data_type()`` walks the MRO to find a matching formatter.
    Unregistered types raise ``TypeError``.
    """

    _type_formatters: dict = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._type_formatters = {}
        for member_name in dir(cls):
            member = getattr(cls, member_name, None)
            handles_types = getattr(member, "_handles_types", None)
            if handles_types is not None:
                for dt_cls in handles_types:
                    cls._type_formatters[dt_cls] = member_name

    @staticmethod
    def handles(*data_type_classes):
        """Decorator — tag a method as a formatter for *data_type_classes*.

        The actual registration happens in ``__init_subclass__`` so each
        subclass gets its own isolated registry.
        """
        def decorator(fn):
            fn._handles_types = data_type_classes
            return fn
        return decorator

    def format_data_type(self, data_type: DataType) -> str:
        for klass in type(self).__mro__:
            formatters = getattr(klass, "_type_formatters", {})
            if type(data_type) in formatters:
                return getattr(self, formatters[type(data_type)])(data_type)
        raise TypeError(
            f"{type(self).__name__} does not support {type(data_type).__name__}. "
            f"Use an appropriate backend-specific DataType."
        )

    def supports_data_types(self) -> list:
        """Return ``(DataTypeClass, sql_name)`` pairs from the registry.

        Auto-generated from ``@handles`` registrations so it stays in sync
        without manual maintenance.
        """
        result = []
        seen = set()
        for klass in type(self).__mro__:
            for dt_cls, method_name in getattr(klass, "_type_formatters", {}).items():
                if dt_cls not in seen:
                    seen.add(dt_cls)
                    try:
                        sql_name = getattr(self, method_name)(dt_cls())
                    except TypeError:
                        sql_name = dt_cls.__name__
                    result.append((dt_cls, sql_name))
        return result
