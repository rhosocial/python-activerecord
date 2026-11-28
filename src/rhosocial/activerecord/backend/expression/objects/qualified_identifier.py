# src/rhosocial/activerecord/backend/expression/objects/qualified_identifier.py
from typing import Optional, TYPE_CHECKING

from ..bases.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class QualifiedIdentifier(BaseExpression):
    """Represents a schema-qualified identifier (e.g., schema.table_name).

    Per-role quoting fields (all default to ``True``):
    - ``name_need_quote`` ↔ ``name``
    - ``schema_need_quote`` ↔ ``schema``
    """

    @property
    def format_method(self) -> str:
        return "format_qualified_identifier"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        name: str = "",
        name_need_quote: bool = True,
        schema_need_quote: bool = True,
    ):
        super().__init__(dialect)
        self.name_need_quote = self.quote_flag(name_need_quote, "name_need_quote")
        self.schema_need_quote = self.quote_flag(schema_need_quote, "schema_need_quote")
        self.schema = schema
        self.name = name
