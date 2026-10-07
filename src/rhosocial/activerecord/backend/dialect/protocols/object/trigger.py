# src/rhosocial/activerecord/backend/dialect/protocols/object/trigger.py
"""Rendering a trigger name."""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

from .namespace import NamespaceSupport

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.objects import Trigger

__all__ = ["TriggerObjectSupport"]


@runtime_checkable
class TriggerObjectSupport(NamespaceSupport, Protocol):
    """How a :class:`~....expression.objects.Trigger` is named.

    A trigger's name is scoped differently across engines -- PostgreSQL requires
    it to be unique per target table rather than per schema -- so this protocol
    exists to be overridden where the namespace alone does not identify the
    trigger. That difference is about *how a trigger is named*, not about the
    statement that creates one, which is why it belongs here.
    """

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
        ...  # pragma: no cover