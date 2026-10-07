# src/rhosocial/activerecord/backend/dialect/mixins/object_sequence_name.py
"""Sequence naming.

The counterpart of :attr:`Sequence.format_method`, and the only code that turns a
sequence into SQL. A dialect that spells sequences differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Sequence

__all__ = ["SequenceNameMixin"]


class SequenceNameMixin(NamespaceMixin):
    """Renders a sequence as its name."""

    def format_sequence_object(self, expr: "Sequence") -> Tuple[str, tuple]:
        """Render *expr* as a sequence name.

        Args:
            expr: The sequence being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The sequence carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
