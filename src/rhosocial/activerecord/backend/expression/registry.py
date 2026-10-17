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
from typing import Dict, Optional, Set, Tuple, Type

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
    """The kind of an expression class, delegated to the class itself.

    The registry does not own naming (§7: "it does not judge names"). How a
    kind is derived belongs to the expression class — see
    :meth:`BaseExpression.kind` — and a backend owns the reserved tokens its own
    compound identifier needs. This function exists only as the registry's
    access path to that derivation, so callers holding a class do not have to
    remember which object owns it.
    """
    return expr_class.kind()


class ExpressionRegistry:
    """The kind whitelist: ``kind`` -> expression class, and nothing else.

    The registry owns one mapping. It does not own naming (the class derives its
    own kind, §4.11.1), it does not own rendering (an expression declares its
    own ``format_method``, §3), and it does not construct nodes.

    It also does not *discover*. Nothing here imports an expression package or
    walks subclasses: a kind exists because someone registered it. That is what
    leaves a backend's own expressions exactly as privileged as a third-party
    plugin -- neither is found, both are registered -- and what makes selective
    assembly possible: whatever a package did not register answers
    ``kind_not_registered``.
    """

    def __init__(self) -> None:
        # The three deserialization whitelists. See the node-table section
        # below for why there are three and not one.
        self._nodes: Dict[str, Type[BaseExpression]] = {}
        self._enums: Dict[str, Type] = {}
        self._dataclasses: Dict[str, Type] = {}
        # Kinds that are registered but must not be read right now. Kept apart
        # from ``_nodes`` because "not registered" and "registered but off" are
        # different answers: the first is a deployment that lacks the kind, the
        # second is a deployment that has it and has switched it off.
        self._disabled: Set[str] = set()

    # ------------------------------------------------------------------
    # The node table: the kind whitelist deserialization resolves through.
    #
    # Serialization never consults it — a node carries its own identity.
    # Deserialization consults it and nothing else: the three tables below are
    # whitelists, not an import mechanism. Resolution is a dict lookup over
    # classes registered up front, never an ``importlib`` call driven by a
    # name read out of an artifact (§4.11.4 forbids the latter outright).
    #
    # Expression classes, enums and dataclasses are kept apart on purpose.
    # They are three different shapes with three different contracts: only
    # expression classes carry a kind and recurse into nested nodes; enums are
    # finite value sets; dataclasses are structural records. Folding them into
    # one table would let an artifact name any of the three where the other
    # belongs, which is precisely what the whitelist is there to prevent.
    # ------------------------------------------------------------------

    def register_node(self, expr_class: Type[BaseExpression]) -> str:
        """Add one expression class to the kind whitelist.

        The kind is derived from the class name (§4.11.1) rather than stored,
        so the class name is the only source of identity and the two can never
        drift apart. Registering the same class twice is a no-op; two *different*
        classes claiming the same kind is a hard error — which class an
        artifact resolves to must not depend on registration order.
        """
        kind = kind_of(expr_class)
        existing = self._nodes.get(kind)
        if existing is expr_class:
            return kind
        if existing is not None:
            raise RegistryError(
                RegistryReason.SPEC_INVALID,
                f"kind '{kind}' is claimed by both "
                f"{existing.__module__}.{existing.__name__} and "
                f"{expr_class.__module__}.{expr_class.__name__}; the kind "
                f"whitelist must resolve each kind to exactly one class",
                kind=kind,
            )
        self._nodes[kind] = expr_class
        return kind

    def resolve_node(self, kind: str) -> Type[BaseExpression]:
        """Resolve a kind to its expression class — the whitelist lookup.

        Raises:
            RegistryError: ``kind_not_registered``, naming the kind. There is
                no "unknown kind" state distinct from "not registered": a kind
                that is not in the whitelist is a kind this build cannot read.
        """
        try:
            expr_class = self._nodes[kind]
        except KeyError:
            raise RegistryError(
                RegistryReason.KIND_NOT_REGISTERED,
                f"kind '{kind}' is not in the kind whitelist "
                f"({len(self._nodes)} kinds registered); artifacts may only "
                f"name a registered kind",
                kind=kind,
            ) from None
        if kind in self._disabled:
            raise RegistryError(
                RegistryReason.INSTANCE_UNSUPPORTED,
                f"kind '{kind}' is registered but disabled in this registry; "
                f"the build knows the kind and declines to read it",
                kind=kind,
            )
        return expr_class

    def unregister_node(self, kind: str) -> None:
        """Drop a kind from the whitelist.

        For selective assembly *after* the fact: a deployment that wants no DDL
        can register everything and then remove the statement kinds it refuses
        to accept. Dropping a kind nobody registered is a hard error -- it means
        the caller believes something is there that is not.
        """
        if kind not in self._nodes:
            raise RegistryError(
                RegistryReason.KIND_NOT_REGISTERED,
                f"kind '{kind}' is not registered, so it cannot be unregistered",
                kind=kind,
            )
        del self._nodes[kind]
        self._disabled.discard(kind)

    def disable(self, kind: str) -> None:
        """Refuse a registered kind without forgetting it.

        Different from :meth:`unregister_node`: the kind stays in
        :meth:`node_kinds` and can be re-enabled, which is what a per-request
        capability switch needs. An unregistered kind is absent from the build;
        a disabled one is present and declined.
        """
        if kind not in self._nodes:
            raise RegistryError(
                RegistryReason.KIND_NOT_REGISTERED,
                f"kind '{kind}' is not registered, so it cannot be disabled",
                kind=kind,
            )
        self._disabled.add(kind)

    def enable(self, kind: str) -> None:
        """Re-allow a kind that :meth:`disable` switched off."""
        if kind not in self._nodes:
            raise RegistryError(
                RegistryReason.KIND_NOT_REGISTERED,
                f"kind '{kind}' is not registered, so it cannot be enabled",
                kind=kind,
            )
        self._disabled.discard(kind)

    def node_kinds(self) -> Tuple[str, ...]:
        """The whole kind whitelist, sorted — the enumerable contract list.

        Includes disabled kinds: the whitelist is what this build *knows*, and
        a disabled kind is known. Use :meth:`is_enabled` to ask whether it may
        be read right now.
        """
        return tuple(sorted(self._nodes))

    def is_enabled(self, kind: str) -> bool:
        """Whether *kind* is registered and not switched off."""
        return kind in self._nodes and kind not in self._disabled

    def register_enum(self, enum_class: Type) -> None:
        """Add an enum class to the whitelist, keyed by its short name."""
        name = enum_class.__name__
        existing = self._enums.get(name)
        if existing is enum_class:
            return
        if existing is not None:
            raise RegistryError(
                RegistryReason.SPEC_INVALID,
                f"enum '{name}' is claimed by both {existing.__module__} and "
                f"{enum_class.__module__}; enum names must be unique in the "
                f"whitelist",
            )
        self._enums[name] = enum_class

    def resolve_enum(self, name: str) -> Type:
        """Resolve an enum short name to its class, or fail naming it."""
        try:
            return self._enums[name]
        except KeyError:
            raise RegistryError(
                RegistryReason.KIND_NOT_REGISTERED,
                f"enum '{name}' is not in the enum whitelist",
                kind=name,
            ) from None

    def register_dataclass(self, dataclass_type: Type) -> None:
        """Add a dataclass to the whitelist, keyed by its short name."""
        name = dataclass_type.__name__
        existing = self._dataclasses.get(name)
        if existing is dataclass_type:
            return
        if existing is not None:
            raise RegistryError(
                RegistryReason.SPEC_INVALID,
                f"dataclass '{name}' is claimed by both "
                f"{existing.__module__} and {dataclass_type.__module__}; "
                f"dataclass names must be unique in the whitelist",
            )
        self._dataclasses[name] = dataclass_type

    def resolve_dataclass(self, name: str) -> Type:
        """Resolve a dataclass short name to its type, or fail naming it."""
        try:
            return self._dataclasses[name]
        except KeyError:
            raise RegistryError(
                RegistryReason.KIND_NOT_REGISTERED,
                f"dataclass '{name}' is not in the dataclass whitelist",
                kind=name,
            ) from None


#: The process-level registry dialect packages assemble themselves into.
#: Selective assembly is normal: whatever a package did not register simply
#: answers ``kind_not_registered``.
default_registry = ExpressionRegistry()
