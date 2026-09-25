# src/rhosocial/activerecord/ddl/selector.py
"""Dialect-aware selection and binding of declared DDL expressions.

Declarations are often supplied as a single value, an ordered list of
backend alternatives, or a lazy factory.  :class:`DialectExpressionSelector`
normalizes those forms, validates the expected declaration type, rejects
foreign backend candidates according to the selected multiplicity, and binds
the selected expressions to the active dialect.

Selection probes expression renderability by calling ``to_sql()`` and catching
``UnsupportedFeatureError``.  This is a capability check during expression
construction, not SQL execution; other rendering errors are allowed to
propagate.  The selector does not format a final statement, create a plan, or
run a database operation.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple, Type, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from .binder import DialectBinder

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class DeclarationSelectionError(ValueError):
    """Report that no declared DDL candidate is applicable.

    The exception retains both the interface name and the per-candidate
    failure details so callers can distinguish foreign ownership from a
    dialect capability failure without parsing the formatted message.
    """

    def __init__(self, interface: str, failures: List[Tuple[str, str, str]]):
        """Initialize a selection failure with structured details.

        Args:
            interface: Name of the declaration or statement interface that
                had no applicable candidate.
            failures: Ordered ``(kind, owner, reason)`` tuples describing
                each rejected candidate.

        Notes:
            The supplied failure list is retained on the exception so callers
            can inspect the same ordered details used to build its message.
        """
        self.interface = interface
        self.failures = failures
        details = "; ".join(
            f"{kind} (owner {owner}): {reason}" for kind, owner, reason in failures
        )
        super().__init__(f"{interface}(): no applicable candidate. {details}.")


class ExpressionOwnership:
    """Classify expression classes relative to the active backend dialect.

    Ownership is used to prevent a backend-specific declaration from leaking
    into another backend.  A class may declare an explicit ``owner_backend``
    attribute; otherwise its module path is inspected for the conventional
    ``.impl.<backend>`` component.  Classes without either signal are generic.

    Attributes:
        GENERIC: Classification for core or otherwise unowned classes.
        OWNED: Classification for classes owned by the active backend.
        FOREIGN: Classification for classes owned by another backend.
    """

    GENERIC = "generic"
    OWNED = "owned"
    FOREIGN = "foreign"

    MODULE_PATTERN = re.compile(r"\.impl\.([a-z0-9_]+)(?:\.|$)")

    def __init__(self, dialect: "SQLDialectBase"):
        """Create ownership information for ``dialect``.

        Args:
            dialect: The active SQL dialect whose module identifies the
                backend slug used for ownership comparisons.
        """
        self.backend = self.backend_slug(type(dialect).__module__)

    @classmethod
    def backend_slug(cls, module_name: str) -> Optional[str]:
        """Extract a backend slug from a module path.

        Args:
            module_name: Python module path to inspect, normally
                ``type(dialect).__module__`` or an expression class's
                ``__module__``.

        Returns:
            The lowercase slug captured by the ``.impl.<slug>`` convention,
            or ``None`` when the path has no such component.

        Notes:
            The regular expression is intentionally narrow: it accepts only
            lowercase letters, digits, and underscores in the backend
            component, matching the backend module naming convention.
        """
        match = cls.MODULE_PATTERN.search(module_name)
        return match.group(1) if match else None

    def owner_backend(self, expression_class: type) -> Optional[str]:
        """Return the backend slug that owns an expression class.

        Args:
            expression_class: The class whose ownership is being resolved.

        Returns:
            The explicit ``owner_backend`` value when present; otherwise the
            slug inferred from ``expression_class.__module__``; otherwise
            ``None`` for a generic class.

        Notes:
            An explicit attribute takes precedence even when it is an empty
            string, because the method checks for ``None`` rather than
            truthiness.
        """
        declared = getattr(expression_class, "owner_backend", None)
        if declared is not None:
            return declared
        return self.backend_slug(expression_class.__module__)

    def classify(self, expression_class: type) -> str:
        """Classify an expression class for the active backend.

        Args:
            expression_class: The class to classify.

        Returns:
            ``GENERIC`` when no owner can be identified, ``OWNED`` when the
            owner matches this dialect's backend slug, and ``FOREIGN``
            otherwise.

        Notes:
            A dialect whose module does not follow the ``.impl.<backend>``
            convention has no inferred slug, so unowned classes remain
            generic and explicitly owned classes are compared with ``None``.
        """
        owner = self.owner_backend(expression_class)
        if owner is None:
            return self.GENERIC
        return self.OWNED if owner == self.backend else self.FOREIGN


class DialectExpressionSelector:
    """Select declaration candidates that the active dialect can use.

    The selector combines three independent decisions: declaration shape
    validation, backend ownership, and renderability.  A foreign candidate is
    skipped for additive interfaces but makes a single-choice interface fail;
    a generic or active-backend candidate that cannot render is never silently
    discarded.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        """Create a selector and its dialect binder/ownership classifier.

        Args:
            dialect: The active SQL dialect used to bind and probe selected
                declaration expressions.
        """
        self.dialect = dialect
        self.binder = DialectBinder(dialect)
        self.ownership = ExpressionOwnership(dialect)

    @staticmethod
    def normalize(declared: Any) -> List[Any]:
        """Normalize one declaration into an ordered candidate list.

        Args:
            declared: ``None``, one candidate, or a list/tuple of candidates.

        Returns:
            An empty list for ``None``, a shallow copy of a list/tuple, or a
            one-element list for a scalar declaration.
        """
        if declared is None:
            return []
        if isinstance(declared, (list, tuple)):
            return list(declared)
        return [declared]

    def validate(
        self,
        candidate: Any,
        interface: str,
        expected_type: Optional[Type[Any]] = None,
    ) -> None:
        """Validate one candidate's declaration type.

        Args:
            candidate: Value returned by a declaration or lazy factory.
            interface: Interface name used in the error message.
            expected_type: Required type, or ``None`` when any value is valid.

        Raises:
            TypeError: If ``expected_type`` is specified and the candidate is
                not an instance of it.
        """
        if expected_type is None or isinstance(candidate, expected_type):
            return
        expected_name = getattr(expected_type, "__name__", str(expected_type))
        raise TypeError(
            f"{interface}() returned {type(candidate).__name__}; expected "
            f"{expected_name} or a subclass."
        )

    def select_one(
        self,
        interface: str,
        declared: Any,
        expected_type: Optional[Type[Any]] = None,
    ) -> Optional[Any]:
        """Return the first applicable candidate in declaration order.

        Args:
            interface: Interface name used in validation and failure details.
            declared: A scalar, list/tuple, ``None``, or lazy declaration.
            expected_type: Optional type required for every candidate.

        Returns:
            The first applicable candidate bound to the dialect, or ``None``
            when the declaration contains no candidates.

        Raises:
            DeclarationSelectionError: If every candidate is foreign or
                otherwise inapplicable.
            TypeError: If a candidate does not satisfy ``expected_type``.

        Notes:
            Foreign candidates are retained in the failure list rather than
            skipped, because a single-choice declaration has no alternative
            from which to recover.
        """
        candidates = self.normalize(declared)
        if not candidates:
            return None
        failures: List[Tuple[str, str, str]] = []
        for candidate in candidates:
            if callable(candidate):
                candidate = self.binder.bind(candidate)
            self.validate(candidate, interface, expected_type)
            applicable, classification, reason = self.applicability(candidate)
            if applicable:
                return self.bind(candidate)
            failures.append((type(candidate).__name__, self._owner_label(candidate), reason))
        raise DeclarationSelectionError(interface, failures)

    def select_many(
        self,
        interface: str,
        declared: Any,
        expected_type: Optional[Type[Any]] = None,
    ) -> List[Any]:
        """Return every applicable candidate in declaration order.

        Args:
            interface: Interface name used in validation and failure details.
            declared: A scalar, list/tuple, ``None``, or lazy declaration.
            expected_type: Optional type required for every candidate.

        Returns:
            A list containing each applicable, dialect-bound candidate in its
            original declaration order.  An empty declaration returns ``[]``.

        Raises:
            DeclarationSelectionError: If a generic or active-backend
                candidate is declared but cannot be rendered by the dialect.
            TypeError: If a candidate does not satisfy ``expected_type``.

        Notes:
            Foreign-backend candidates are skipped because additive
            declarations are explicitly intended to contain alternatives for
            multiple backends.  They are not treated as successful
            selections.
        """
        selected: List[Any] = []
        for candidate in self.normalize(declared):
            if callable(candidate):
                candidate = self.binder.bind(candidate)
            self.validate(candidate, interface, expected_type)
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
        """Bind an expression candidate while preserving scalar declarations.

        Args:
            candidate: A ``BaseExpression`` or a non-expression declaration
                value.

        Returns:
            A dialect-bound copy when ``candidate`` is a ``BaseExpression``;
            otherwise the original non-expression value unchanged.

        Notes:
            The binder's specialized paths handle nested index and constraint
            expressions.  This wrapper does not perform ownership or
            capability checks.
        """
        if isinstance(candidate, BaseExpression):
            return self.binder.bind(candidate)
        return candidate

    def applies(self, candidate: Any) -> bool:
        """Return whether a candidate is usable on the active dialect.

        Args:
            candidate: The declaration value to probe.

        Returns:
            ``True`` for applicable generic/owned declarations and for
            expressions that pass ownership and renderability checks;
            ``False`` otherwise.

        Notes:
            This convenience method discards the ownership and failure reason
            returned by :meth:`applicability`.
        """
        applicable, _, _ = self.applicability(candidate)
        return applicable

    def applicability(self, candidate: Any) -> Tuple[bool, str, str]:
        """Classify a candidate and explain whether it can be selected.

        Args:
            candidate: A declaration value to inspect.

        Returns:
            A ``(applicable, classification, reason)`` tuple.  The
            classification is ``"declared"`` for generic non-expressions,
            ``"generic"``, ``"owned"``, or ``"foreign"`` for declaration
            classes.  ``reason`` is empty when applicable and otherwise
            describes foreign ownership or an ``UnsupportedFeatureError``.

        Raises:
            Exception: Errors other than ``UnsupportedFeatureError`` raised
                while binding or rendering a candidate are propagated.

        Notes:
            Renderability is probed with ``candidate.to_sql()`` after binding.
            This may format a transient SQL representation for capability
            selection, but it never executes a statement.
        """
        classification = self.ownership.classify(type(candidate))
        if classification == ExpressionOwnership.FOREIGN:
            return False, classification, "owned by a foreign backend"
        if not isinstance(candidate, BaseExpression):
            label = "declared" if classification == ExpressionOwnership.GENERIC else classification
            return True, label, ""
        bound = self.binder.bind(candidate)
        try:
            bound.to_sql()
        except UnsupportedFeatureError as exc:
            return False, classification, f"not renderable here: {exc}"
        return True, classification, ""

    def _owner_label(self, candidate: Any) -> str:
        """Return a readable ownership label for selection errors.

        Args:
            candidate: The rejected declaration value.

        Returns:
            ``"backend '<slug>'"`` for an owned backend class, or
            ``"core (generic)"`` when no owner can be identified.
        """
        owner = self.ownership.owner_backend(type(candidate))
        return f"backend {owner!r}" if owner else "core (generic)"


__all__ = [
    "DeclarationSelectionError",
    "DialectExpressionSelector",
    "ExpressionOwnership",
]
