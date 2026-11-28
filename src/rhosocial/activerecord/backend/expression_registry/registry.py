# src/rhosocial/activerecord/backend/expression_registry/registry.py
"""The expression registry: the kind whitelist, and nothing else.

A registry maps one **kind** to the fully qualified name of the expression
class that owns it. It does not own naming (the class derives its own kind,
§4.11.1), it does not own rendering (an expression declares its own
``format_method``, §3), and it does not construct nodes — whoever defines a
kind brings its constructor, and ``{kind, params}`` builds the tree recursively.

It does three things:

- **register** — add a class under its kind, storing the class's fully
  qualified name. Registering the same target twice is a no-op; two *different*
  targets claiming one kind is an assembly-time hard failure, not a silent
  overwrite, because which class an artifact resolves to must never depend on
  registration order.
- **check** — a kind is either in the table, deliberately disabled, or absent.
  Absent means "this build cannot read it"; there is no separate "unknown
  kind" state.
- **resolve** — turn a kind from an untrusted artifact back into a class.
  Resolution imports the class named by a *registered* target. The artifact
  supplies only a key into the table, never a module path (§4.11.4).

Version differences never affect registration (the same classes are the same
kinds across every version; a version-dependent rendering decision belongs to
the formatter's ``supports`` check, not the table).

Serialization does **not** go through the registry — a node carries its kind
and parameters and encodes directly. Deserialization is the one moment a kind
has to become a class again, which is what the table is for.
"""

import importlib
from enum import Enum
from functools import lru_cache
from typing import Dict, Mapping, Optional, Set, Tuple, Type

from ..expression.bases import BaseExpression


def _fqn(expr_class: Type[BaseExpression]) -> str:
    """A class's fully qualified name, the table's stored value."""
    return f"{expr_class.__module__}.{expr_class.__qualname__}"


@lru_cache(maxsize=None)
def _load(fqn: str) -> Type[BaseExpression]:
    """Import the class a registered fully qualified name points at.

    The name comes from the table, never from an artifact (§4.11.4): an
    artifact can only name a kind, and a kind only resolves if someone
    registered that exact target.
    """
    module_name, _, qualname = fqn.rpartition(".")
    if not module_name:
        raise TypeError(f"'{fqn}' is not a fully qualified class name")
    target = importlib.import_module(module_name)
    for part in qualname.split("."):
        target = getattr(target, part)
    if not isinstance(target, type):
        raise TypeError(f"'{fqn}' does not name a class")
    return target


class RegistryReason(Enum):
    """Structured failure reasons (§5.5.4 — the reason is data, not text)."""

    KIND_NOT_REGISTERED = "kind_not_registered"
    INSTANCE_UNSUPPORTED = "instance_unsupported"
    SPEC_INVALID = "spec_invalid"
    REGISTRY_FROZEN = "registry_frozen"


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


class ExpressionRegistry:
    """The kind whitelist: ``kind`` -> expression class, and nothing else.

    The registry owns one mapping: ``kind`` to a fully qualified class name. It
    does not own naming (the class derives its own kind, §4.11.1), it does not
    own rendering (an expression declares its own ``format_method``, §3), and it
    does not construct nodes.

    It also does not *discover*. Nothing here imports an expression package or
    walks subclasses: a kind exists because someone registered it. That is what
    leaves a backend's own expressions exactly as privileged as a third-party
    plugin -- neither is found, both are registered -- and what makes selective
    assembly possible: whatever a package did not register answers
    ``kind_not_registered``.

    A registry is built, then :meth:`freeze`-d. Freezing is what makes an
    assembled table a *value*: the owner (core, a backend) publishes one shared
    instance and no caller can silently widen or narrow it for everyone else.
    Callers who need a different set start from :meth:`twin` or
    :meth:`merged` and get their own instance.
    """

    def __init__(self, kinds: Optional[Mapping[str, str]] = None) -> None:
        # The deserialization whitelist: kind -> fully qualified class name.
        # Value kinds and class kinds share one namespace; the difference is
        # only how many kinds one class answers, which resolution does not
        # care about.
        self._nodes: Dict[str, str] = dict(kinds or {})
        # Kinds that are registered but must not be read right now. Kept apart
        # from ``_nodes`` because "not registered" and "registered but off" are
        # different answers: the first is a deployment that lacks the kind, the
        # second is a deployment that has it and has switched it off.
        self._disabled: Set[str] = set()
        # Once frozen the table is a published value: mutators refuse, and a
        # caller who needs a different set builds a new registry.
        self._frozen = False

    @property
    def is_frozen(self) -> bool:
        """Whether this registry refuses further mutation."""
        return self._frozen

    def freeze(self) -> "ExpressionRegistry":
        """Refuse every future mutation, and return this registry.

        Idempotent: a frozen registry stays frozen, and freezing one twice is
        not an error. A registry is frozen when its owner publishes it, so two
        callers holding the same instance cannot change what the other reads.
        """
        self._frozen = True
        return self

    def _refuse_mutation(self, kind: str) -> None:
        """Raise if this registry is frozen, naming the kind refused."""
        if self._frozen:
            raise RegistryError(
                RegistryReason.REGISTRY_FROZEN,
                f"kind '{kind}' cannot be changed: the registry is frozen; "
                f"build a new one with merged() or ExpressionRegistry(...)",
                kind=kind,
            )

    def twin(self) -> "ExpressionRegistry":
        """An independent, mutable twin carrying the same registrations.

        The mapping is copied verbatim: a kind registered by another owner is
        not re-derived from the class behind it, so a twin carries exactly the
        owner's targets.

        The twin starts **unfrozen** even when the source is frozen: a copy is
        the workspace a caller narrows or widens before freezing its own
        published instance. Freezing the twin later does not affect the source.
        """
        twin = ExpressionRegistry()
        twin._nodes = dict(self._nodes)
        twin._disabled = set(self._disabled)
        return twin

    def copy(self) -> "ExpressionRegistry":
        """Alias of :meth:`twin`, kept for callers written before it had a name."""
        return self.twin()

    def merged(self, other: "ExpressionRegistry") -> "ExpressionRegistry":
        """A new frozen registry holding the union of both kind tables.

        Fusion is how one owner composes another owner's kinds without either
        listing the other: core's table plus a backend's table is the backend's
        table. ``other`` is not mutated, and neither is ``self``.

        A kind both sides claim with the *same* target is one kind, not a
        collision. Two different targets claiming one kind are a hard error,
        naming both targets, because no artifact could say which one it meant.

        Args:
            other: The registry to fuse into this one.

        Returns:
            A frozen registry holding every kind either side registered.

        Raises:
            RegistryError: ``spec_invalid`` when both sides claim a kind with
                different classes.
            TypeError: when *other* is not an :class:`ExpressionRegistry`.
        """
        if not isinstance(other, ExpressionRegistry):
            raise TypeError(f"merged() takes an ExpressionRegistry, got {type(other).__name__}")
        fused = self.twin()
        conflicts = []
        for kind in sorted(other._nodes):
            target = other._nodes[kind]
            existing = fused._nodes.get(kind)
            if existing is not None and existing != target:
                conflicts.append((kind, existing, target))
                continue
            fused._nodes[kind] = target
        fused._disabled |= other._disabled
        if conflicts:
            detail = "; ".join(
                f"kind '{k}' is claimed by both {a} and {b}" for k, a, b in conflicts
            )
            raise RegistryError(RegistryReason.SPEC_INVALID, detail)
        fused.freeze()
        return fused

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

        Raises:
            RegistryError: ``registry_frozen`` when the registry has been
                frozen, naming the class's kind.
        """
        kind = expr_class.kind()
        target = _fqn(expr_class)
        self._refuse_mutation(kind)
        existing = self._nodes.get(kind)
        if existing == target:
            return kind
        if existing is not None:
            raise RegistryError(
                RegistryReason.SPEC_INVALID,
                f"kind '{kind}' is claimed by both "
                f"{existing} and {target}; the kind "
                f"whitelist must resolve each kind to exactly one class",
                kind=kind,
            )
        self._nodes[kind] = target
        return kind

    def resolve_node(self, kind: str) -> Type[BaseExpression]:
        """Resolve a kind to its expression class — the whitelist lookup.

        Raises:
            RegistryError: ``kind_not_registered``, naming the kind. There is
                no "unknown kind" state distinct from "not registered": a kind
                that is not in the whitelist is a kind this build cannot read.
        """
        try:
            target = self._nodes[kind]
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
        try:
            return _load(target)
        except Exception as exc:
            raise RegistryError(
                RegistryReason.SPEC_INVALID,
                f"kind '{kind}' is registered to {target}, which cannot be "
                f"imported: {exc}",
                kind=kind,
            ) from exc

    def unregister_node(self, kind: str) -> None:
        """Drop a kind from the whitelist.

        For selective assembly *after* the fact: a deployment that wants no DDL
        can register everything and then remove the statement kinds it refuses
        to accept. Dropping a kind nobody registered is a hard error -- it means
        the caller believes something is there that is not.
        """
        self._refuse_mutation(kind)
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
        support switch needs. An unregistered kind is absent from the build;
        a disabled one is present and declined.
        """
        self._refuse_mutation(kind)
        if kind not in self._nodes:
            raise RegistryError(
                RegistryReason.KIND_NOT_REGISTERED,
                f"kind '{kind}' is not registered, so it cannot be disabled",
                kind=kind,
            )
        self._disabled.add(kind)

    def enable(self, kind: str) -> None:
        """Re-allow a kind that :meth:`disable` switched off."""
        self._refuse_mutation(kind)
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


#: There is deliberately **no** module-level registry instance here.
#:
#: An earlier version declared one, and it was empty for the life of the
#: process: nothing ever assembled into it, because *which* expressions the
#: framework ships is the framework's decision, not this module's (§7 -- the
#: registry does not own implementations, so it must not import expression
#: packages to learn what they contain).
#:
#: The name was the real damage: it read as "the one table everything is in",
#: when every owner maintains its own. :func:`.core_registry.core_registry`
#: builds and caches core's; each backend publishes its own table as a constant
#: in ``impl.<name>.expression_registry`` -- core's kinds plus its own, never a
#: sibling's. A dialect takes no part in it. There is no table shared by all
#: owners, and no alias standing in for one. Anyone who reached for the object
#: here got a table that admits nothing and refused every artifact by name, with
#: nothing to say why.
#:
#: Build your own -- :class:`ExpressionRegistry` starts empty, which is what makes
#: a narrow table safe to hand a caller.
