# src/rhosocial/activerecord/backend/dialect/mixins/object_domain_name.py
"""Domain naming.

The counterpart of :attr:`Domain.format_method`, and the only code that turns a
domain into SQL. A dialect that spells domains differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Domain

__all__ = ["DomainNameMixin"]


class DomainNameMixin(NamespaceMixin):
    """Renders a domain as its name."""

    def format_domain_object(self, expr: "Domain") -> Tuple[str, tuple]:
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
