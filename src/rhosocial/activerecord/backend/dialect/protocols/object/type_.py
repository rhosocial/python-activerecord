# src/rhosocial/activerecord/backend/dialect/protocols/object/type_.py
"""Rendering a type or domain name -- the ``data_type`` position."""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

from .namespace import NamespaceSupport

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.objects import Domain, Type

__all__ = ["TypeObjectSupport"]


@runtime_checkable
class TypeObjectSupport(NamespaceSupport, Protocol):
    """How a user-defined type or a domain is named.

    These names appear where a type is expected rather than where a table is
    expected::

        CREATE TABLE account (balance positive_money);

    Type and domain share a protocol because both are types and both are named
    the same way. They are not one class -- a domain is a type plus constraints,
    and an engine may support one without the other -- so the protocol declares
    a formatter for each.
    """

    def format_type_object(self, expr: "Type") -> Tuple[str, tuple]:
        """Render *expr* as a type name.

        This is the name in a ``data_type`` position: a column declared as this
        type, a cast target. Distinct from ``format_type_definition``, which
        renders the declaration of the type rather than a reference to it.

        Args:
            expr: The type being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: The type carries a namespace level this
                dialect declares it cannot express.
        """
        ...  # pragma: no cover

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
        ...  # pragma: no cover