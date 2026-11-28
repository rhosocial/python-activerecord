# src/rhosocial/activerecord/backend/dialect/protocols/family/PredicateSupport.py
"""Protocol mirror of PredicateMixin (family-level feature group). Members/order/signatures identical."""

from typing import TYPE_CHECKING, Any, List, Tuple
from rhosocial.activerecord.backend.expression.functions import (
    AllPredicate,
    AnyPredicate,
    ExistsPredicate,
)
from rhosocial.activerecord.backend.expression.predicates import (
    BetweenPredicate,
    ComparisonPredicate,
    DistinctFromPredicate,
    InPredicate,
    IsBooleanPredicate,
    IsNullPredicate,
    LikePredicate,
    LogicalPredicate,
)
from typing import runtime_checkable, Protocol


@runtime_checkable
class PredicateSupport(Protocol):
    def format_comparison_predicate(self, expr: ComparisonPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_logical_predicate(self, expr: LogicalPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_in_predicate(self, expr: InPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_between_predicate(self, expr: BetweenPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_is_null_predicate(self, expr: IsNullPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_distinct_from_predicate(self, expr: DistinctFromPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_is_boolean_predicate(self, expr: IsBooleanPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_exists_predicate(self, expr: ExistsPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_any_predicate(self, expr: AnyPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_all_predicate(self, expr: AllPredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_like_predicate(self, expr: LikePredicate) -> Tuple[str, tuple]:
        ...  # pragma: no cover
