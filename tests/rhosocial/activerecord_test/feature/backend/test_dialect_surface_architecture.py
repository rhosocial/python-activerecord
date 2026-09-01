# tests/rhosocial/activerecord_test/feature/backend/test_dialect_surface_architecture.py
"""Architecture guard: dialect rendering surface must be public.

Plan: dialect-feature-group-refactor (2026-08-31).  Format functions are
declared in protocols and implemented in mixins — never private — because
the dialect surface is the user-facing extension point ("who defines the
clause, who declares it" — the functional-group principle):

    功能组 = 表达式类 + supports_* 协议声明 + format_* 公有实现

Private rendering helpers cannot be overridden or composed by users and
historically drifted into dead duplicated copies (mariadb/mysql/firebird).

Scanned population: every importable backend implementation package plus
the core shared dialect mixins.  Backends absent from the installation are
naturally skipped, so this test also runs green in core-only CI.
"""

import ast
import glob
import pathlib

CORE_ROOT = pathlib.Path(__file__).parents[5] / "src/rhosocial/activerecord"

# Exemptions: CLI display helpers and expression-internal derived methods
# are not part of the dialect rendering surface (documented in
# dialect-feature-group-refactor.md, categories D4/D5).
EXEMPT_DIR_PARTS = ("cli", "expression")


def _impl_roots():
    """Importable backend impl roots present in this installation."""
    impl_pkg = CORE_ROOT / "backend" / "impl"
    if not impl_pkg.is_dir():
        return []
    return [
        d for d in sorted(impl_pkg.iterdir())
        if d.is_dir() and (d / "__init__.py").exists()
    ]


def _scan_private_format(root: pathlib.Path):
    """Return [(file, class, func)] for private ``_format*`` methods."""
    hits = []
    for f in glob.glob(str(root / "**" / "*.py"), recursive=True):
        rel = pathlib.Path(f).relative_to(root).as_posix()
        if any(part in rel.split("/") for part in EXEMPT_DIR_PARTS):
            continue
        try:
            tree = ast.parse(pathlib.Path(f).read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef) and sub.name.startswith("_format"):
                        hits.append((rel, node.name, sub.name))
    return hits


def test_shared_dialect_mixins_have_no_private_format_functions():
    """Core shared mixins implement protocol-declared format_* publicly."""
    root = CORE_ROOT / "backend" / "dialect" / "mixins"
    hits = _scan_private_format(root)
    assert not hits, f"private format helpers in shared mixins: {hits}"


def test_backend_dialect_surfaces_have_no_private_format_functions():
    """Every importable backend keeps its rendering surface public."""
    violations = []
    for impl_root in _impl_roots():
        # Skip expression/ trees: expression-internal derived helpers
        # (category D4) are exempt; dialect/mixin/cli surfaces are scanned.
        hits = _scan_private_format(impl_root)
        for rel, cls, fn in hits:
            violations.append(f"{impl_root.parent.parent.name}/{rel}: {cls}.{fn}")
    assert not violations, "private format helpers on dialect surfaces:\n" + "\n".join(
        violations
    )
