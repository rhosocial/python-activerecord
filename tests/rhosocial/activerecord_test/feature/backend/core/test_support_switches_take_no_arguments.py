# tests/rhosocial/activerecord_test/feature/backend/core/test_support_switches_take_no_arguments.py
"""``supports_*`` is a support switch: no arguments, one bool.

A capability flag answers "does this dialect configuration have capability k",
so its only input is the dialect instance. Anything that needs a name or a kind
is either a separate switch (closed vocabulary) or a format-time validation
(open vocabulary) -- never an argument to ``supports_*``.
"""
import ast
from pathlib import Path

import pytest


def _source_files():
    """The core backend tree inside this repository."""
    root = (
        Path(__file__).resolve().parents[6]
        / "src"
        / "rhosocial"
        / "activerecord"
        / "backend"
    )
    files = []
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append(path)
    return files


def _required_arguments(func: ast.FunctionDef):
    """Parameters that must be passed, excluding ``self``."""
    args = func.args
    positional = list(args.args)
    required = positional[1 : len(positional) - len(args.defaults)]
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        if default is None:
            required.append(arg)
    return [a.arg for a in required]


def _annotates_bool(func: ast.FunctionDef) -> bool:
    """A switch declares ``-> bool`` (or no annotation, which cannot be judged here)."""
    annotation = func.returns
    if annotation is None:
        return True
    if isinstance(annotation, ast.Name) and annotation.id == "bool":
        return True
    if isinstance(annotation, ast.Constant) and annotation.value == "bool":
        return True
    return False


def _offenders(tree, label):
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if not item.name.startswith("supports_"):
                continue
            missing = _required_arguments(item)
            if missing:
                found.append(f"{label}:{item.lineno} {item.name}({', '.join(missing)})")
            elif not _annotates_bool(item):
                found.append(
                    f"{label}:{item.lineno} {item.name} does not return bool"
                )
    return found


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: str(p.name))
def test_support_switch_takes_no_required_argument(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _offenders(tree, path.name)
    assert not offenders, "\n".join(offenders)


def test_the_scan_reaches_the_source_tree():
    files = _source_files()
    assert len(files) > 50, f"only {len(files)} source files were scanned"


def test_the_scan_flags_a_planted_violation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class P:\n"
        "    def supports_thing(self, name):\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert _offenders(tree, "probe")


def test_the_scan_accepts_a_defaulted_parameter(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class P:\n"
        "    def supports_thing(self, name=None):\n"
        "        return False\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _offenders(tree, "probe")


def test_the_scan_flags_a_non_bool_annotation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "from typing import Dict\n"
        "class P:\n"
        "    def supports_thing(self) -> Dict[str, bool]:\n"
        "        return {}\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    offenders = _offenders(tree, "probe")
    assert offenders and "does not return bool" in offenders[0]


def test_the_scan_accepts_a_quoted_bool_annotation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        'class P:\n    def supports_thing(self) -> "bool":\n        return False\n',
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _offenders(tree, "probe")


def _protocol_bases(tree, label):
    """Dialect classes must not inherit a ``*Support`` protocol.

    A runtime-checkable Protocol is satisfied structurally; inheriting it only
    adds its ellipsis-bodied members, which make ``isinstance`` pass even when
    nothing implements them.
    """
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or not node.name.endswith("Dialect"):
            continue
        for base in node.bases:
            if isinstance(base, ast.Name):
                name = base.id
            elif isinstance(base, ast.Attribute):
                name = base.attr
            else:
                continue
            if name.endswith("Support"):
                found.append(f"{label}:{node.lineno} {node.name}({name})")
    return found


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: str(p.name))
def test_dialect_does_not_inherit_a_protocol(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = _protocol_bases(tree, path.name)
    assert not offenders, "\n".join(offenders)


def test_the_protocol_scan_reaches_the_source_tree():
    assert len(_source_files()) > 50


def test_the_protocol_scan_flags_a_planted_violation(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class ProbeSupport:\n"
        "    pass\n"
        "class ProbeDialect(ProbeSupport):\n"
        "    pass\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert _protocol_bases(tree, "probe")


def test_the_protocol_scan_accepts_a_plain_base(tmp_path):
    probe = tmp_path / "_probe.py"
    probe.write_text(
        "class Base:\n"
        "    pass\n"
        "class ProbeDialect(Base):\n"
        "    pass\n",
        encoding="utf-8",
    )
    tree = ast.parse(probe.read_text(encoding="utf-8"))
    assert not _protocol_bases(tree, "probe")
