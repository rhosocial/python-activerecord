# scripts/p3_fix_reads_and_writes.py
"""Rewrite the two forms the AST sweep could not see.

The sweep rewrote *class-body* declarations. Two other forms remain in
backend repositories:

1. a read such as ``Indexed.__table_name__`` -- a consumer outside the
   framework, which now has to call the accessor;
2. a runtime assignment such as ``Author.__table_name__ = "archive"`` --
   a dynamic declaration, which is expressed by installing a classmethod
   on the model, the same way an override would be declared in a class body.

Reads are rewritten first: an assignment's left side is not a read, and
matching it as one would turn ``X.__table_name__ = v`` into the invalid
``X.table_name() = v``.
"""
import re
import sys
from pathlib import Path

MAP = {
    "__table_name__": "table_name",
    "__schema_name__": "schema_name",
    "__primary_key__": "primary_key",
    "__pk_auto_generated__": "pk_auto_generated",
    "__read_only__": "read_only",
    "__deleted_at_field__": "deleted_at_field",
    "__created_at_field__": "created_at_field",
    "__updated_at_field__": "updated_at_field",
    "__version_field__": "version_field",
    "__version_increment_by__": "version_increment_by",
}

ASSIGN = re.compile(
    r"^(\s*)([A-Za-z_][A-Za-z0-9_.]*)\.(__[a-z_]+__)\s*=\s*(.*)$",
    re.MULTILINE,
)
READ = re.compile(
    r"([A-Za-z_][A-Za-z0-9_.]*)\.(__[a-z_]+__)(?!\s*=\s*)(?![A-Za-z0-9_])"
)


def convert(path: Path, dry: bool) -> int:
    raw = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    text = raw.replace("\r\n", "\n")
    count = 0

    def read_repl(match: "re.Match") -> str:
        nonlocal count
        owner, dunder = match.groups()
        method = MAP.get(dunder)
        if method is None:
            return match.group(0)
        count += 1
        return f"{owner}.{method}()"

    text = READ.sub(read_repl, text)

    def assign_repl(match: "re.Match") -> str:
        nonlocal count
        indent, owner, dunder, value = match.groups()
        method = MAP.get(dunder)
        if method is None:
            return match.group(0)
        count += 1
        return f"{indent}{owner}.{method} = classmethod(lambda cls: {value})"

    text = ASSIGN.sub(assign_repl, text)

    if count and not dry:
        if crlf:
            text = text.replace("\n", "\r\n")
        path.write_bytes(text.encode("utf-8"))
    return count


def main() -> None:
    dry = "--dry" in sys.argv
    roots = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = total = 0
    for root in roots:
        for path in sorted(Path(root).rglob("*.py")):
            if "__pycache__" in path.as_posix():
                continue
            n = convert(path, dry)
            if n:
                files += 1
                total += n
                print(f"{path.as_posix()}: {n}")
    print(f"{'would rewrite' if dry else 'rewrote'} {total} occurrences in {files} files")


if __name__ == "__main__":
    main()
