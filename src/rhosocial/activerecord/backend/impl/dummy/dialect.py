# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy Dialect for SQL generation without a real backend.
"""
from typing import Dict, Any, Optional, List, Tuple

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase,
    ReturningOptions,
    ReturningClauseHandler,
    SQLExpressionBase,
    ExplainOptions,
    AggregateHandler,
    JsonOperationHandler,
    CTEHandler,
    ExplainType, # New import for ExplainType
    ExplainFormat # New import for ExplainFormat
)
from rhosocial.activerecord.backend.errors import ReturningNotSupportedError


# --- New DummySQLExpression class ---
class DummySQLExpression(SQLExpressionBase):
    """A simple dummy SQL expression."""
    def format(self, dialect: 'SQLDialectBase') -> str:
        return self.expression


# --- Dummy Handlers for abstract properties ---
class DummyAggregateHandler(AggregateHandler):
    """A dummy aggregate handler that raises NotImplementedError for all operations."""
    def __init__(self, version: Tuple):
        super().__init__(version)
    @property
    def supports_window_functions(self) -> bool: return False
    @property
    def supports_advanced_grouping(self) -> bool: return False
    def format_window_function(self, expr, pb, ob, ft, fs, fe, eo) -> str: raise NotImplementedError("DummyAggregateHandler.format_window_function")
    def format_grouping_sets(self, tn, cols) -> str: raise NotImplementedError("DummyAggregateHandler.format_grouping_sets")


class DummyJsonOperationHandler(JsonOperationHandler):
    """A dummy JSON operation handler that raises NotImplementedError for all operations."""
    @property
    def supports_json_operations(self) -> bool: return False
    @property
    def supports_json_arrows(self) -> bool: return False
    def format_json_operation(self, column, path, operation, value, alias) -> str: raise NotImplementedError("DummyJsonOperationHandler.format_json_operation")
    def supports_json_function(self, fn) -> bool: return False


class DummyCTEHandler(CTEHandler):
    """A dummy CTE handler that allows to_sql tests to pass."""
    @property
    def is_supported(self) -> bool:
        return True

    @property
    def supports_recursive(self) -> bool:
        return True

    def format_cte(self, name, query, cols, rec, mat) -> str:
        return f"{name} AS ({query})"

    def format_with_clause(self, ctes: List[Dict[str, Any]], recursive: bool = False) -> str:
        cte_parts = [self.format_cte(c['name'], c['query'], c.get('columns'), c.get('recursive'), c.get('materialized')) for c in ctes]
        with_keyword = "WITH RECURSIVE" if recursive else "WITH"
        return f"{with_keyword} {', '.join(cte_parts)}"


class DummyReturningHandler(ReturningClauseHandler):
    """Dummy ReturningHandler that just formats a generic RETURNING clause."""
    def __init__(self, dialect: 'SQLDialectBase'):
        self._dialect = dialect

    @property
    def is_supported(self) -> bool:
        return True # For formatting purposes, we can assume it's "supported"

    def format_clause(self, columns: Optional[List[str]] = None) -> str:
        if columns:
            return f"RETURNING {', '.join(self._dialect.format_identifier(c) for c in columns)}"
        return "RETURNING *"

    def format_advanced_clause(
        self,
        columns: Optional[List[str]] = None,
        expressions: Optional[List[Dict[str, Any]]] = None, # List of dicts, not Dict[str,Any]
        aliases: Optional[Dict[str, str]] = None,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> str:
        # Based on base ReturningClauseHandler's format_advanced_clause logic
        if not self.is_supported:
            raise ReturningNotSupportedError("RETURNING clause not supported by this database")

        items = []

        if columns:
            for col in columns:
                alias = aliases.get(col) if aliases and col in aliases else None
                if alias:
                    items.append(f"{self._dialect.format_identifier(col)} AS {self._dialect.format_identifier(alias)}")
                else:
                    items.append(self._dialect.format_identifier(col))

        if expressions:
            for expr_dict in expressions:
                expr_text = expr_dict.get("expression", "")
                expr_alias = expr_dict.get("alias") # Alias is inside the dict
                if expr_alias:
                    items.append(f"{expr_text} AS {self._dialect.format_identifier(expr_alias)}")
                else:
                    items.append(expr_text)
        
        if not items:
            return "RETURNING *"

        return f"RETURNING {', '.join(items)}"

    def supports_feature(self, feature: str) -> bool:
        """Always supports 'columns' and 'expressions' for dummy."""
        return feature in {"columns", "expressions"}


class DummyDialect(SQLDialectBase):
    """
    A dummy SQL dialect for generating SQL strings without connecting to a real database.
    It uses generic SQL syntax and PostgreSQL-like identifier quoting (double quotes).
    """

    def __init__(self):
        super().__init__(version=(0, 0, 0)) # Call super().__init__ with a dummy version
        # Initialize handlers for abstract properties
        self._returning_handler = DummyReturningHandler(self)
        self._aggregate_handler = DummyAggregateHandler(self.version)
        self._json_operation_handler = DummyJsonOperationHandler()
        self._cte_handler = DummyCTEHandler()

    # --- Implement abstract methods from SQLDialectBase ---

    def format_expression(self, expr: SQLExpressionBase) -> str:
        """Formats a SQL expression."""
        return expr.format(self)

    def get_placeholder(self) -> str:
        """Returns a generic '?' parameter placeholder."""
        return '?'

    def format_string_literal(self, value: str) -> str:
        """Formats a string literal by single-quoting it and escaping internal quotes."""
        escaped_value = value.replace("'", "''")
        return f"'{escaped_value}'"

    def format_identifier(self, identifier: str) -> str:
        """Formats a SQL identifier by double-quoting it."""
        return f'"{identifier}"'

    def format_limit_offset(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Tuple[Optional[str], List[Any]]:
        """Appends standard LIMIT and OFFSET clauses."""
        clause_parts = []
        params = []
        if limit is not None:
            clause_parts.append(f"LIMIT ?")
            params.append(limit)
        if offset is not None:
            clause_parts.append(f"OFFSET ?")
            params.append(offset)
        
        if not clause_parts:
            return None, []
        return " ".join(clause_parts), params

    def get_parameter_placeholder(self, position: int) -> str:
        """Returns a generic '?' parameter placeholder, ignoring position for dummy."""
        return '?'

    def format_explain(self, sql: str, options: Optional[ExplainOptions] = None) -> str:
        """Formats an EXPLAIN statement for a dummy backend."""
        explain_clause = "EXPLAIN"
        if options:
            if options.type == ExplainType.ANALYZE: # Use options.type instead of options.analyze
                explain_clause += " ANALYZE"
            # Add other options here if desired, simplified for dummy
            if options.format != ExplainFormat.TEXT:
                 explain_clause += f" (FORMAT {options.format.value.upper()})"
        return f"{explain_clause} {sql}"

    def create_expression(self, expression: str) -> SQLExpressionBase:
        """Creates a dummy SQL expression object."""
        return DummySQLExpression(expression)

    # --- Other methods (helpers or inherited concrete methods) ---

    def get_type_mappings(self) -> Dict[str, Any]:
        """Returns a minimal set of type mappings (mostly illustrative)."""
        return {
            "INT": "INTEGER",
            "STR": "TEXT",
            "BOOL": "BOOLEAN",
            "UUID": "UUID",
            "DATETIME": "TIMESTAMP"
        }

    # Internal _format_ methods are called by SQLDialectBase.format_literal
    def _format_binary_literal(self, value: bytes) -> str:
        """Formats a binary literal (e.g., using hex representation)."""
        return f"X'{value.hex()}'"

    def _format_boolean_literal(self, value: bool) -> str:
        """Formats a boolean literal."""
        return "TRUE" if value else "FALSE"

    def _format_null_literal(self, value: Any) -> str: # SQLDialectBase.format_literal passes value
        """Formats a NULL literal."""
        return "NULL"

    def _format_list_literal(self, values: List[Any]) -> str:
        """Formats a list literal (e.g., for an IN clause)."""
        return f"({', '.join(self.format_literal(v) for v in values)})"

    def _format_json_path_literal(self, path: str) -> str:
        """Formats a JSON path literal."""
        return f"'{path}'"

    def _check_returning_compatibility(self, options: ReturningOptions) -> None:
        """Always allows RETURNING for dummy purposes."""
        pass