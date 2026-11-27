# tests/rhosocial/activerecord_test/feature/rules/test_expression_constructors_do_not_refuse.py
"""An expression constructor collects; refusal belongs to the formatter.

The formal contract splits the two phases: instantiation gathers parameters and
does not validate them, while ``format_*`` reads the dialect's capability probes
and refuses what the dialect cannot render. A constructor that raises
``UnsupportedFeatureError`` moves a dialect fact into the data node: the node
can no longer be built (so it cannot be deserialized from a stored plan), and
the registry keeps a kind whose formatter was never asked.

This guard walks ``src`` and reports every ``__init__`` that raises
``UnsupportedFeatureError``. The scan is exercised against a fabricated
offender so a vacuous walk cannot pass.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Sequence, Union

_SRC = Path(__file__).resolve().parents[5] / "src" / "rhosocial" / "activerecord" / "backend" / "expression"

_Function = Union[ast.FunctionDef, ast.AsyncFunctionDef]


def _source_files() -> List[Path]:
    return [p for p in sorted(_SRC.rglob("*.py")) if "__pycache__" not in p.parts]


def _raises_unsupported(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Raise) or sub.exc is None:
            continue
        exc = sub.exc
        if isinstance(exc, ast.Call):
            exc = exc.func
        if isinstance(exc, ast.Name) and exc.id == "UnsupportedFeatureError":
            return True
        if isinstance(exc, ast.Attribute) and exc.attr == "UnsupportedFeatureError":
            return True
    return False


def _called_names(node: ast.AST) -> set:
    """Names called from *node*, as plain identifiers.

    Only bare calls matter here: a constructor that refuses through a helper
    (``_require(dialect, ...)``) used to slip past the direct-raise scan, and
    the UUID family shipped that way. Attribute calls (``self.method()``) are
    left out on purpose so a node calling its own renderer is not mistaken for
    a refusal.
    """
    names = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
            names.add(sub.func.id)
    return names


def _refusing_functions(tree: ast.Module) -> set:
    """Module-local function names that can raise ``UnsupportedFeatureError``.

    Transitive: a helper that calls another refusing helper counts, so an
    indirection of any depth is still seen. The fixpoint terminates because
    the set only grows and the population is finite.
    """
    funcs = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
    refusing = {name for name, fn in funcs.items() if _raises_unsupported(fn)}
    changed = True
    while changed:
        changed = False
        for name, fn in funcs.items():
            if name in refusing:
                continue
            if _called_names(fn) & refusing:
                refusing.add(name)
                changed = True
    return refusing


def _offenders(tree: ast.Module, label: str) -> List[str]:
    found = []
    refusing = _refusing_functions(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name != "__init__":
                continue
            if _raises_unsupported(item) or (_called_names(item) & refusing):
                found.append(f"{label}:{item.lineno} {node.name}.__init__ refuses")
    return found


def _scan(paths: Sequence[Path]) -> List[str]:
    return [
        offender
        for path in paths
        for offender in _offenders(
            ast.parse(path.read_text(encoding="utf-8")),
            str(path.relative_to(_SRC)),
        )
    ]


def test_no_expression_constructor_refuses_unsupported() -> None:
    files = _source_files()
    assert files, f"no source files found under {_SRC}"
    offenders = _scan(files)
    assert not offenders, "\n".join(offenders)


def test_the_scan_reaches_the_source_tree() -> None:
    inits = 0
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                inits += sum(
                    1
                    for i in node.body
                    if isinstance(i, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and i.name == "__init__"
                )
    assert inits > 100, f"only {inits} constructors were seen"


def test_the_scan_flags_a_planted_offender(tmp_path: Path) -> None:
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class P:\n"
        "    def __init__(self):\n"
        "        raise UnsupportedFeatureError('P', 'thing')\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert _offenders(tree, "probe")


def test_the_scan_flags_a_constructor_that_refuses_through_a_helper(tmp_path: Path) -> None:
    """The direct-raise scan was vacuous for this shape, and the UUID family
    used it: ``_require(...)`` raised, the constructor itself never named the
    exception, and every guard passed while three nodes could not be built."""
    probe = tmp_path / "_probe_indirect.py"
    probe.write_text(
        "def _require(flag):\n"
        "    if not flag:\n"
        "        raise UnsupportedFeatureError('P', 'thing')\n"
        "\n"
        "class P:\n"
        "    def __init__(self, flag):\n"
        "        _require(flag)\n"
        "        self.flag = flag\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert _offenders(tree, "probe")


def test_the_scan_flags_a_chain_of_helpers(tmp_path: Path) -> None:
    probe = tmp_path / "_probe_chain.py"
    probe.write_text(
        "def inner(flag):\n"
        "    if not flag:\n"
        "        raise UnsupportedFeatureError('P', 'thing')\n"
        "\n"
        "def outer(flag):\n"
        "    inner(flag)\n"
        "\n"
        "class P:\n"
        "    def __init__(self, flag):\n"
        "        outer(flag)\n"
        "        self.flag = flag\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert _offenders(tree, "probe")


def test_the_scan_accepts_a_collecting_constructor(tmp_path: Path) -> None:
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class P:\n"
        "    def __init__(self, value):\n"
        "        self.value = value\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _offenders(tree, "probe")
