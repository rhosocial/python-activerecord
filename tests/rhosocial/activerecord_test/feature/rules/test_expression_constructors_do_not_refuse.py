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


def _offenders(tree: ast.Module, label: str) -> List[str]:
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name != "__init__":
                continue
            if _raises_unsupported(item):
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
                inits += sum(1 for i in node.body if isinstance(i, (ast.FunctionDef, ast.AsyncFunctionDef)) and i.name == "__init__")
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
