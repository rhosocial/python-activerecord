# src/rhosocial/activerecord/base/ddl/selector.py
"""Dialect-aware selection of declared DDL expressions (Gates 1-2).

Gate 1 classifies each candidate against the current backend (owned / generic /
foreign); Gate 2 lets the dialect decide by rendering — a generic candidate is
open to every backend and answers "can I render it" through its capability bits.

Selection is **never silent** (§5.6): single-value interfaces raise when a
non-empty declaration has no applicable candidate; additive interfaces skip
foreign-backend candidates but raise when an owned/generic candidate is not
renderable.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from ...backend.dialect.exceptions import UnsupportedFeatureError
from ...backend.expression.bases import BaseExpression
from .binder import DialectBinder
from .contracts import DeclarationContract

if TYPE_CHECKING:  # pragma: no cover
    from ...backend.dialect import SQLDialectBase


class DeclarationSelectionError(ValueError):
    """Raised when a declared candidate cannot be selected (§5.6).

    The message names the interface, the candidate type, its owning backend
    and why it does not apply — a declaration that names something is never
    silently dropped.
    """

    def __init__(self, interface: str, failures: List[Tuple[str, str, str]]):
        self.interface = interface
        self.failures = failures
        details = "; ".join(f"{kind} (owner {owner}): {reason}" for kind, owner, reason in failures)
        super().__init__(
            f"{interface}(): no applicable candidate. {details}."
        )


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
        """Return the first applicable candidate (order = priority).

        An empty declaration yields ``None``; a **non-empty** declaration
        with no applicable candidate raises :class:`DeclarationSelectionError`
        — single-value declarations are never silently dropped (§5.6).
        """
        candidates = contract.normalize(declared)
        if not candidates:
            return None
        failures: List[Tuple[str, str, str]] = []
        for candidate in candidates:
            contract.validate(candidate, interface)
            applicable, classification, reason = self.applicability(candidate)
            if applicable:
                return self.bind(candidate)
            failures.append((type(candidate).__name__, self._owner_label(candidate), reason))
        raise DeclarationSelectionError(interface, failures)

    def select_many(
        self,
        contract: DeclarationContract,
        interface: str,
        declared: Any,
    ) -> List[Any]:
        """Return every applicable candidate (in declaration order).

        Foreign-backend candidates are skipped (multi-backend candidate lists
        are normal); an owned/generic candidate this backend cannot render
        raises :class:`DeclarationSelectionError` (§5.6).
        """
        selected: List[Any] = []
        for candidate in contract.normalize(declared):
            contract.validate(candidate, interface)
            applicable, classification, reason = self.applicability(candidate)
            if applicable:
                selected.append(self.bind(candidate))
                continue
            if classification == ExpressionOwnership.FOREIGN:
                continue
            raise DeclarationSelectionError(
                interface,
                [(type(candidate).__name__, self._owner_label(candidate), reason)],
            )
        return selected

    def bind(self, candidate: Any) -> Any:
        """Bind expressions; non-expression declarations pass through."""
        if isinstance(candidate, BaseExpression):
            return self.binder.bind(candidate)
        return candidate

    def applies(self, candidate: Any) -> bool:
        """Gate 1 + Gate 2: is the candidate renderable on this dialect?"""
        applicable, _, _ = self.applicability(candidate)
        return applicable

    def applicability(self, candidate: Any) -> Tuple[bool, str, str]:
        """Classify a candidate and explain its applicability.

        Returns ``(applicable, classification, reason)``: ``reason`` is empty
        when applicable, else names the owning backend and why the candidate
        does not apply (foreign ownership, or not renderable on this dialect).
        """
        if not isinstance(candidate, BaseExpression):
            return True, "declared", ""
        classification = self.ownership.classify(type(candidate))
        if classification == ExpressionOwnership.FOREIGN:
            return False, classification, "owned by a foreign backend"
        bound = self.binder.bind(candidate)
        try:
            bound.to_sql()
        except UnsupportedFeatureError as exc:
            return False, classification, f"not renderable here: {exc}"
        return True, classification, ""

    def _owner_label(self, candidate: Any) -> str:
        """A readable owner label for error messages."""
        owner = self.ownership.owner_backend(type(candidate))
        return f"backend {owner!r}" if owner else "core (generic)"
