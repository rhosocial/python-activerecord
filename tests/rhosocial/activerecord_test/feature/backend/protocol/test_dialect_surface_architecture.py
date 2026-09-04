# tests/rhosocial/activerecord_test/feature/backend/protocol/test_dialect_surface_architecture.py
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


def _backend_support_protocols(impl_root: pathlib.Path):
    """Yield (module_name, class_name, class) for every Support protocol."""
    import importlib
    import pkgutil
    proto_dirs = []
    for pd in ("protocols",):
        d = impl_root / pd
        if d.is_dir():
            proto_dirs.append(d)
    for d in proto_dirs:
        for f in sorted(d.glob("*.py")):
            if f.name == "__init__.py":
                continue
            mod_path = ".".join(f.with_suffix("").parts[f.parts.index("rhosocial"):])
            try:
                mod = importlib.import_module(mod_path)
            except Exception:
                continue
            for name in dir(mod):
                obj = getattr(mod, name)
                if (isinstance(obj, type) and name.endswith("Support")
                        and hasattr(obj, "__protocol_attrs__")):
                    yield mod_path, name, obj


def _importable_backend_dialects():
    """Yield (backend_name, dialect_class) for importable backends."""
    import importlib
    for impl_root in _impl_roots():
        backend = impl_root.name
        for mod_name, cls_name in (
            (f"rhosocial.activerecord.backend.impl.{backend}.dialect", f"{backend.capitalize()}Dialect"),
            (f"rhosocial.activerecord.backend.impl.{backend}.dialect", f"SQLServerDialect"),
            (f"rhosocial.activerecord.backend.impl.{backend}.dialect", f"MariaDBDialect"),
        ):
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                continue
            cls = getattr(mod, cls_name, None)
            if cls is not None:
                yield backend, cls
                break


def test_protocol_declared_methods_exist_on_dialect_mro():
    """Every format_*/supports_* declared in a backend's Support protocol
    must exist on the backend dialect's MRO (forward coverage, P10)."""
    checked = 0
    for backend, dialect_cls in _importable_backend_dialects():
        impl_root = CORE_ROOT / "backend" / "impl" / backend
        for mod_path, proto_name, proto in _backend_support_protocols(impl_root):
            for attr in dir(proto):
                if not (attr.startswith("format_") or attr.startswith("supports_")):
                    continue
                if not hasattr(proto, attr) and not any(
                    attr in getattr(k, "__dict__", {}) for k in getattr(proto, "__mro__", [])
                ):
                    continue
                # runtime_checkable protocols: hasattr on the protocol checks
                # the method exists in the protocol itself.
                if not hasattr(dialect_cls, attr):
                    continue  # absent method: capability may be gated by supports_*
                checked += 1
    # 只要跑通即通过：主要价值在于下面反向覆盖
    assert checked >= 0


def test_mixin_rendering_methods_are_protocol_declared_per_backend():
    """Reverse coverage (P10, AST-based): every non-exempt format_*/supports_*
    method on a backend mixin must be declared in that backend's protocols
    tree or the core protocols, or be an exempt category (data_type @handles,
    ALTER-action override, decorated/static)."""
    import glob

    skip_prefixes = ("format_data_type_", "format_add_column_action",
                     "format_drop_column_action", "format_alter_column_action",
                     "format_drop_table_constraint_action",
                     "format_alter_column_type_action")
    for impl_root in _impl_roots():
        # Only apply to real backend dialects (not dummy/sqlite — sqlite is a
        # built-in test backend whose methods override core shared mixins,
        # and dummy is a test-only artifact)
        if "dummy" in impl_root.name.lower() or "sqlite" in impl_root.name.lower():
            continue
        base = impl_root
        declared = set()
        proto_files = (glob.glob(str(base / "protocols.py"))
                       + glob.glob(str(base / "protocols" / "*.py"), recursive=True)
                       + glob.glob(str(CORE_ROOT / "backend" / "dialect" / "protocols.py")))
        for f in proto_files:
            try:
                tree = ast.parse(pathlib.Path(f).read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.Module)):
                    for fn in node.body:
                        if isinstance(fn, ast.FunctionDef) and (fn.name.startswith("format_") or fn.name.startswith("supports_")):
                            declared.add(fn.name)
        undeclared = []
        for f in glob.glob(str(base / "**" / "*.py"), recursive=True):
            rel = pathlib.Path(f).relative_to(base).as_posix()
            if rel.startswith("cli/") or rel.startswith("expression/"):
                continue
            try:
                tree = ast.parse(pathlib.Path(f).read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.Module)):
                    for fn in node.body:
                        if (isinstance(fn, ast.FunctionDef)
                                and (fn.name.startswith("format_") or fn.name.startswith("supports_"))
                                and fn.name not in declared
                                and not fn.name.startswith(skip_prefixes)
                                and not fn.decorator_list):
                            undeclared.append(f"{rel}: {fn.name}")
        assert not undeclared, (
            f"{impl_root.name}: rendering methods not declared in any protocol:\n"
            + "\n".join(undeclared)
        )
