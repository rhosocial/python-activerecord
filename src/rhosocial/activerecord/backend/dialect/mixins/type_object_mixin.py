# .../mixins/type_object_mixin.py
"""Object-naming mixin. Members/order/signature mirror the protocol."""

from typing import Tuple
from .schema_namespace import NamespaceMixin
from ...expression.objects import Type
from ...expression.objects import Domain

class TypeObjectMixin:
    def format_type_object(self, expr: "Type") -> "Tuple[str, tuple]":
            """Render *expr* as a type name.

            Args:
                expr: The type being named.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is empty, because an
                identifier is never a bind parameter.

            Raises:
                UnsupportedFeatureError: The type carries a namespace level this
                    dialect declares it cannot express.
            """
            self.validate_namespace(expr)
            return self.format_qualified_name(expr)

    def format_domain_object(self, expr: "Domain") -> "Tuple[str, tuple]":
            """Render *expr* as a domain name.

            Args:
                expr: The domain being named.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is empty, because an
                identifier is never a bind parameter.

            Raises:
                UnsupportedFeatureError: The domain carries a namespace level this
                    dialect declares it cannot express.
            """
            self.validate_namespace(expr)
            return self.format_qualified_name(expr)
