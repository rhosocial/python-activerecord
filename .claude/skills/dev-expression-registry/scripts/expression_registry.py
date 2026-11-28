# .claude/skills/dev-expression-registry/scripts/expression_registry.py
"""Print the expression registries — core, or core plus a named backend.

The registries are the authoritative answer to "which expressions exist".
This script only reads the published tables; it never walks source or infers
anything from class names. Kinds are the identities that cross the wire in an
artifact, so the printed list is also the set of nodes a reader can rebuild.

What it is NOT: a claim that a dialect renders every listed kind. Formatting is
the dialect's job and can differ by version. See dev-expression-dialect.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import types
from typing import Any, Dict, List, Sequence

IMPL_ROOT = "rhosocial.activerecord.backend.impl"
CORE_MODULE = "rhosocial.activerecord.backend.expression_registry"

# Backends import their DB driver eagerly in __init__. Only the expression
# registry is needed here, so stub a driver that cannot load. This never
# touches a real driver that imports fine.
DRIVER_STUB_MODULES = (
    "pyodbc",
    "clickhouse_connect",
    "mysql.connector",
    "mariadb",
    "oracledb",
    "psycopg",
    "snowflake.connector",
    "firebird.driver",
)

EXCLUDE_FRAGMENTS = ("__pycache__", "examples", "tests", "docs")


def _make_driver_stub(name: str) -> Any:
    module = types.ModuleType(name)
    module.__path__ = []  # type: ignore[attr-defined]

    def __getattr__(attr: str) -> Any:
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)
        stub = type(attr, (Exception,), {"__module__": name})
        setattr(module, attr, stub)
        return stub

    module.__getattr__ = __getattr__  # type: ignore[attr-defined]
    return module


def install_driver_stubs(names: Sequence[str] = DRIVER_STUB_MODULES) -> List[str]:
    """Stub drivers that fail to import. Must run before importing a backend."""
    stubbed: List[str] = []
    for name in names:
        root = name.split(".")[0]
        if name in sys.modules:
            continue
        try:
            importlib.import_module(name)
            continue
        except Exception:
            pass
        try:
            importlib.import_module(root)
            continue
        except Exception:
            pass
        sys.modules[name] = _make_driver_stub(name)
        stubbed.append(name)
    return stubbed


def installed_backends() -> List[str]:
    """Backend names on the active interpreter's impl search path.

    Backends are PEP 420 namespace portions with no __init__.py, so
    pkgutil.iter_modules silently returns nothing. Enumerating directories on
    ``impl.__path__`` is the reliable source, and it includes editable installs.
    """
    impl = importlib.import_module(IMPL_ROOT)
    names = set()
    for entry in getattr(impl, "__path__", ()):
        try:
            children = os.listdir(entry)
        except OSError:
            continue
        for child in children:
            if child.startswith(".") or any(f in child for f in EXCLUDE_FRAGMENTS):
                continue
            if os.path.isdir(os.path.join(entry, child)):
                names.add(child)
    return sorted(names)


def core_expressions() -> Dict[str, str]:
    """CORE_EXPRESSIONS: the kinds core declares, mapped to class FQNs."""
    return dict(getattr(importlib.import_module(CORE_MODULE), "CORE_EXPRESSIONS"))


def backend_expressions(name: str):
    """Return (own mapping, merged registry) for one backend."""
    module = importlib.import_module(f"{IMPL_ROOT}.{name}.expression_registry")
    own = getattr(module, f"{name.upper()}_EXPRESSIONS", None)
    if own is None:
        candidates = [
            v
            for k, v in vars(module).items()
            if k.endswith("_EXPRESSIONS") and k != "CORE_EXPRESSIONS" and isinstance(v, dict)
        ]
        if not candidates:
            raise RuntimeError(f"{module.__name__} publishes no *_EXPRESSIONS mapping")
        own = candidates[0]
    registry = getattr(module, f"{name.upper()}_EXPRESSION_REGISTRY", None)
    if registry is None:
        candidates = [
            v for k, v in vars(module).items() if k.endswith("_EXPRESSION_REGISTRY")
        ]
        registry = candidates[0] if candidates else None
    return dict(own), registry


def _dump_table(title: str, table: Dict[str, str], kinds_only: bool) -> None:
    print(f"{title} ({len(table)} kinds)")
    for kind in sorted(table):
        if kinds_only:
            print(f"  {kind}")
        else:
            print(f"  {kind:<48} -> {table[kind]}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        action="append",
        default=[],
        metavar="NAME",
        help="backend namespace; repeat, or use 'all'. Omit for core only",
    )
    parser.add_argument("--list-backends", action="store_true", help="list discovered backends")
    parser.add_argument("--kinds-only", action="store_true", help="print kinds without FQNs")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    install_driver_stubs()
    backends = installed_backends()

    if args.list_backends:
        print("\n".join(backends))
        return 0

    requested: List[str] = []
    for item in args.backend:
        if item == "all":
            requested = list(backends)
            break
        if item not in backends:
            parser.error(f"unknown backend {item!r}; available: {', '.join(backends)}")
        if item not in requested:
            requested.append(item)

    core = core_expressions()
    result: Dict[str, Any] = {"core": core}
    for name in requested:
        own, registry = backend_expressions(name)
        result[name] = own
        result[f"{name}_registry_size"] = len(registry.node_kinds()) if registry else None

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    _dump_table("CORE_EXPRESSIONS", core, args.kinds_only)
    for name in requested:
        own = result[name]
        _dump_table(f"{name.upper()}_EXPRESSIONS", own, args.kinds_only)
        size = result[f"{name}_registry_size"]
        if size is not None:
            print(f"{name}: merged registry admits {size} kinds (core + {name})")
    if not requested and not args.json:
        print("\nAdd --backend <name> to print a backend's own kinds, or --backend all.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
