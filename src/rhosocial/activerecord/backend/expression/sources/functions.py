# src/rhosocial/activerecord/backend/expression/sources/functions.py
"""
Table sources produced by a call.

A function that returns a set can be read from. That does not make it a
table: it is still a routine in the catalogue, and whether it is *usable here*
is a property of its return type rather than of its identity. The check
belongs where the query is built, not on the object.
"""

from typing import Any, Optional

from .base import TableSource

__all__ = ["TableFunctionSource"]


class TableFunctionSource(TableSource):
    """A function invoked in a ``FROM`` clause for its rows."""

    __slots__ = ("function_name", "args", "with_ordinality")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this source."""
        return "format_table_function"

    def __init__(
        self,
        dialect: "SQLDialectBase",  # noqa: F821
        function_name: str,
        args: Optional[Any] = None,
        with_ordinality: bool = False,
        alias: Optional[str] = None,
        alias_need_quote: bool = True,
    ) -> None:
        """Invoke *function_name* as a row source.

        Args:
            dialect: The dialect that will render this source.
            function_name: Name of the function to invoke.
            args: Arguments, as expressions or literals.
            with_ordinality: Whether to append an ordinality column
                (PostgreSQL; rejected elsewhere).
            alias: Name this source is known by inside the query.
            alias_need_quote: Whether the alias is quoted when rendered.
        """
        super().__init__(dialect, alias=alias, alias_need_quote=alias_need_quote)
        self.function_name = function_name
        self.args = args
        self.with_ordinality = with_ordinality