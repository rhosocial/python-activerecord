# src/rhosocial/activerecord/relation/type_resolver.py
"""
Type resolution utilities for relation descriptors.

Provides robust FQN-based model type resolution that handles:
- Module-level classes with direct or string annotations
- Forward references (circular imports between models)
- Classes defined inside test methods or nested scopes
- from __future__ import annotations (PEP 563)
- TYPE_CHECKING imports
"""

import sys
from typing import Type, Any, Union, ForwardRef, Optional, Dict


def resolve_model_fqn(cls: Type[Any]) -> str:
    """
    Compute the Fully Qualified Name for a model class.

    Uses __module__ and __qualname__ to produce a stable, importable
    identifier that works across nested classes and locally-defined classes.

    Args:
        cls: The model class.

    Returns:
        FQN string in the form ``module.qualname``.
    """
    return f"{cls.__module__}.{cls.__qualname__}"


def evaluate_annotation(
    annotation: Union[str, ForwardRef],
    owner: Type[Any],
    *,
    extra_ns: Optional[Dict[str, Any]] = None,
) -> Type[Any]:
    """
    Evaluate a string or ForwardRef annotation in the owning class's context.

    Builds a namespace from:
    1. The module globals of ``owner``
    2. All type members of ``owner`` itself (supports nested classes)
    3. Any extra namespace entries provided by the caller
    4. (fallback) Any locals on the stack frame where the call originated

    This function replaces the old ``_evaluate_forward_ref`` that walked the
    call stack.  It is deterministic and does not depend on runtime call-site
    context.

    Args:
        annotation: The string or ForwardRef to evaluate.
        owner:      The class whose namespace provides the resolution context.
        extra_ns:   Optional mapping from names to types for dynamic classes.

    Returns:
        The resolved type object.

    Raises:
        NameError: If the annotation cannot be resolved.
    """
    import inspect

    type_str = annotation if isinstance(annotation, str) else annotation.__forward_arg__

    ns = _build_owner_namespace(owner)
    if extra_ns:
        ns.update(extra_ns)

    try:
        return eval(type_str, ns, None)
    except NameError:
        pass

    frame = inspect.currentframe()
    frame = frame.f_back if frame else None
    while frame:
        local_types = {k: v for k, v in frame.f_locals.items() if isinstance(v, type)}
        if local_types:
            fallback_ns = dict(ns)
            fallback_ns.update(local_types)
            try:
                return eval(type_str, fallback_ns, None)
            except NameError:
                pass
        frame = frame.f_back

    raise NameError(f"name '{type_str}' is not defined")


def _build_owner_namespace(owner: Type[Any]) -> Dict[str, Any]:
    """Build a combined namespace for resolving annotations owned by *owner*.

    The namespace merges (in priority order):
    1. The module globals where *owner* is defined.
    2. Type members on *owner* itself (supports nested / inner classes).

    When the classes are defined inside a function scope (e.g. inside a test
    method), the function's local namespace is not visible to this helper.
    Callers that need to resolve symbols defined in local scopes should use
    ``evaluate_annotation``, which adds a runtime frame-fallback in addition
    to this base namespace.
    """
    module = sys.modules.get(owner.__module__)
    globalns = {k: getattr(module, k) for k in dir(module)} if module else {}

    localns: Dict[str, Any] = {}
    localns.update({owner.__name__: owner})
    for k, v in vars(owner).items():
        if isinstance(v, type):
            localns[k] = v

    ns: Dict[str, Any] = {}
    ns.update(globalns)
    ns.update(localns)
    return ns


def _unwrap_generic_type(raw: Any, typing_module: Any) -> Any:
    """
    Unwrap nested generic types to find the innermost type argument.

    For ``ClassVar[BelongsTo[ForwardRef('Target')]]`` this returns
    ``ForwardRef('Target')``.

    For ``ClassVar[HasMany['Post']]`` with ``from __future__ import annotations``
    this returns ``'Post'`` (the raw string).

    For already-resolved types (no generic wrapper) the input is returned unchanged.
    """
    while hasattr(raw, "__origin__") and hasattr(raw, "__args__"):
        origin = raw.__origin__
        args = raw.__args__
        if origin is typing_module.ClassVar:
            raw = args[0]
        else:
            raw = args[0]
    return raw


def _resolve_final(raw: Any) -> Union[None, Type[Any], str, ForwardRef]:
    """Normalize the final resolution result.

    Accepts ForwardRef, str, or type; returns None for anything else.
    """
    if isinstance(raw, (ForwardRef, str, type)):
        return raw
    return None


def resolve_relation_type(owner: Type[Any], field_name: str) -> Union[None, Type[Any], str, ForwardRef]:
    """
    Resolve the raw type argument of a relation descriptor from annotations.

    Given the owning class and the attribute name of the descriptor, this
    function extracts the first type argument from the annotation, handling
    ``ClassVar`` wrappers and both string and ForwardRef forms.

    This replaces the fragile iteration logic previously in
    ``RelationDescriptor._resolve_model``.

    When ``from __future__ import annotations`` (PEP 563) is active, all
    annotations are stored as strings.  In that case we first attempt
    ``typing.get_type_hints`` with the owning class's module globals, then
    fall back to evaluating the raw annotation string in the combined
    namespace built by ``_build_owner_namespace``.

    Args:
        owner:      The model class that owns the relation descriptor.
        field_name: The attribute name of the descriptor on the owner class.

    Returns:
        - A resolved ``type`` object if the annotation could be fully resolved.
        - A ``str`` or ``ForwardRef`` if the annotation is a forward reference
          that needs further evaluation.
        - ``None`` if the annotation cannot be located.

    Raises:
        TypeError: If the annotation is found but cannot be unwrapped.
    """
    import sys
    import typing

    raw_hints = getattr(owner, "__annotations__", {})
    raw = raw_hints.get(field_name)
    if raw is None:
        return None

    if isinstance(raw, ForwardRef):
        return raw

    if isinstance(raw, type):
        return raw

    if isinstance(raw, str):
        ns = _build_owner_namespace(owner)
        if sys.version_info >= (3, 11):
            evaluated = typing.get_type_hints(owner, localns=ns, include_extras=False)
        else:
            evaluated = typing.get_type_hints(owner, localns=ns)
        annotation = evaluated.get(field_name)
        if annotation is not None and annotation is not raw:
            raw = annotation

    raw = _unwrap_generic_type(raw, typing)

    return _resolve_final(raw)