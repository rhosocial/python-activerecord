# src/rhosocial/activerecord/backend/dialect/mixins/object_trigger_name.py
"""Trigger naming.

The counterpart of :attr:`Trigger.format_method`, and the only code that turns a
trigger into SQL. A dialect that spells triggers differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Trigger

__all__ = ["TriggerNameMixin"]


class TriggerNameMixin(NamespaceMixin):
    """Renders a trigger as its name."""

    def format_trigger_object(self, expr: "Trigger") -> Tuple[str, tuple]:
        """Render *expr* as a trigger name.

        Args:
            expr: The trigger being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The trigger carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
