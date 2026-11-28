# tests/rhosocial/activerecord_test/feature/rules/backend/test_backend_package_excludes_impl.py
"""Core's generic backend layer carries no backend implementation content.

A backend's proprietary definitions never enter core, and the dependency runs
one way: a concrete backend imports the generic layer, never the reverse. In
Python the two sides are separated by package — the generic side is
``rhosocial.activerecord.backend.*``, the proprietary side is
``rhosocial.activerecord.backend.impl.*`` — and the generic entry must not
re-export proprietary nodes.

The operational form of that rule, and what this test checks, is one sentence:
**no module under ``rhosocial.activerecord.backend`` may consume anything from
``rhosocial.activerecord.backend.impl``**. Content crosses a package boundary by
import, so the scan looks at every channel an import can be written through:

* an absolute import whose module names ``backend.impl``;
* a relative import whose module is ``impl`` or starts with ``impl.``;
* a name dotted with ``backend.impl`` in an ``import``/``from ... import``;
* a dynamic import — ``importlib.import_module`` / ``__import__`` — whose
  literal argument names ``backend.impl``.

Where the line is drawn
-----------------------
A *mention* is not a dependency. A docstring example that shows a caller how to
use ``SQLiteDialect``, or a CLI ``prog`` string naming the module it launches, is
text about the backend, not content taken from it; those files stay clean because
they execute no import. Only executable references count, and the scan therefore
reads the AST rather than the raw text.

What this cannot see: a module reached by ``getattr`` on a computed name, or an
``__import__`` whose argument is built at run time. Those are named here rather
than silently assumed absent. The reach is also structural — the scan covers the
installed ``backend`` package's own ``__path__``, so a subpackage separated from
that path is not in scope.

Directory convention
--------------------
Files in this directory govern ``rhosocial.activerecord.backend.*`` — core's
generic layer — and are written here, in core. The rules that govern
``rhosocial.activerecord.backend.impl.*`` are written once in
``rhosocial-activerecord-testsuite`` and only bridged into a backend's test tree;
their bridges live under ``feature/rules/backend/impl/`` so the two kinds of
directory never collide by name.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from typing import Iterator, List, Tuple

IMPL_PACKAGE = ("backend", "impl")


def generic_backend_root() -> Path:
    """The installed generic ``backend`` package directory."""
    package = importlib.import_module("rhosocial.activerecord.backend")
    for candidate in vars(package).get("__path__", ()):
        path = Path(candidate).resolve()
        if path.is_dir():
            return path
    raise AssertionError("the installed backend package exposes no directory")


def generic_sources(root: Path) -> Iterator[Tuple[str, Path]]:
    """Every source of the generic layer: ``impl/`` itself is out of scope."""
    impl_root = root / "impl"
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        if impl_root in path.parents:
            continue
        yield path.relative_to(root).as_posix(), path


def names_impl(module: str) -> bool:
    """Whether a dotted module lives in ``backend.impl``.

    Segment-based, not substring-based: ``backend.implementations`` is a
    different package from ``backend.impl`` and must not be reported.
    """
    parts = module.lstrip(".").split(".")
    if not parts or not parts[0]:
        return False
    # A relative import names only the tail: ``.impl.sqlite.dialect``.
    if parts[0] == "impl":
        return True
    return any(
        parts[index : index + 2] == list(IMPL_PACKAGE) for index in range(len(parts) - 1)
    )


def dynamic_import_name(call: ast.Call) -> str:
    """The called function's simple name; empty when it is not a plain call."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def impl_references(tree: ast.AST) -> List[Tuple[int, str]]:
    """Executable references from this module into ``backend.impl``.

    Returns ``(lineno, spelling)`` pairs so a report names the line and the
    exact form the reference took.
    """
    found: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if names_impl(alias.name):
                    found.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if names_impl(module):
                found.append((node.lineno, f"from {'.' * node.level}{module} import ..."))
            for alias in node.names:
                if names_impl(alias.name):
                    found.append((node.lineno, f"from {module} import {alias.name}"))
        elif isinstance(node, ast.Call):
            if dynamic_import_name(node) not in {"import_module", "__import__"}:
                continue
            if not node.args:
                continue
            argument = node.args[0]
            if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
                continue
            if names_impl(argument.value):
                found.append(
                    (node.lineno, f"{dynamic_import_name(node)}({argument.value!r})")
                )
    return found


def scan(sources: List[Tuple[str, Path]]) -> List[str]:
    """Offenders across a labelled source list, one line each."""
    offenders: List[str] = []
    for label, path in sources:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError, ValueError):
            continue
        for lineno, spelling in impl_references(tree):
            offenders.append(f"{label}:{lineno}: {spelling}")
    return offenders


def probe(source: str) -> List[str]:
    """Offenders in a synthetic module, parsed exactly like a real one."""
    tree = ast.parse(source, filename="<probe>")
    return [f"<probe>:{lineno}: {spelling}" for lineno, spelling in impl_references(tree)]


MIN_SOURCES = 400


def test_the_scan_reaches_the_generic_layer() -> None:
    """The generic layer is the whole package minus ``impl``; that is hundreds."""
    sources = list(generic_sources(generic_backend_root()))
    assert len(sources) >= MIN_SOURCES, (
        f"only {len(sources)} generic source files were scanned; "
        "a scan that misses the layer is not a check"
    )


def test_no_generic_module_consumes_impl_content() -> None:
    """Property one: core takes nothing from a backend implementation."""
    offenders = scan(list(generic_sources(generic_backend_root())))
    assert not offenders, "generic backend modules referencing backend.impl:\n" + "\n".join(
        offenders
    )


def test_an_absolute_import_is_flagged() -> None:
    found = probe(
        "from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect\n"
    )
    assert found, "an absolute import of an impl module was not reported"


def test_a_relative_import_is_flagged() -> None:
    found = probe("from .impl.sqlite.dialect import SQLiteDialect\n")
    assert found, "a relative import of an impl module was not reported"


def test_a_bare_impl_package_import_is_flagged() -> None:
    found = probe("from . import impl\n")
    assert found, "importing the impl package itself was not reported"


def test_a_dynamic_import_is_flagged() -> None:
    found = probe(
        "import importlib\n"
        "importlib.import_module('rhosocial.activerecord.backend.impl.sqlite.dialect')\n"
    )
    assert found, "a dynamic import of an impl module was not reported"


def test_a_mention_in_text_is_not_a_dependency() -> None:
    """A docstring example or a CLI prog string describes, it does not consume."""
    source = (
        '"""Usage::\n\n'
        "    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect\n"
        '"""\n'
        "PROG = 'python -m rhosocial.activerecord.backend.impl.sqlite'\n"
    )
    assert not probe(source), "a textual mention was reported as a dependency"


def test_an_unrelated_import_is_clean() -> None:
    found = probe("from rhosocial.activerecord.backend.dialect.base import SQLDialectBase\n")
    assert not found, "a generic import inside the generic layer was reported"


def test_a_similarly_spelled_package_is_clean() -> None:
    """``backend.implementations`` is not ``backend.impl``; segment match, not prefix."""
    found = probe("from rhosocial.activerecord.backend.implementations import Thing\n")
    assert not found, "a package whose name merely starts with impl was reported"
