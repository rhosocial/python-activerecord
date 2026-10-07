# src/rhosocial/activerecord/backend/dialect/protocols/query/json.py
"""JSONSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Any, Dict, Optional, Protocol, TYPE_CHECKING, Tuple, runtime_checkable

from ....expression import bases

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import JSONExpression


@runtime_checkable
class JSONSupport(Protocol):
    """Protocol for JSON type support."""

    def supports_json_type(self) -> bool:
        """Whether JSON type is supported."""
        ...  # pragma: no cover

    def supports_json_arrow_operators(self) -> bool:
        """Whether JSON arrow operators (-> and ->>) are supported.

        Backends that do not support arrow operators use function-based
        alternatives (e.g., JSON_EXTRACT/JSON_UNQUOTE) in format_json_expression.
        """
        ...  # pragma: no cover

    def get_json_access_operator(self) -> str:
        """
        Get JSON access operator.

        Returns:
            '->' (PostgreSQL/MySQL/SQLite) or other dialect-specific operator
        """
        ...  # pragma: no cover

    def supports_json_table(self, dialect_options: Optional[Dict[str, Any]] = None) -> bool:
        """Whether JSON_TABLE function is supported.

        Args:
            dialect_options: Optional backend-specific options (e.g., MySQL: {'on_error': 'IGNORE'})
                See backend-specific documentation for available options.
        """
        ...  # pragma: no cover

    def format_json_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """
        Format JSON expression.

        Dispatches to arrow or function-based formatting depending on the
        expression's *mode* and the dialect's capability:

        - ``JSONPathMode.ARROW``:    always use arrow operators (raises if unsupported)
        - ``JSONPathMode.FUNCTION``: always use function-based formatting
        - ``JSONPathMode.AUTO``:     use arrow if supported, else function-based

        Args:
            expr: JSONExpression node carrying column, path, and operation info.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

    def format_json_arrow_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """
        Force-arrow JSON path formatting.

        Always renders the JSON path using arrow operators (-> / ->>).
        Raises ``UnsupportedFeatureError`` when the dialect does not
        support them.
        """
        ...  # pragma: no cover

    def format_json_function_expression(self, expr: "JSONExpression") -> Tuple[str, Tuple]:
        """
        Force-function JSON path formatting.

        Always renders the JSON path via function-based equivalents
        such as JSON_EXTRACT / JSON_UNQUOTE or backend-specific
        functions (e.g. Snowflake VARIANT colon notation).
        """
        ...  # pragma: no cover

    def format_json_table_expression(
        self,
        expr: "bases.BaseExpression",
    ) -> Tuple[str, Tuple]:
        """
        Formats a JSON_TABLE expression.

        Args:
            expr: JSONTableExpression node carrying all formatting state
                  (json_col, path, columns, alias, dialect_options, etc.).

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover
