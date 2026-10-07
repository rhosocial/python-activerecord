# src/rhosocial/activerecord/backend/dialect/protocols/ddl/table/create_table_using_template.py
"""
CreateTableUsingTemplateSupport.

``CREATE TABLE ... USING TEMPLATE`` -- derive the shape from a staged template query.

Naming an object is not here -- that is
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .....expression.statements import (
        CreateTableFromTemplateExpression,
    )


@runtime_checkable
class CreateTableUsingTemplateSupport(Protocol):
    """``CREATE TABLE ... USING TEMPLATE`` -- derive the shape from a staged template query.

    One protocol per statement expression: the ``format_*`` methods below are
    the counterparts of the ``format_method`` those expressions declare.
    """

    def supports_create_table_using_template(self) -> bool:
        """Whether the engine accepts the form ``create_table_using_template``.

        Defaults to ``False``; a dialect that accepts it returns ``True``.
        """
        ...  # pragma: no cover

    def format_create_table_using_template(self, expr: "CreateTableFromTemplateExpression") -> Tuple[str, tuple]:
        """Render a :class:`~....expression.statements.CreateTableFromTemplateExpression`.

        Raises rather than emitting an unsupported form: a statement the
        engine cannot parse is not a statement worth producing.
        """
        ...  # pragma: no cover
