# src/rhosocial/activerecord/backend/impl/sqlite/expression/json.py
"""SQLite-specific JSON expression nodes."""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression, SQLValue
from rhosocial.activerecord.backend.expression.mixins import (
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class SQLiteJsonExtractFunction(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValue,
):
    """``json_extract(expression, path)`` — SQLite's single-path extraction.

    This is a **backend-specific node** and lives in the SQLite implementation
    package, not the core expression layer (catalog §3.4): the same concept is
    spelled ``->`` on PostgreSQL and ``JSON_EXTRACT`` with a path grammar of
    its own on MySQL, so the core must not reserve a slot for any one backend's
    spelling.

    It exists because ``json_extract`` is a real function with its own
    rendering, and building it through :class:`FunctionCall` would leave the
    function's identity inside a name string. The path is an expression
    (usually a string literal), so it binds like any other operand and never
    reaches the SQL as hand-concatenated text.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: "BaseExpression",
        path: "BaseExpression",
    ):
        super().__init__(dialect)
        self.expression = expression
        self.path = path

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_sqlite_json_extract_function"
