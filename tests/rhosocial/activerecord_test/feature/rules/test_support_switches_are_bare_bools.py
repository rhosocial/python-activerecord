# tests/rhosocial/activerecord_test/feature/rules/test_support_switches_are_bare_bools.py
"""Every ``supports_*`` under ``src/`` is a switch: no parameters, one bool.

A capability switch answers "does this dialect have this capability". Its only
input is the dialect instance it hangs off and its only answer is one bool. That
shape is what makes it usable: a caller may enumerate the switches, ask each one
without knowing what arguments it might need, and hold the answer for a dialect
instance without asking again.

The rule is not stylistic. ``supports_json_table(dialect_options=None)`` was
accepted for a while and the backend guide taught it, so a caller that passed
``{'on_error': 'IGNORE'}`` got a different answer for the same dialect: the
"capability" depended on the statement being built. Options that vary per
statement belong to the formatter, whose output is exactly one statement. A
switch that varies per statement is a question with no single answer.

What is checked: every ``def`` named ``supports_*`` in ``src/**/*.py`` -- in
mixins, in protocols (whose bodies are ``...``), in implementations -- declares
exactly ``self`` and returns ``bool``, bare or quoted. A defaulted parameter still
counts as a parameter: the caller may omit it, but the switch offers a second
input.

What this cannot see: the nine backend repositories, where the same rule holds
and each backend guards its own tree.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Sequence, Union

_SRC = Path(__file__).resolve().parents[5] / "src"

_ModuleFunction = Union[ast.FunctionDef, ast.AsyncFunctionDef]


def _source_files() -> List[Path]:
    """Every ``src/**/*.py`` file in this repository."""
    return [path for path in sorted(_SRC.rglob("*.py")) if "__pycache__" not in path.parts]


def _parameters(func: _ModuleFunction) -> List[str]:
    """Every parameter the switch declares, ``self`` excluded."""
    args = func.args
    positional = list(args.posonlyargs) + list(args.args)
    if positional and positional[0].arg == "self":
        positional = positional[1:]
    names = [arg.arg for arg in positional]
    names += [arg.arg for arg in args.kwonlyargs]
    if args.vararg is not None:
        names.append("*" + args.vararg.arg)
    if args.kwarg is not None:
        names.append("**" + args.kwarg.arg)
    return names


def _returns_bool(func: _ModuleFunction) -> bool:
    """A switch declares ``-> bool``, bare or quoted."""
    annotation = func.returns
    if annotation is None:
        return False
    if isinstance(annotation, ast.Name):
        return annotation.id == "bool"
    return isinstance(annotation, ast.Constant) and annotation.value == "bool"


def _offenders(tree: ast.Module, label: str) -> List[str]:
    """Every ``supports_*`` in the tree that is not a bare bool switch."""
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("supports_"):
            continue
        declared = _parameters(node)
        if declared:
            found.append(f"{label}:{node.lineno} {node.name} declares {', '.join(declared)}")
        elif not _returns_bool(node):
            found.append(f"{label}:{node.lineno} {node.name} does not return bool")
    return found


def _scan(paths: Sequence[Path]) -> List[str]:
    found = []
    for path in paths:
        found.extend(
            _offenders(
                ast.parse(path.read_text(encoding="utf-8")),
                str(path.relative_to(_SRC)),
            )
        )
    return found


def _switch_names(paths: Sequence[Path]) -> List[str]:
    """Names of every ``supports_*`` function, so a vacuous walk is visible."""
    names = []
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("supports_"):
                    names.append(node.name)
    return names


def _probe(tmp_path: Path, source: str) -> List[str]:
    probe = tmp_path / "_probe.py"
    probe.write_text(source, encoding="utf-8")
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    return _offenders(tree, "probe")


def test_every_support_switch_is_a_bare_bool() -> None:
    """The rule, over the real source tree."""
    files = _source_files()
    assert files, f"no source files found under {_SRC}"
    offenders = _scan(files)
    assert not offenders, "\n".join(offenders)


def test_the_scan_reaches_the_source_tree() -> None:
    """The file set and the switch set are neither empty nor nearly empty."""
    files = _source_files()
    assert len(files) > 200, f"only {len(files)} source files were scanned"
    switches = _switch_names(files)
    assert len(switches) > 500, f"only {len(switches)} support switches were seen"


def test_the_scan_flags_a_required_parameter(tmp_path: Path) -> None:
    offenders = _probe(
        tmp_path,
        "class P:\n"
        "    def supports_thing(self, name) -> bool:\n"
        "        return False\n",
    )
    assert offenders and "declares name" in offenders[0]


def test_the_scan_flags_a_defaulted_parameter(tmp_path: Path) -> None:
    """The shape the backend guide used to teach for JSON_TABLE."""
    offenders = _probe(
        tmp_path,
        "from typing import Any, Dict, Optional\n"
        "class P:\n"
        "    def supports_thing(self, dialect_options: Optional[Dict[str, Any]] = None) -> bool:\n"
        "        return False\n",
    )
    assert offenders and "declares dialect_options" in offenders[0]


def test_the_scan_flags_a_keyword_only_parameter(tmp_path: Path) -> None:
    offenders = _probe(
        tmp_path,
        "class P:\n"
        "    def supports_thing(self, *, kind) -> bool:\n"
        "        return False\n",
    )
    assert offenders and "declares kind" in offenders[0]


def test_the_scan_flags_variadic_parameters(tmp_path: Path) -> None:
    offenders = _probe(
        tmp_path,
        "class P:\n"
        "    def supports_thing(self, *args) -> bool:\n"
        "        return False\n",
    )
    assert offenders and "declares *args" in offenders[0]


def test_the_scan_flags_a_non_bool_annotation(tmp_path: Path) -> None:
    offenders = _probe(
        tmp_path,
        "from typing import Dict\n"
        "class P:\n"
        "    def supports_thing(self) -> Dict[str, bool]:\n"
        "        return {}\n",
    )
    assert offenders and "does not return bool" in offenders[0]


def test_the_scan_flags_a_missing_annotation(tmp_path: Path) -> None:
    offenders = _probe(
        tmp_path,
        "class P:\n"
        "    def supports_thing(self):\n"
        "        return False\n",
    )
    assert offenders and "does not return bool" in offenders[0]


def test_the_scan_accepts_a_bare_switch(tmp_path: Path) -> None:
    offenders = _probe(
        tmp_path,
        'class P:\n    def supports_thing(self) -> "bool":\n        return False\n',
    )
    assert not offenders


def test_the_scan_ignores_functions_that_are_not_switches(tmp_path: Path) -> None:
    offenders = _probe(
        tmp_path,
        "class P:\n"
        "    def format_thing(self, expr, dialect_options=None):\n"
        "        return '', ()\n",
    )
    assert not offenders
