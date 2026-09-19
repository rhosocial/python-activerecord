# src/rhosocial/activerecord/base/ddl/selector.py
"""Dialect-aware selection of declared DDL expressions (Gates 1-2).

Gate 1 classifies each candidate against the current backend (owned / generic /
foreign); Gate 2 lets the dialect decide by rendering — a generic candidate is
open to every backend and answers "can I render it" through its capability bits.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, TYPE_CHECKING

from ...backend.dialect.exceptions import UnsupportedFeatureError
from ...backend.expression.bases import BaseExpression
from .binder import DialectBinder
from .contracts import DeclarationContract

if TYPE_CHECKING:  # pragma: no cover
    from ...backend.dialect import SQLDialectBase


class ExpressionOwnership:
    """Classifies a declared expression against the current backend.

    Ownership is derived from the module namespace (``.impl.<backend>``, the
    same convention as backend data types) unless the class declares an explicit
    ``owner_backend`` attribute. Core-namespace expressions are generic.
    """

    GENERIC = "generic"
    OWNED = "owned"
    FOREIGN = "foreign"

    MODULE_PATTERN = re.compile(r"\.impl\.([a-z0-9_]+)(?:\.|$)")

    def __init__(self, dialect: "SQLDialectBase"):
        self.backend = self.backend_slug(type(dialect).__module__)

    @classmethod
    def backend_slug(cls, module_name: str) -> Optional[str]:
        """The backend slug embedded in a module path, if any."""
        match = cls.MODULE_PATTERN.search(module_name)
        return match.group(1) if match else None

    def owner_backend(self, expression_class: type) -> Optional[str]:
        """The backend that owns an expression class, or ``None`` if generic."""
        declared = getattr(expression_class, "owner_backend", None)
        if declared is not None:
            return declared
        return self.backend_slug(expression_class.__module__)

    def classify(self, expression_class: type) -> str:
        """Classify a candidate as generic, owned, or foreign."""
        owner = self.owner_backend(expression_class)
        if owner is None:
            return self.GENERIC
        return self.OWNED if owner == self.backend else self.FOREIGN


class DialectExpressionSelector:
    """Selects and binds declared candidates through the three gates."""

    def __init__(self, dialect: "SQLDialectBase"):
        self.dialect = dialect
        self.binder = DialectBinder(dialect)
        self.ownership = ExpressionOwnership(dialect)

    def select(
        self,
        contract: DeclarationContract,
        interface: str,
        declared: Any,
    ) -> Any:
        """Select from a declaration; additive contracts return a list."""
        if contract.additive:
            return self.select_many(contract, interface, declared)
        return self.select_one(contract, interface, declared)

    def select_one(
        self,
        contract: DeclarationContract,
        interface: str,
        declared: Any,
    ) -> Optional[Any]:
        """Return the first applicable candidate (order = priority)."""
        for candidate in contract.normalize(declared):
            contract.validate(candidate, interface)
            if self.applies(candidate):
                return self.bind(candidate)
        return None

    def select_many(
        self,
        contract: DeclarationContract,
        interface: str,
        declared: Any,
    ) -> List[Any]:
        """Return every applicable candidate (in declaration order)."""
        selected: List[Any] = []
        for candidate in contract.normalize(declared):
            contract.validate(candidate, interface)
            if self.applies(candidate):
                selected.append(self.bind(candidate))
        return selected

    def bind(self, candidate: Any) -> Any:
        """Bind expressions; non-expression declarations pass through."""
        if isinstance(candidate, BaseExpression):
            return self.binder.bind(candidate)
        return candidate

    def applies(self, candidate: Any) -> bool:
        """Gate 1 + Gate 2: is the candidate renderable on this dialect?"""
        if not isinstance(candidate, BaseExpression):
            return True
        if self.ownership.classify(type(candidate)) == ExpressionOwnership.FOREIGN:
            return False
        bound = self.binder.bind(candidate)
        try:
            bound.to_sql()
        except UnsupportedFeatureError:
            return False
        return True
