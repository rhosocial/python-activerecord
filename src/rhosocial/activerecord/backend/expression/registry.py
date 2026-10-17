# src/rhosocial/activerecord/backend/expression/registry.py
"""The expression registry: registration, checking and dispatch — nothing else.

This is the registry the architecture rules describe (§7 of the
expression-dialect rules, §5.5 of the spec): a dialect exposes its formatting
capability for an expression **kind** by registering a render function here,
and callers dispatch through it. The registry does three things and nothing
more:

- **登记 (register)** — an entry is ``kind`` + ``render(node)`` + an optional
  ``supports(node)`` predicate, registered for one dialect. The functions
  belong to the dialect package; the registry only indexes them. It does not
  own implementations, does not judge names, and does not construct nodes —
  whoever defines a kind brings its constructor, and ``{kind, params}``
  builds the tree recursively.
- **检查 (check)** — a boolean answer to "would this dialect render this
  kind?". Unregistered means *not supported*: there is no separate "unknown
  kind" state.
- **调用 (invoke)** — dispatch to the registered render function, failing with
  one error class whose ``reason`` field is data:
  ``kind_not_registered`` (the message always names the kind and the
  dialect — it carries both "this dialect does not support it" and "this
  assembly only loaded part of the functionality"), ``instance_unsupported``
  (registered, but this instance — version / session state — declines), and
  ``spec_invalid`` (the supports predicate said yes but the formatter refused:
  the predicate is an optimisation, never a guarantee, so the formatter's
  refusal wins as a fast, structured failure).

Version differences never affect registration (the same dialect class
registers the same kind set across all its versions; the difference lives in
``supports`` and inside the formatters). Registering the same
``(dialect, kind)`` twice is an assembly-time hard failure, not a silent
overwrite: which render wins must never depend on assembly order.

Serialization does **not** go through the registry — a node carries its kind
and parameters and encodes directly. Deserialization resolves kinds through
the registry (currently still via class FQNs; the kind whitelist arrives with
the bare-node rewrite).
"""

from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple, Type

from .bases import BaseExpression


class RegistryReason(Enum):
    """Structured failure reasons (§5.5.4 — the reason is data, not text)."""

    KIND_NOT_REGISTERED = "kind_not_registered"
    INSTANCE_UNSUPPORTED = "instance_unsupported"
    SPEC_INVALID = "spec_invalid"


class RegistryError(Exception):
    """The one registry failure class; read ``reason``, don't parse messages.

    Attributes:
        reason: A :class:`RegistryReason` naming the failure class.
        dialect: The dialect name the failure is about (may be ``None`` when
            the failure is not dialect-specific).
        kind: The expression kind the failure is about (may be ``None``).
    """

    def __init__(
        self,
        reason: RegistryReason,
        message: str,
        *,
        dialect: Optional[str] = None,
        kind: Optional[str] = None,
    ):
        super().__init__(message)
        self.reason = reason
        self.dialect = dialect
        self.kind = kind


def kind_of(expr_class: Type[BaseExpression]) -> str:
    """Derive the kind of an expression class from its name (§4.9.2).

    The kind is the class name's snake_case form; runs of consecutive
    capitals count as one word (``JSONValue`` → ``json_value``). This is the
    same mechanical derivation every language port uses, so a kind never has
    to be stored on the node.
    """
    import re

    name = expr_class.__name__
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name)
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    return "_".join(name.lower().split())


class _Registration:
    """One (dialect, kind) entry: the render function plus its predicate."""

    __slots__ = ("render", "supports")

    def __init__(
        self,
        render: Callable[[BaseExpression], Tuple[str, tuple]],
        supports: Optional[Callable[[BaseExpression], bool]],
    ):
        self.render = render
        self.supports = supports


class ExpressionRegistry:
    """Index of ``(dialect, kind)`` → render function."""

    def __init__(self) -> None:
        # Keyed by (dialect class, kind): a dialect's formatting
        # implementations belong to the class, and every instance of it
        # dispatches through the same table — version differences live in
        # ``supports``, never in the registration set.
        self._entries: Dict[Tuple[type, str], _Registration] = {}

    def register(
        self,
        dialect: Any,
        kind: str,
        render: Callable[[BaseExpression], Tuple[str, tuple]],
        supports: Optional[Callable[[BaseExpression], bool]] = None,
    ) -> None:
        """Register a render function for one ``(dialect, kind)`` pair.

        Args:
            dialect: The dialect (instance or class) whose package provides
                ``render``; its class is the registration key.
            kind: The expression kind this render function handles.
            render: The formatting function. It receives the node and
                returns ``(sql, params)``.
            supports: Optional per-instance predicate. Version differences
                affect this predicate only — never the registration.

        Raises:
            RegistryError: The same ``(dialect, kind)`` is already
                registered — an assembly-time hard failure, because a silent
                overwrite would make the winning render depend on assembly
                order.
        """
        dialect_class = dialect if isinstance(dialect, type) else type(dialect)
        key = (dialect_class, kind)
        if key in self._entries:
            raise RegistryError(
                RegistryReason.SPEC_INVALID,
                f"the '{kind}' kind is already registered for dialect "
                f"'{dialect_class.__name__}'; registering it twice would make "
                f"the winning render depend on assembly order",
                dialect=dialect_class.__name__,
                kind=kind,
            )
        self._entries[key] = _Registration(render, supports)

    def check(self, dialect: Any, kind: str, node: Optional[BaseExpression] = None) -> bool:
        """Would this dialect render this kind (for this node)?

        Unregistered means not supported — there is no third "unknown kind"
        state. A registered kind with a ``supports`` predicate answers
        ``False`` when the predicate declines the instance.
        """
        dialect_class = dialect if isinstance(dialect, type) else type(dialect)
        entry = self._entries.get((dialect_class, kind))
        if entry is None:
            return False
        if entry.supports is None or node is None:
            return True
        return bool(entry.supports(node))

    def invoke(self, dialect: Any, node: BaseExpression) -> Tuple[str, tuple]:
        """Dispatch a node to its dialect's render function.

        Returns:
            The ``(sql, params)`` pair the render function produced.

        Raises:
            RegistryError: With ``reason`` naming the failure —
                ``kind_not_registered`` (message names the kind and the
                dialect), ``instance_unsupported``, or ``spec_invalid`` when
                a render that passed its predicate still refused.
        """
        dialect_class = dialect if isinstance(dialect, type) else type(dialect)
        kind = kind_of(type(node))
        entry = self._entries.get((dialect_class, kind))
        if entry is None:
            raise RegistryError(
                RegistryReason.KIND_NOT_REGISTERED,
                f"dialect '{dialect_class.__name__}' has no registered render "
                f"function for kind '{kind}'",
                dialect=dialect_class.__name__,
                kind=kind,
            )
        if entry.supports is not None and not entry.supports(node):
            raise RegistryError(
                RegistryReason.INSTANCE_UNSUPPORTED,
                f"dialect '{dialect_class.__name__}' registers '{kind}' but "
                f"this instance does not support it (version or session "
                f"state); a different dialect instance or target may succeed",
                dialect=dialect_class.__name__,
                kind=kind,
            )
        try:
            rendered = entry.render(node)
        except Exception as exc:
            # The predicate is an optimisation, not a guarantee: a render
            # that passed `supports` and still refused is a spec violation,
            # reported as such (fast failure, structured reason).
            raise RegistryError(
                RegistryReason.SPEC_INVALID,
                f"the render function for kind '{kind}' refused a node that "
                f"passed its supports predicate on dialect "
                f"'{dialect_class.__name__}': {exc}",
                dialect=dialect_class.__name__,
                kind=kind,
            ) from exc
        if not (
            isinstance(rendered, tuple)
            and len(rendered) == 2
            and isinstance(rendered[0], str)
            and (rendered[1] is None or isinstance(rendered[1], tuple))
        ):
            raise RegistryError(
                RegistryReason.SPEC_INVALID,
                f"the render function for kind '{kind}' on dialect "
                f"'{dialect_class.__name__}' returned "
                f"{type(rendered).__name__}, expected (sql, params)",
                dialect=dialect_class.__name__,
                kind=kind,
            )
        return rendered

    def supported_kinds(self, dialect: Any) -> Tuple[str, ...]:
        """The kinds registered for this dialect class, sorted."""
        dialect_class = dialect if isinstance(dialect, type) else type(dialect)
        return tuple(sorted(k for (d, k) in self._entries if d is dialect_class))


#: The process-level registry dialect packages assemble themselves into.
#: Selective assembly is normal: whatever a package did not register simply
#: answers ``kind_not_registered``.
default_registry = ExpressionRegistry()
