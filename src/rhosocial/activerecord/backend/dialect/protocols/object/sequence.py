# src/rhosocial/activerecord/backend/dialect/protocols/object/sequence.py
"""Rendering a sequence name."""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

from .namespace import NamespaceSupport

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.objects import Sequence

__all__ = ["SequenceObjectSupport"]


@runtime_checkable
class SequenceObjectSupport(NamespaceSupport, Protocol):
    """How a :class:`~....expression.objects.Sequence` is named.

    A sequence is persistent and named but not a relation: most engines reach it
    through a function call rather than by naming it in a query. Its protocol is
    therefore its own, so an engine can name a sequence without offering it as a
    readable source, or the reverse.
    """

    def format_sequence_object(self, expr: "Sequence") -> Tuple[str, tuple]:
        """Render *expr* as a sequence name.

        This is the name the sequence is created and altered by. Distinct from
        ``format_create_sequence_statement``, which renders the statement.

        Args:
            expr: The sequence being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The sequence carries a namespace level
                this dialect declares it cannot express.
        """
        ...  # pragma: no cover