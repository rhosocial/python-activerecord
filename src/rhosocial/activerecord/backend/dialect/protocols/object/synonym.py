# src/rhosocial/activerecord/backend/dialect/protocols/object/synonym.py
"""Rendering a synonym name."""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

from .namespace import NamespaceSupport

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.objects import Synonym

__all__ = ["SynonymObjectSupport"]


@runtime_checkable
class SynonymObjectSupport(NamespaceSupport, Protocol):
    """How a :class:`~....expression.objects.Synonym` is named.

    A synonym is an alternative name resolving to another object -- a table, a
    view, a sequence, a type, even another synonym. What it resolves to is a
    property of the definition rather than of the name, so only the name is
    rendered here; the same synonym may be re-pointed without the object ceasing
    to exist.
    """

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
        ...  # pragma: no cover