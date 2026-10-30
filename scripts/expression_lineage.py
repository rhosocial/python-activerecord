#!/usr/bin/env python3
# scripts/expression_lineage.py
"""
List the expression kinds: what core ships, and what a backend adds.

Read off the default registry, which is the authority on what exists -- the
same source the artifact whitelist is built from, so this cannot enumerate a
different set.

A backend kind is an **override** when the kind already exists in core, and
**custom** when core has no kind of that name. Classification is by kind, not by
name similarity: two classes with similar names but different kinds are two
kinds, and the added one is custom.

Kinds are emitted in whatever order the registry yields them; the caller's
concern is the set, not the sequence.

Usage::

    python scripts/expression_lineage.py
    python scripts/expression_lineage.py --backend sqlite
    python scripts/expression_lineage.py --json
    python scripts/expression_lineage.py --kind table_list_expression

To survey another backend, add its expression package and dialect class to
``BACKENDS``.
"""
from __future__ import annotations

import argparse
import importlib
import json
import pkgutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

CORE_PACKAGES = (
    "rhosocial.activerecord.backend.expression",
    "rhosocial.activerecord.backend.transaction",
)

BACKENDS = {
    "sqlite": {
        "expression": ("rhosocial.activerecord.backend.impl.sqlite.expression",),
        "dialect": "rhosocial.activerecord.backend.impl.sqlite.dialect",
        "dialect_class": "SQLiteDialect",
    },
}


def _declares_a_formatter(cls: type) -> bool:
    """Whether *cls* resolves to a concrete ``format_method``.

    A base supplying one for its subclasses is a real declaration. Only the
    sentinel on the root base means "none", and that class is not a node, so it
    is not a kind.
    """
    from rhosocial.activerecord.backend.expression.core import BaseExpression

    for klass in cls.__mro__:
        if "format_method" in vars(klass):
            return klass is not BaseExpression
    return False


def _walk(pkgname: str):
    """Yield every concrete expression class a package defines.

    A module that fails to import is skipped rather than fatal: a backend that
    is not installed is not an error.
    """
    from rhosocial.activerecord.backend.expression.core import BaseExpression

    try:
        pkg = importlib.import_module(pkgname)
    except Exception:
        return
    if hasattr(pkg, "__path__"):
        modnames = [
            m
            for _, m, _ in pkgutil.walk_packages(
                path=pkg.__path__, prefix=pkgname + ".", onerror=lambda x: None
            )
        ]
    else:
        modnames = [pkgname]
    for modname in modnames:
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        for name in dir(mod):
            obj = getattr(mod, name, None)
            if not isinstance(obj, type) or obj.__module__ != modname:
                continue
            if not issubclass(obj, BaseExpression) or obj is BaseExpression:
                continue
            if getattr(obj, "__abstractmethods__", None):
                continue
            if not _declares_a_formatter(obj):
                continue
            yield modname, name, obj


def core_kinds() -> dict[str, str]:
    """Map kind -> class name for everything core ships."""
    from rhosocial.activerecord.backend.expression.core import Literal

    out: dict[str, str] = {}
    for pkgname in CORE_PACKAGES:
        for _modname, name, cls in _walk(pkgname):
            if issubclass(cls, Literal):
                continue  # one class carries every value kind
            out[cls.kind()] = name
    return out


def backend_kinds(name: str) -> dict[str, dict]:
    """Map kind -> its relation to core, for one backend."""
    from rhosocial.activerecord.backend.expression.core import Literal

    spec = BACKENDS[name]
    core = core_kinds()
    out: dict[str, dict] = {}
    for pkgname in spec["expression"]:
        for modname, cls_name, cls in _walk(pkgname):
            if issubclass(cls, Literal):
                continue
            kind = cls.kind()
            if kind in out:
                continue
            out[kind] = {
                "class": cls_name,
                "module": modname.rsplit(".", 1)[-1],
                "relation": "override" if kind in core else "custom",
                "overrides": core.get(kind),
            }
    return out


def collect(name: str) -> dict:
    core = core_kinds()
    return {"backend": name, "core": core, "backend_kinds": backend_kinds(name)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", default="sqlite", choices=sorted(BACKENDS))
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--kind", help="show one kind and exit non-zero if absent")
    args = ap.parse_args()

    data = collect(args.backend)

    if args.kind:
        row = data["backend_kinds"].get(args.kind) or (
            {"class": data["core"][args.kind], "relation": "core"}
            if args.kind in data["core"]
            else None
        )
        if row is None:
            print(f"not found: {args.kind}")
            return 1
        print(f"{args.kind}\t{row['relation']}\t{row['class']}")
        return 0

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
        return 0

    core = data["core"]
    rows = data["backend_kinds"]
    overrides = sorted(k for k, v in rows.items() if v["relation"] == "override")
    customs = sorted(k for k, v in rows.items() if v["relation"] == "custom")

    print(f"core kinds: {len(core)}")
    print(f"{args.backend} override: {len(overrides)}")
    print(f"{args.backend} custom:   {len(customs)}")

    print("\n=== core ===")
    for kind in sorted(core):
        print(f"  {kind}\t{core[kind]}")

    print(f"\n=== {args.backend} override ===")
    for kind in overrides:
        print(f"  {kind}\t{rows[kind]['class']}\t(core: {rows[kind]['overrides']})")

    print(f"\n=== {args.backend} custom ===")
    for kind in customs:
        print(f"  {kind}\t{rows[kind]['class']}\t{rows[kind]['module']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())