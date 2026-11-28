# src/rhosocial/activerecord/backend/expression_registry/registration.py
"""Collecting an owner's kinds: kind -> fully qualified class name.

An expression package declares its nodes; this module turns those declarations
into the mapping an owner publishes. It knows nothing about backends or
dialects: it is handed one importable package name and returns that package's
kinds.

    CORE_EXPRESSIONS = collect_expressions(
        "rhosocial.activerecord.backend.expression"
    )

A backend adds its own package to core's mapping:

    SQLITE_EXPRESSIONS = collect_expressions(
        "rhosocial.activerecord.backend.impl.sqlite.expression"
    )

There is no generic assembly step, no ``base=`` parameter, and no list of
backends anywhere: an owner merges the dictionaries it owns. A package that
cannot be imported yields no entries; naming a backend that is not installed
is therefore not an error.
"""

from typing import Dict, Mapping

from ..expression.bases import BaseExpression


def _declares_a_formatter(cls) -> bool:
    """Whether *cls* resolves to a concrete ``format_method``.

    Asked by definition site, not by presence on ``vars(cls)``: a base such as
    ``DeclaredValueType`` supplies one for its subclasses, and that is a real
    declaration. Only the sentinel on :class:`BaseExpression` means "none".
    """
    for klass in cls.__mro__:
        if "format_method" in vars(klass):
            return klass is not BaseExpression
    return False


def collect_expressions(package: str) -> Dict[str, str]:
    """The kinds one expression package declares, as kind -> fully qualified name.

    A class is a kind when it is concrete, declares a formatter, and opts into
    the default table. A node whose rendered SQL is caller-vouched text sets
    ``REGISTER_BY_DEFAULT`` to false: the table is what a reader resolves an
    untrusted artifact against, so admitting it would hand the artifact the
    choice of raw SQL. A caller that trusts its artifacts registers the class
    itself.

    A package may expose its expressions from a single module rather than a
    package; anything without ``__path__`` is treated as that leaf module.

    Kind collisions are collected across the whole walk before reporting: two
    same-named classes derive one kind, and no artifact could say which it
    meant.

    Args:
        package: Importable package or module name to walk.

    Returns:
        ``{kind: "module.Class"}`` for every node the package declares. A
        package that cannot be imported yields an empty mapping.
    """
    import importlib
    import pkgutil

    try:
        root = importlib.import_module(package)
    except Exception:
        return {}

    if hasattr(root, "__path__"):
        modnames = [
            name
            for _, name, _ in pkgutil.walk_packages(
                path=root.__path__, prefix=package + ".", onerror=lambda x: None
            )
        ]
    else:
        modnames = [package]

    found: Dict[str, str] = {}
    problems = []
    for modname in modnames:
        try:
            module = importlib.import_module(modname)
        except Exception:
            continue
        for attr in vars(module).values():
            if not isinstance(attr, type) or attr.__module__ != modname:
                continue
            if not issubclass(attr, BaseExpression):
                continue
            if attr is BaseExpression or getattr(attr, "__abstractmethods__", None):
                continue
            # A leading underscore is not a reason to skip: the dummy backend's
            # own nodes are named that way and they round-trip like any other.
            if not _declares_a_formatter(attr):
                continue
            if not attr.REGISTER_BY_DEFAULT:
                continue
            kind = attr.kind()
            target = f"{attr.__module__}.{attr.__qualname__}"
            existing = found.get(kind)
            if existing is not None and existing != target:
                problems.append(f"kind '{kind}' is claimed by both {existing} and {target}")
                continue
            found[kind] = target

    if problems:
        raise ValueError("; ".join(problems))
    return found


def merge_expressions(*mappings: Mapping[str, str]) -> Dict[str, str]:
    """Merge owner mappings, refusing a kind two different classes claim.

    A backend's table is core's mapping plus its own. The union is a value, so
    a collision must be stated rather than resolved by dictionary order: no
    artifact could say which class it meant.

    Raises:
        ValueError: naming both targets when two mappings claim one kind.
    """
    merged: Dict[str, str] = {}
    for mapping in mappings:
        for kind, target in mapping.items():
            existing = merged.get(kind)
            if existing is not None and existing != target:
                raise ValueError(
                    f"kind '{kind}' is claimed by both {existing} and {target}"
                )
            merged[kind] = target
    return merged
