# src/rhosocial/activerecord/backend/expression/literals.py
"""
Literal identifiers in SQL expressions.
"""

from typing import TYPE_CHECKING
from .bases import SQLValue
from .mixins import ComparisonMixin

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class Identifier(ComparisonMixin, SQLValue):
    """Represents a generic SQL identifier (e.g., table name, column name, alias).

    Per-role quoting fields (all default to ``True``):
    - ``name_need_quote`` ↔ ``name``
    - ``alias_need_quote`` ↔ ``alias``
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        name_need_quote: bool = True,
        alias_need_quote: bool = True,
    ):
        super().__init__(dialect)
        self.name_need_quote = self.quote_flag(name_need_quote, "name_need_quote")
        self.alias_need_quote = self.quote_flag(alias_need_quote, "alias_need_quote")
        self.name = name

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_identifier_expression"

    def __repr__(self) -> str:
        return f"Identifier({self.name!r})"


# No registration call: the framework's assembly point walks this package and
# registers Identifier like every other node. The old class index needed to be
# told about a class defined outside its own walk; the registry does not.
