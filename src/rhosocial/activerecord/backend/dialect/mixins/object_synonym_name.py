# src/rhosocial/activerecord/backend/dialect/mixins/object_synonym_name.py
"""Synonym naming.

The counterpart of :attr:`Synonym.format_method`, and the only code that turns a
synonym into SQL. A dialect that spells synonyms differently overrides this
method rather than any statement that happens to mention one.

Which namespace levels appear in the output is
:meth:`~.schema_namespace.NamespaceMixin.validate_namespace`'s decision, so this
method only appends the object's own name to what that returned.
"""

from typing import Tuple

from .schema_namespace import NamespaceMixin
from ...expression.objects import Synonym

__all__ = ["SynonymNameMixin"]


class SynonymNameMixin(NamespaceMixin):
    """Renders a synonym as its name."""

    def format_synonym_object(self, expr: "Synonym") -> Tuple[str, tuple]:
        """Render *expr* as a synonym name.

        Args:
            expr: The synonym being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The synonym carries a namespace level this
                dialect declares it cannot express.
        """
        self.validate_namespace(expr)
        return self.format_qualified_name(expr)
