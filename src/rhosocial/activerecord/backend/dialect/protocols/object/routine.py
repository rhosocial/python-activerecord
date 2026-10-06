# src/rhosocial/activerecord/backend/dialect/protocols/object/routine.py
"""Rendering a routine name -- function or procedure."""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

from .namespace import NamespaceSupport

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.objects import Function, Procedure

__all__ = ["RoutineObjectSupport"]


@runtime_checkable
class RoutineObjectSupport(NamespaceSupport, Protocol):
    """How a function or a procedure is named.

    Function and procedure share one protocol because they share the question:
    what is this routine called. They are not one class -- an engine may spell
    them differently, and a procedure is never read as a relation -- so the
    protocol declares a formatter for each and a backend overrides only the one
    it spells differently.
    """

    def format_function_object(self, expr: "Function") -> Tuple[str, tuple]:
        """Render *expr* as a function name.

        This is the name the function is called by, and -- when it returns a set
        -- the name it is read as a relation under.

        Args:
            expr: The function being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The function carries a namespace level
                this dialect declares it cannot express.
        """
        ...  # pragma: no cover

    def format_procedure_object(self, expr: "Procedure") -> Tuple[str, tuple]:
        """Render *expr* as a procedure name.

        Args:
            expr: The procedure being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The procedure carries a namespace level
                this dialect declares it cannot express.
        """
        ...  # pragma: no cover