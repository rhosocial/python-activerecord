# src/rhosocial/activerecord/backend/dialect/protocols/object/index.py
"""Rendering an index name."""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

from .namespace import NamespaceSupport

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.objects import Index

__all__ = ["IndexObjectSupport"]


@runtime_checkable
class IndexObjectSupport(NamespaceSupport, Protocol):
    """How an :class:`~....expression.objects.Index` is named.

    An index is not a relation -- ``FROM my_index`` is not legal -- so it has
    its own protocol rather than joining the relations. What names it is shared
    with every other object; only the kind differs.
    """

    def format_index_object(self, expr: "Index") -> Tuple[str, tuple]:
        """Render *expr* as an index name.

        This is the name ``CREATE INDEX`` and ``DROP INDEX`` act on and the name
        a table's inline index definition carries. Distinct from
        ``format_create_index_statement``, which renders the statement.

        Args:
            expr: The index being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The index carries a namespace level this
                dialect declares it cannot express.
        """
        ...  # pragma: no cover