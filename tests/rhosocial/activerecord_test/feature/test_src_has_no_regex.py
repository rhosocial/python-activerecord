# tests/rhosocial/activerecord_test/feature/test_src_has_no_regex.py
"""Guard: the core source tree carries no ``re`` dependency.

The backend validates and scans several small grammars (identifiers, type
names, WKT text, ISO durations). Every one of them is answered by character
scanning under ``backend/textscan.py`` and by the callers that compose it.

Keeping that true is cheaper as a test than as a review habit, so this walks
``src/**/*.py`` and fails on:

* any ``import re`` or ``from re import ...``, and
* any ``re.`` reference in the text -- which also counts prose that names a
pattern, because a comment saying "matches ``re.compile``" is still a
reference a reader may copy.

Tests are free to use ``re`` where a regex is the thing being asserted (generated
SQL above all); this test only guards ``src``.
"""

import ast
from pathlib import Path
from typing import Iterator, List, Tuple

_SRC = Path(__file__).resolve().parents[4] / "src"


def _source_files() -> List[Path]:
    """Every Python module under ``src``, in a stable order."""
    return sorted(_SRC.rglob("*.py"))


def _re_imports(tree: ast.AST) -> Iterator[Tuple[int, str]]:
    """Line numbers and spellings of imports of the ``re`` module."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "re" or alias.name.startswith("re."):
                    yield node.lineno, f"import {alias.name}"
        elif isinstance(node, ast.ImportFrom) and node.module == "re":
            yield node.lineno, "from re import ..."


def _re_attributes(tree: ast.AST) -> Iterator[Tuple[int, str]]:
    """Line numbers of attribute uses on a name spelled ``re``."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if isinstance(node.value, ast.Name) and node.value.id == "re":
            yield node.lineno, f"re.{node.attr}"


def _re_text_mentions(source: str) -> Iterator[Tuple[int, str]]:
    """Line numbers where the text carries ``re.`` as a standalone name.

    A match must stand on a word boundary, so ``core.FunctionCall`` and
    ``where.to_sql()`` do not count while ``re.compile`` does. Comments and
    string literals are scanned too: the rule is about references a reader
    can follow, not about executable statements only.
    """
    for lineno, line in enumerate(source.splitlines(), 1):
        index = line.find("re.")
        while index != -1:
            before = line[index - 1] if index else ""
            if not (before.isalnum() or before == "_"):
                yield lineno, line.strip()
                break
            index = line.find("re.", index + 1)


def test_src_has_no_regex() -> None:
    """Fail naming every ``re`` import and reference under ``src``."""
    assert _SRC.is_dir(), f"src directory not found at {_SRC}"
    files = _source_files()
    assert files, f"no Python modules found under {_SRC}"

    violations: List[str] = []
    for path in files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        relative = path.relative_to(_SRC.parent)
        for lineno, detail in _re_imports(tree):
            violations.append(f"{relative}:{lineno}: imports the re module ({detail})")
        for lineno, detail in _re_attributes(tree):
            violations.append(f"{relative}:{lineno}: uses a re attribute ({detail})")
        for lineno, text in _re_text_mentions(source):
            violations.append(f"{relative}:{lineno}: mentions re. ({text})")

    assert not violations, (
        "src must not use the re module (scan text instead):\n  " + "\n  ".join(violations)
    )
