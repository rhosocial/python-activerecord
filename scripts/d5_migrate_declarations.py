# scripts/d5_migrate_declarations.py  (temporary; delete after the wave)
"""D5 sweep: class-body dunder declarations -> accessor method overrides.

AST-located, not regex-matched, so a docstring example or a local variable
that happens to spell a dunder is never rewritten. Namespace-dict entries
(for ``type(...)`` dynamic models) take the ``classmethod(lambda cls: ...)``
form.
"""
import ast
import sys
from pathlib import Path

ROOTS = [Path("src"), Path("tests")]
EXCLUDE_RELPATHS = {
    "src/rhosocial/activerecord/field/version.py",
    "src/rhosocial/activerecord/field/read_only.py",
    "src/rhosocial/activerecord/field/soft_delete.py",
    "src/rhosocial/activerecord/field/timestamp.py",
    "src/rhosocial/activerecord/interface/model.py",
    "src/rhosocial/activerecord/field/composite_pk.py",
    "src/rhosocial/activerecord/base/ddl.py",
    # Its _LOCATOR_LANDINGS table spells the dunders as dict keys on purpose.
    "src/rhosocial/activerecord/field/field_config.py",
}

MAP = {
    "__table_name__": "table_name",
    "__schema_name__": "schema_name",
    "__primary_key__": "primary_key",
    "__pk_auto_generated__": "pk_auto_generated",
    "__deleted_at_field__": "deleted_at_field",
    "__created_at_field__": "created_at_field",
    "__updated_at_field__": "updated_at_field",
    "__version_field__": "version_field",
    "__version_increment_by__": "version_increment_by",
    "__read_only__": "read_only",
}


def value_text(seg: str) -> str:
    """Strip a trailing comma from a captured value."""
    seg = seg.strip()
    if seg.endswith(","):
        seg = seg[:-1].rstrip()
    return seg


def convert_file(path: Path, dry: bool) -> int:
    rel = path.as_posix()
    if rel in EXCLUDE_RELPATHS or "__pycache__" in rel:
        return 0
    raw = path.read_bytes()
    source = raw.decode("utf-8")
    crlf = "\r\n" in source
    try:
        tree = ast.parse(source)
    except SyntaxError:
        print(f"SKIP (syntax): {rel}")
        return 0

    targets = []  # (lineno, dunder, replacement_lines)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                    t = stmt.targets[0]
                    if isinstance(t, ast.Name) and t.id in MAP:
                        targets.append((stmt.lineno, t.id))
                elif isinstance(stmt, ast.AnnAssign):
                    t = stmt.target
                    if isinstance(t, ast.Name) and t.id in MAP:
                        targets.append((stmt.lineno, t.id))
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and key.value in MAP
                ):
                    targets.append((key.lineno, key.value))

    if not targets:
        return 0
    lines = source.split("\n")
    out = []
    changed = 0
    pending = {lineno: dunder for lineno, dunder in targets}
    for i, line in enumerate(lines, start=1):
        if i in pending:
            dunder = pending[i]
            method = MAP[dunder]
            indent = line[: len(line) - len(line.lstrip())]
            if line.lstrip().startswith('"'):
                # Namespace dict entry: value runs to end of line (checked
                # single-line only; the sweep aborts on anything else).
                raw = line.split(":", 1)[1].rstrip()
                trailing = "," if raw.endswith(",") else ""
                value = value_text(raw)
                out.append(
                    f'{indent}"{method}": classmethod('
                    f"lambda cls: {value}){trailing}"
                )
            else:
                raw = line.split("=", 1)[1] if "=" in line else ""
                value = value_text(raw)
                out.append(f"{indent}@classmethod")
                out.append(f"{indent}def {method}(cls):")
                out.append(f"{indent}    return {value}")
                # Separate the new method from whatever follows only when the
                # source offered no blank line of its own, so the rewritten
                # file keeps the original spacing.
                nxt = lines[i] if i < len(lines) else ""
                if nxt.strip():
                    out.append("")
            changed += 1
            continue
        out.append(line)
    if changed and not dry:
        out_text = "\n".join(out)
        if crlf:
            out_text = out_text.replace("\n", "\r\n")
        path.write_bytes(out_text.encode("utf-8"))
    return changed


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    roots = [Path(a) for a in args] if args else ROOTS
    total = files = 0
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            n = convert_file(path, dry)
            if n:
                files += 1
                total += n
    print(f"{'would convert' if dry else 'converted'} {total} declarations in {files} files")


if __name__ == "__main__":
    main()
