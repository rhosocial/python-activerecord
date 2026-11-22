# src/rhosocial/activerecord/backend/dialect/protocols/query/dml_support.py
"""Protocol for base DML statement rendering. Pure-format family group."""

from typing import runtime_checkable, Protocol, Tuple, List, Any

@runtime_checkable
class DMLSupport(Protocol):
    def format_insert_statement(self, expr: "InsertStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_insert_values_source(self, expr: "ValuesSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_insert_select_source(self, expr: "SelectSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_insert_default_values_source(self, expr: "DefaultValuesSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_on_conflict_clauses(self, expr: "InsertStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_update_statement(self, expr: "UpdateStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_delete_statement(self, expr: "DeleteStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover
