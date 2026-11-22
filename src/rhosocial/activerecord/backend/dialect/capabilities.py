# src/rhosocial/activerecord/backend/dialect/capabilities.py
"""Shared capability / suggestion reporting for CLI ``info`` commands.

Each backend's ``cli/info.py`` used to carry a private copy of the protocol
support matrix logic. This module centralizes it so a backend only supplies:
its protocol family groups, its dialect-specific group names, the argument
sets for parameterised probes, its backend protocol module, and (optionally)
its server-variable provider.

Two independent axes are reported:
  * support  -- does the dialect answer the probe (isinstance / call result)
  * origin   -- where the capability comes from:
        reuse       core defines it and the core class wins in the MRO
        override    core defines it but a backend class wins in the MRO
        proprietary no core definition; a backend class owns it
"""
from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional

from typing import Protocol

CORE_DIALECT_MODULE = "rhosocial.activerecord.backend.dialect"
IMPL_MARK = ".backend.impl."


# ---------------------------------------------------------------------------
# protocol discovery
# ---------------------------------------------------------------------------
def iter_protocols(pkg: Any, name_filter=None) -> List[type]:
    """All Protocol classes re-exported by *pkg* (deduplicated)."""
    out = []
    seen = set()
    for _, obj in vars(pkg).items():
        if not inspect.isclass(obj) or obj is Protocol:
            continue
        if Protocol not in getattr(obj, "__mro__", ()):
            continue
        if name_filter is not None and not name_filter(obj.__name__):
            continue
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        out.append(obj)
    return out


def suggestion_protocols() -> List[type]:
    """The ``*SuggestionSupport`` protocols."""
    from ..suggestion import protocols as suggestion_protocols_pkg
    return iter_protocols(suggestion_protocols_pkg, lambda n: n.endswith("SuggestionSupport"))


# ---------------------------------------------------------------------------
# origin classification (method level)
# ---------------------------------------------------------------------------
def _is_real_implementation(cls: type) -> bool:
    """Protocol bodies are ``...``; skip them when looking for implementors."""
    return Protocol not in getattr(cls, "__mro__", ())


def _owner_of(cls: type, method_name: str) -> Optional[type]:
    for base in cls.__mro__:
        if method_name in base.__dict__ and _is_real_implementation(base):
            return base
    return None


def _origin_of(cls: type) -> str:
    mod = getattr(cls, "__module__", "") or ""
    if mod.startswith(CORE_DIALECT_MODULE):
        return "core"
    if IMPL_MARK in mod:
        return "backend"
    return "other"


def classify_origin(dialect: Any, method_name: str) -> str:
    """reuse / override / proprietary / absent for one capability method."""
    cls = type(dialect)
    owners = [
        b for b in cls.__mro__
        if method_name in b.__dict__ and _is_real_implementation(b)
    ]
    if not owners:
        return "absent"
    first = owners[0]
    core_defines = any(_origin_of(b) == "core" for b in owners)
    origin = _origin_of(first)
    if origin == "backend":
        return "override" if core_defines else "proprietary"
    if origin == "core":
        return "reuse"
    return "other"


def classify_protocol_origin(
    dialect: Any, protocol: type, backend_protocols_mod: Any = None
) -> str:
    """reuse / override / proprietary / not-supported for a protocol.

    A protocol defined under ``impl.<b>`` is always proprietary. A core
    protocol is reuse when all its methods come from core owners, override
    when any method's first owner is a backend class.
    """
    mod = getattr(protocol, "__module__", "") or ""
    try:
        supported = isinstance(dialect, protocol)
    except TypeError:
        # protocol is not runtime_checkable; fall back to a structural probe
        members = [m for m, v in inspect.getmembers(protocol) if callable(v)]
        supported = all(hasattr(dialect, m) for m in members)
    if IMPL_MARK in mod:
        return "proprietary" if supported else "not-supported"
    if mod.startswith(CORE_DIALECT_MODULE):
        if not supported:
            return "not-supported"
        origins = set()
        for name, member in inspect.getmembers(protocol):
            if callable(member) and not name.startswith("_"):
                origins.add(classify_origin(dialect, name))
        return "override" if ("override" in origins or "proprietary" in origins) else "reuse"
    return "other"


# ---------------------------------------------------------------------------
# support checking (method level)
# ---------------------------------------------------------------------------
def get_support_methods(protocol_class: type) -> List[str]:
    """support-check methods declared by a protocol (naming convention)."""
    methods = []
    for name, member in inspect.getmembers(protocol_class):
        if callable(member) and (
            name.startswith("supports_")
            or (name.startswith("is_") and name.endswith("_available"))
        ):
            methods.append(name)
    return sorted(methods)


def check_protocol_support(
    dialect: Any, protocol_class: type, all_args: Optional[Dict[str, List[str]]] = None
) -> Dict[str, Any]:
    """Evaluate a protocol's support probes against a dialect instance."""
    all_args = all_args or {}
    results: Dict[str, Any] = {}
    for method_name in get_support_methods(protocol_class):
        if not hasattr(dialect, method_name):
            results[method_name] = False
            continue
        try:
            method = getattr(dialect, method_name)
            sig = inspect.signature(method)
            required = [
                p for p in sig.parameters.values()
                if p.default == inspect.Parameter.empty and p.name != "self"
            ]
            if not required:
                results[method_name] = bool(method())
            elif method_name in all_args:
                per_arg = {}
                for arg in all_args[method_name]:
                    try:
                        per_arg[arg] = bool(method(arg))
                    except Exception:
                        per_arg[arg] = False
                results[method_name] = {
                    "supported": sum(1 for v in per_arg.values() if v),
                    "total": len(per_arg),
                    "args": per_arg,
                }
            else:
                results[method_name] = False
        except Exception:
            results[method_name] = False
    return results


def _support_stats(results: Dict[str, Any]) -> tuple:
    """(supported, total) over a probe-result mapping."""
    supported = 0
    total = 0
    for value in results.values():
        if isinstance(value, dict):
            supported += value.get("supported", 0)
            total += value.get("total", 0)
        else:
            total += 1
            if value:
                supported += 1
    return supported, total


# ---------------------------------------------------------------------------
# report builders
# ---------------------------------------------------------------------------
def build_capability_report(
    dialect: Any,
    family_groups: Dict[str, list],
    dialect_specific_groups=None,
    all_args: Optional[Dict[str, List[str]]] = None,
    verbose: int = 0,
) -> Dict[str, Any]:
    """Build the ``capabilities`` section for a dialect.

    *family_groups* maps group name -> list of protocol classes (backend data).
    Every protocol carries ``supported``/``total``/``percentage`` plus an
    ``origin`` (reuse/override/proprietary). Dialect-specific groups are
    forced to proprietary.
    """
    dialect_specific_groups = dialect_specific_groups or set()
    all_args = all_args or {}
    report: Dict[str, Any] = {}
    for group_name, protocols in family_groups.items():
        group_info: Dict[str, Any] = {}
        for protocol in protocols:
            methods = check_protocol_support(dialect, protocol, all_args)
            supported, total = _support_stats(methods)
            percentage = round(supported / total * 100, 1) if total else 0
            if group_name in dialect_specific_groups:
                origin = "proprietary"
            else:
                origin = classify_protocol_origin(dialect, protocol)
            entry = {
                "supported": supported,
                "total": total,
                "percentage": percentage,
                "origin": origin,
            }
            if verbose >= 2:
                entry["methods"] = methods
                entry["method_origins"] = {
                    m: classify_origin(dialect, m) for m in methods
                }
            group_info[protocol.__name__] = entry
        report[group_name] = group_info
    return report


def build_suggestion_report(dialect: Any, verbose: int = 0) -> Dict[str, Any]:
    """Build the ``suggestions`` section (isinstance over all suggest protocols)."""
    report: Dict[str, Any] = {}
    for proto in suggestion_protocols():
        supported = isinstance(dialect, proto)
        methods = sorted(
            name for name, member in inspect.getmembers(proto)
            if callable(member) and name.startswith("suggest_")
        )
        entry: Dict[str, Any] = {"supported": supported}
        if verbose >= 2:
            entry["methods"] = methods
        report[proto.__name__] = entry
    return report


__all__ = [
    "iter_protocols",
    "suggestion_protocols",
    "classify_origin",
    "classify_protocol_origin",
    "get_support_methods",
    "check_protocol_support",
    "build_capability_report",
    "build_suggestion_report",
]
