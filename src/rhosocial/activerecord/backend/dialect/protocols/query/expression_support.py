# .../protocols/query/expression_support.py
"""Protocol for base expression rendering. Pure-format family group."""

from typing import Optional, Tuple
from rhosocial.activerecord.backend.expression import bases
from rhosocial.activerecord.backend.expression.functions import CastExpression
from rhosocial.activerecord.backend.expression.objects import QualifiedIdentifier
from rhosocial.activerecord.backend.expression.sources import Subquery
from rhosocial.activerecord.backend.expression.value_types import Identifier
from rhosocial.activerecord.backend.expression.operators import (
    ArithmeticOperation,
    BinaryExpression,
    RawSQL,
    RawSQLPredicate,
    SQLOperation,
    ConcatenationOperation,
    UnaryExpression,
)
from typing import runtime_checkable, Protocol

@runtime_checkable
class ExpressionSupport(Protocol):
    def format_identifier_expression(self, expr: Identifier) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_qualified_identifier(self, expr: QualifiedIdentifier) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_parameter_expression(self, expr: "bases.Parameter") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_cast_expression(self, expr: CastExpression) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_sql_operation(self, expr: SQLOperation) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_binary_expression(self, expr: BinaryExpression) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_concatenation_operation(
            self, expr: "ConcatenationOperation"
        ) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_unary_expression(self, expr: UnaryExpression) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_arithmetic_operation(self, expr: ArithmeticOperation) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_raw_sql(self, expr: RawSQL) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_raw_sql_predicate(self, expr: "RawSQLPredicate") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_subquery(self, expr: Subquery) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_values_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_case_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        ...  # pragma: no cover
    STRING_CONCATENATION: Optional[str]
